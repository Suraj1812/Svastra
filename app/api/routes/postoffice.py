import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
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
from app.postoffice.validators import AcknowledgementRequest, CEPEvent, CEPValidationError
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
    if outbound is not None:
        try:
            validate_patient_scope(db, current_user=current_user, patient_id=outbound.patient_id)
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
    event_id: str,
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
    outbound.status = "pending"
    db.commit()
    return success_response(serialize_outbound(dispatch_event(db, event_id)), "CEP delivery retried")


@router.get("/outbound")
def get_outbound_events(
    patient_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        validate_patient_scope(db, current_user=current_user, patient_id=patient_id)
    except RelationshipValidationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    events = db.query(OutboundEvent).filter(OutboundEvent.patient_id == patient_id).order_by(
        OutboundEvent.created_at.desc()
    ).limit(100).all()
    return success_response({"events": [serialize_outbound(event) for event in events]})


@router.get("/timeline")
def get_timeline_events(
    patient_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        validate_patient_scope(db, current_user=current_user, patient_id=patient_id)
    except RelationshipValidationError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    events = db.query(TimelineEvent).filter(TimelineEvent.patient_id == patient_id).order_by(
        TimelineEvent.occurred_at.desc()
    ).limit(100).all()
    return success_response(
        {
            "events": [
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "timestamp": event.occurred_at,
                    "source": event.source_app,
                    "payload": json.loads(event.payload_json)["payload"],
                }
                for event in events
            ]
        }
    )
