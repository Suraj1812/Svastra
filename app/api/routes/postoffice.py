from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.serializers import client_ip
from app.audit.audit_service import record_audit_event
from app.config import settings
from app.core.responses import success_response
from app.database import get_db
from app.models.postoffice import OutboundEvent, TimelineEvent
from app.postoffice.dispatcher import (
    acknowledge_event,
    dispatch_event,
    send_event,
    serialize_acknowledgement,
    serialize_outbound,
)
from app.postoffice.monitor_service import (
    MonitorValidationError,
    get_monitor_event,
    list_monitor_events,
    monitor_summary,
)
from app.postoffice.timeline_service import serialize_timeline_event
from app.postoffice.validators import AcknowledgementRequest, CEPEvent, CEPValidationError
from app.schemas.monitor import EventMonitorQuery, EventMonitorSummaryQuery
from app.relationships.relationship_validator import validate_patient_scope
from app.relationships.relationship_validator import RelationshipValidationError


router = APIRouter(prefix="/postoffice", tags=["PostOffice"])


def _postoffice_error(error: Exception):
    if isinstance(error, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    if "not found" in str(error).lower():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/send", status_code=status.HTTP_202_ACCEPTED)
def send_cep_event(
    payload: CEPEvent,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        outbound, route, duplicate = send_event(db, payload, actor_user=current_user)
        outbound = dispatch_event(db, outbound.event_id)
    except (CEPValidationError, ValueError, PermissionError) as error:
        _postoffice_error(error)
    return success_response(
        {
            **serialize_outbound(outbound),
            "handler": route.handler,
            "duplicate": duplicate,
        },
        "CEP event validated and routed",
    )


@router.post("/acknowledge")
def acknowledge_cep_event(
    payload: AcknowledgementRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    outbound = db.query(OutboundEvent).filter(OutboundEvent.event_id == payload.event_id).first()
    timeline = db.query(TimelineEvent).filter(TimelineEvent.event_id == payload.event_id).first()
    scoped_patient_id = outbound.patient_id if outbound is not None else timeline.patient_id if timeline else None
    if scoped_patient_id is not None:
        try:
            validate_patient_scope(db, current_user=current_user, patient_id=scoped_patient_id)
        except RelationshipValidationError as error:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    try:
        acknowledgement, duplicate = acknowledge_event(
            db,
            event_id=payload.event_id,
            received_by=payload.received_by,
            status=payload.status,
            actor_user=current_user,
        )
    except (ValueError, PermissionError) as error:
        _postoffice_error(error)
    return success_response(
        {**serialize_acknowledgement(acknowledgement), "duplicate": duplicate},
        "CEP event acknowledged",
    )


@router.post("/events/{event_id}/retry")
def retry_cep_event(
    request: Request,
    event_id: Annotated[
        str,
        Path(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,63}$"),
    ],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    outbound = db.query(OutboundEvent).filter(OutboundEvent.event_id == event_id).first()
    if outbound is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outbound event not found")
    try:
        validate_patient_scope(db, current_user=current_user, patient_id=outbound.patient_id)
    except RelationshipValidationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    if outbound.retry_count >= settings.postoffice_max_retries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PostOffice retry limit of {settings.postoffice_max_retries} has been reached",
        )
    outbound.status = "pending"
    db.commit()
    retried = dispatch_event(db, event_id)
    record_audit_event(
        db,
        action="postoffice.delivery_retried",
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        mobile_number=current_user.mobile_number,
        ip_address=client_ip(request),
        metadata={
            "event_id": event_id,
            "patient_id": outbound.patient_id,
            "retry_count": retried.retry_count,
        },
    )
    return success_response(serialize_outbound(retried), "CEP delivery retried")


@router.get("/outbound")
def get_outbound_events(
    patient_id: Annotated[int, Query(gt=0)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        validate_patient_scope(db, current_user=current_user, patient_id=patient_id)
    except RelationshipValidationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    events = db.query(OutboundEvent).filter(OutboundEvent.patient_id == patient_id).order_by(
        OutboundEvent.created_at.desc()
    ).limit(limit).all()
    return success_response({"events": [serialize_outbound(event) for event in events]})


@router.get("/timeline")
def get_timeline_events(
    patient_id: Annotated[int, Query(gt=0)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        validate_patient_scope(db, current_user=current_user, patient_id=patient_id)
    except RelationshipValidationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    events = db.query(TimelineEvent).filter(TimelineEvent.patient_id == patient_id).order_by(
        TimelineEvent.occurred_at.desc()
    ).limit(limit).all()
    return success_response(
        {
            "events": [
                serialize_timeline_event(db, event, role=current_user.role)
                for event in events
            ]
        }
    )


@router.get("/monitor/summary")
def get_event_monitor_summary(
    filters: Annotated[EventMonitorSummaryQuery, Query()],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        validate_patient_scope(db, current_user=current_user, patient_id=filters.patient_id)
        result = monitor_summary(
            db,
            filters=filters,
            role=current_user.role,
            viewer_id=current_user.id,
        )
    except (RelationshipValidationError, MonitorValidationError, ValueError) as error:
        _postoffice_error(
            PermissionError(str(error)) if isinstance(error, RelationshipValidationError) else error
        )
    return success_response(result, "Event monitor summary loaded")


@router.get("/monitor/events")
def get_event_monitor_events(
    filters: Annotated[EventMonitorQuery, Query()],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        validate_patient_scope(db, current_user=current_user, patient_id=filters.patient_id)
        result = list_monitor_events(
            db,
            filters=filters,
            role=current_user.role,
            viewer_id=current_user.id,
        )
    except (RelationshipValidationError, MonitorValidationError, ValueError) as error:
        _postoffice_error(
            PermissionError(str(error)) if isinstance(error, RelationshipValidationError) else error
        )
    return success_response(result, "Event monitor page loaded")


@router.get("/monitor/events/{event_id}")
def get_event_monitor_detail(
    request: Request,
    event_id: Annotated[
        str,
        Path(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,63}$"),
    ],
    patient_id: Annotated[int, Query(gt=0)],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        validate_patient_scope(db, current_user=current_user, patient_id=patient_id)
        result = get_monitor_event(
            db,
            patient_id=patient_id,
            event_id=event_id,
            role=current_user.role,
            viewer_id=current_user.id,
        )
    except RelationshipValidationError as error:
        _postoffice_error(PermissionError(str(error)))
    except (MonitorValidationError, LookupError, ValueError) as error:
        _postoffice_error(error)
    record_audit_event(
        db,
        action="postoffice.monitor_detail_viewed",
        actor_user_id=current_user.id,
        actor_role=current_user.role,
        mobile_number=current_user.mobile_number,
        ip_address=client_ip(request),
        metadata={"event_id": event_id, "patient_id": patient_id},
    )
    return success_response(result, "Event monitor detail loaded")
