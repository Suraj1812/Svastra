from __future__ import annotations

from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.serializers import client_ip
from app.core.responses import success_response
from app.database import get_db
from app.schemas.workflow import AlertAcknowledgeRequest, EvaluateOverdueRequest, TaskResponseRequest
from app.terminology.term_service import search_response_reasons
from app.workflow.service import (
    acknowledge_alert,
    evaluate_overdue_tasks,
    get_provider_dashboard_feed,
    get_patient_tasks,
    get_provider_alerts,
    get_provider_tasks,
    get_scoped_attachment,
    get_scoped_task,
    record_task_response,
    resolve_alert,
    serialize_alert,
    serialize_attachment,
    serialize_response,
    serialize_task,
    upload_investigation_report,
)


router = APIRouter(tags=["Task Workflow"])
TaskStatusQuery = Literal["pending", "completed", "completed_late", "missed"]
AlertStatusQuery = Literal["OPEN", "NEW", "ACKNOWLEDGED", "RESOLVED"]
TASK_ID_PATTERN = r"^task_[a-f0-9]{32}$"
ALERT_ID_PATTERN = r"^alert_[a-f0-9]{32}$"
ATTACHMENT_ID_PATTERN = r"^attachment_[a-f0-9]{32}$"


def _workflow_error(error: Exception):
    if isinstance(error, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    if "not found" in str(error).lower():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("/terminology/response-reasons")
def response_reason_search(
    query: Optional[str] = Query(default=None, max_length=80),
    limit: int = Query(default=20, ge=1, le=50),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Patient role is required")
    try:
        reasons = search_response_reasons(db, query=query, limit=limit)
    except ValueError as error:
        _workflow_error(error)
    return success_response({"reasons": reasons, "count": len(reasons)})


@router.get("/me/tasks")
def my_tasks(
    execution_status: Optional[TaskStatusQuery] = Query(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Patient role is required")
    tasks = get_patient_tasks(
        db,
        patient_id=current_user.id,
        execution_status=execution_status,
    )
    return success_response({"tasks": [serialize_task(task) for task in tasks]})


@router.get("/provider/tasks")
def provider_tasks(
    patient_id: Optional[int] = Query(default=None, gt=0),
    execution_status: Optional[TaskStatusQuery] = Query(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "provider":
        raise HTTPException(status_code=403, detail="Provider role is required")
    tasks = get_provider_tasks(
        db,
        provider_id=current_user.id,
        patient_id=patient_id,
        execution_status=execution_status,
    )
    return success_response({"tasks": [serialize_task(task) for task in tasks]})


@router.get("/tasks/{task_uid}")
def task_detail(
    task_uid: Annotated[str, Path(pattern=TASK_ID_PATTERN)],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        task = get_scoped_task(db, task_uid=task_uid, user=current_user)
    except (ValueError, PermissionError) as error:
        _workflow_error(error)
    return success_response(serialize_task(task))


@router.post("/tasks/{task_uid}/responses", status_code=status.HTTP_201_CREATED)
def respond_to_task(
    task_uid: Annotated[str, Path(pattern=TASK_ID_PATTERN)],
    payload: TaskResponseRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        task, response, deliveries = record_task_response(
            db,
            task_uid=task_uid,
            patient=current_user,
            response_status=payload.response_status,
            reason=payload.reason.model_dump() if payload.reason else None,
            numeric_value=payload.numeric_value,
            measurement_unit=payload.measurement_unit,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _workflow_error(error)
    return success_response(
        {
            "task": serialize_task(task),
            "response": serialize_response(response),
            "deliveries": deliveries,
        },
        "Response saved",
    )


@router.post("/tasks/{task_uid}/upload", status_code=status.HTTP_201_CREATED)
async def upload_task_report(
    task_uid: Annotated[str, Path(pattern=TASK_ID_PATTERN)],
    request: Request,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        content = await file.read()
        task, response, attachment, deliveries = upload_investigation_report(
            db,
            task_uid=task_uid,
            patient=current_user,
            filename=file.filename or "",
            content_type=file.content_type or "",
            content=content,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _workflow_error(error)
    finally:
        await file.close()
    return success_response(
        {
            "task": serialize_task(task),
            "response": serialize_response(response),
            "attachment": serialize_attachment(attachment),
            "delivery": deliveries[0],
            "deliveries": deliveries,
        },
        "Report uploaded",
    )


@router.get("/attachments/{attachment_uid}")
def download_attachment(
    attachment_uid: Annotated[str, Path(pattern=ATTACHMENT_ID_PATTERN)],
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        attachment = get_scoped_attachment(
            db,
            attachment_uid=attachment_uid,
            user=current_user,
        )
    except (ValueError, PermissionError) as error:
        _workflow_error(error)
    return FileResponse(
        attachment.storage_path,
        media_type=attachment.content_type,
        filename=attachment.original_filename,
        headers={"X-Content-SHA256": attachment.sha256},
    )


@router.post("/provider/tasks/evaluate-overdue")
def evaluate_overdue(
    payload: EvaluateOverdueRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        tasks, alerts, deliveries = evaluate_overdue_tasks(
            db,
            provider=current_user,
            patient_id=payload.patient_id,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _workflow_error(error)
    return success_response(
        {
            "evaluated": len(tasks),
            "tasks": [serialize_task(task) for task in tasks],
            "alerts": [serialize_alert(alert) for alert in alerts],
            "deliveries": deliveries,
        },
        "Overdue tasks evaluated",
    )


@router.get("/provider/alerts")
def provider_alerts(
    patient_id: Optional[int] = Query(default=None, gt=0),
    alert_status: Optional[AlertStatusQuery] = Query(default=None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "provider":
        raise HTTPException(status_code=403, detail="Provider role is required")
    alerts = get_provider_alerts(
        db,
        provider_id=current_user.id,
        patient_id=patient_id,
        status=alert_status,
    )
    return success_response({"alerts": [serialize_alert(alert) for alert in alerts]})


@router.get("/provider/dashboard-feed")
def provider_dashboard_feed(
    patient_id: Optional[int] = Query(default=None, gt=0),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != "provider":
        raise HTTPException(status_code=403, detail="Provider role is required")
    try:
        feed = get_provider_dashboard_feed(
            db,
            provider_id=current_user.id,
            patient_id=patient_id,
        )
    except PermissionError as error:
        _workflow_error(error)
    return success_response(feed, "Provider dashboard feed loaded")


@router.post("/provider/alerts/{alert_uid}/acknowledge")
def acknowledge_provider_alert(
    alert_uid: Annotated[str, Path(pattern=ALERT_ID_PATTERN)],
    payload: AlertAcknowledgeRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        alert, changed, delivery = acknowledge_alert(
            db,
            alert_uid=alert_uid,
            provider=current_user,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _workflow_error(error)
    return success_response(
        {**serialize_alert(alert), "changed": changed, "delivery": delivery},
        "Alert acknowledged" if changed else "Alert already acknowledged",
    )


@router.post("/provider/alerts/{alert_uid}/resolve")
def resolve_provider_alert(
    alert_uid: Annotated[str, Path(pattern=ALERT_ID_PATTERN)],
    payload: AlertAcknowledgeRequest,
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        alert, changed, delivery = resolve_alert(
            db,
            alert_uid=alert_uid,
            provider=current_user,
            ip_address=client_ip(request),
        )
    except (ValueError, PermissionError) as error:
        _workflow_error(error)
    return success_response(
        {**serialize_alert(alert), "changed": changed, "delivery": delivery},
        "Alert resolved" if changed else "Alert already resolved",
    )
