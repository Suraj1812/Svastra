import json
from datetime import date, datetime, timedelta, timezone

from app.config import settings
from app.models.audit import AuditLog
from app.models.care import Advisory
from app.models.postoffice import TimelineEvent
from app.models.workflow import CareTask, ClinicalAlert, ClinicalAttachment, TaskResponse
from tests.helpers import grant_provider_access, headers, register_patient, register_provider


def _plan(client, patient, provider, title="One-step care"):
    response = client.post(
        "/care-plans",
        json={"patient_id": patient["user"]["id"], "title": title},
        headers=headers(provider),
    )
    assert response.status_code == 201
    return response.json()["data"]


def _add(client, plan, provider, *, concept_id, term, tag, configuration):
    response = client.post(
        f"/care-plans/{plan['id']}/advisories",
        json={
            "concept_id": concept_id,
            "term": term,
            "tag": tag,
            "configuration": configuration,
        },
        headers=headers(provider),
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _publish(client, plan, advisory, provider):
    response = client.post(
        f"/care-plans/{plan['id']}/advisories/{advisory['id']}/publish",
        json={"confirmed": True},
        headers=headers(provider),
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _common(**extra):
    return {
        "frequency": "once_daily",
        "duration_value": 1,
        "duration_unit": "hours",
        **extra,
    }


def test_publication_generates_schedule_task_and_coded_medication_response(integration_client):
    patient = register_patient(integration_client, "9876501401")
    provider = register_provider(integration_client, "9876501402")
    grant_provider_access(integration_client, patient, provider)
    plan = _plan(integration_client, patient, provider)
    advisory = _add(
        integration_client,
        plan,
        provider,
        concept_id="2647801000189105",
        term="Levaz 500 mg oral tablet",
        tag="medication",
        configuration=_common(dose_value=1, dose_unit="tablet", route="oral"),
    )

    published = _publish(integration_client, plan, advisory, provider)
    assert set(published["workflow"]) == {"schedule", "advisory", "tasks"}
    assert published["advisory"]["execution_status"] == "pending"

    tasks = integration_client.get("/me/tasks", headers=headers(patient))
    assert tasks.status_code == 200
    task = tasks.json()["data"]["tasks"][0]
    assert task["expected_response"] == "taken_or_missed"
    assert task["execution_status"] == "pending"

    missing_reason = integration_client.post(
        f"/tasks/{task['task_id']}/responses",
        json={"response_status": "missed"},
        headers=headers(patient),
    )
    assert missing_reason.status_code == 400

    tampered_reason = integration_client.post(
        f"/tasks/{task['task_id']}/responses",
        json={
            "response_status": "missed",
            "reason": {"concept_id": "422587007", "term": "Something else"},
        },
        headers=headers(patient),
    )
    assert tampered_reason.status_code == 400

    response = integration_client.post(
        f"/tasks/{task['task_id']}/responses",
        json={
            "response_status": "missed",
            "reason": {"concept_id": "422587007", "term": "Nausea"},
        },
        headers=headers(patient),
    )
    assert response.status_code == 201, response.text
    body = response.json()["data"]
    assert body["task"]["execution_status"] == "missed"
    assert body["response"]["value"]["reason"]["term"] == "Nausea"
    assert body["deliveries"][0]["event_id"].startswith("evt_")

    duplicate = integration_client.post(
        f"/tasks/{task['task_id']}/responses",
        json={"response_status": "taken"},
        headers=headers(patient),
    )
    assert duplicate.status_code == 400

    db = integration_client.testing_session_local()
    try:
        assert db.query(CareTask).count() == 1
        assert db.query(TaskResponse).count() == 1
        assert db.query(Advisory).one().execution_status == "missed"
        event_types = [row[0] for row in db.query(TimelineEvent.event_type).order_by(TimelineEvent.id)]
        assert event_types[-4:] == [
            "schedule.generate",
            "advisory.publish",
            "task.generate",
            "response.log",
        ]
        response_event = db.query(TimelineEvent).filter(TimelineEvent.event_type == "response.log").one()
        payload = json.loads(response_event.payload_json)["payload"]
        assert payload["response"]["reason"]["conceptId"] == "422587007"
        assert db.query(AuditLog).filter(AuditLog.action == "task.response_received").count() == 1
    finally:
        db.close()


def test_allergy_conflict_blocks_publication_and_generates_alert(integration_client):
    patient = register_patient(integration_client, "9876501411")
    provider = register_provider(integration_client, "9876501412")
    integration_client.post(
        "/me/allergies",
        json={"allergen_term": "Levofloxacin"},
        headers=headers(patient),
    )
    grant_provider_access(integration_client, patient, provider)
    plan = _plan(integration_client, patient, provider)
    advisory = _add(
        integration_client,
        plan,
        provider,
        concept_id="2647801000189105",
        term="Levaz 500 mg oral tablet",
        tag="medication",
        configuration=_common(dose_value=1, dose_unit="tablet", route="oral"),
    )
    blocked = integration_client.post(
        f"/care-plans/{plan['id']}/advisories/{advisory['id']}/publish",
        json={"confirmed": True},
        headers=headers(provider),
    )
    assert blocked.status_code == 400
    assert "Publishing blocked" in blocked.json()["error"]["message"]

    alerts = integration_client.get("/provider/alerts", headers=headers(provider))
    assert alerts.status_code == 200
    assert alerts.json()["data"]["alerts"][0]["alert_type"] == "allergy_conflict"

    db = integration_client.testing_session_local()
    try:
        assert db.query(Advisory).one().status == "DRAFT"
        assert db.query(CareTask).count() == 0
        assert db.query(ClinicalAlert).count() == 1
        assert db.query(TimelineEvent).filter(TimelineEvent.event_type == "alert.trigger").count() == 1
        assert db.query(TimelineEvent).filter(TimelineEvent.event_type == "advisory.publish").count() == 0
    finally:
        db.close()


def test_measurement_threshold_generates_provider_alert(integration_client):
    patient = register_patient(integration_client, "9876501421")
    provider = register_provider(integration_client, "9876501422")
    grant_provider_access(integration_client, patient, provider)
    plan = _plan(integration_client, patient, provider)
    advisory = _add(
        integration_client,
        plan,
        provider,
        concept_id="demo_term_temperature",
        term="Temperature",
        tag="measurement",
        configuration=_common(
            measurement_unit="°F",
            value_warning={
                "condition": "more_than",
                "threshold_value": 100.4,
                "measurement_unit": "°F",
                "notification": "immediate",
                "severity": "critical",
            },
        ),
    )
    _publish(integration_client, plan, advisory, provider)
    task = integration_client.get("/me/tasks", headers=headers(patient)).json()["data"]["tasks"][0]

    wrong_unit = integration_client.post(
        f"/tasks/{task['task_id']}/responses",
        json={"response_status": "recorded", "numeric_value": 101, "measurement_unit": "°C"},
        headers=headers(patient),
    )
    assert wrong_unit.status_code == 400

    response = integration_client.post(
        f"/tasks/{task['task_id']}/responses",
        json={"response_status": "recorded", "numeric_value": 101, "measurement_unit": "°F"},
        headers=headers(patient),
    )
    assert response.status_code == 201
    assert len(response.json()["data"]["deliveries"]) == 2
    alerts = integration_client.get("/provider/alerts?alert_status=OPEN", headers=headers(provider))
    assert alerts.json()["data"]["alerts"][0]["alert_type"] == "value_threshold"
    assert alerts.json()["data"]["alerts"][0]["severity"] == "critical"


def test_wednesday_timeline_and_dashboard_feed_show_threshold_alert(integration_client):
    patient = register_patient(integration_client, "9876501425")
    provider = register_provider(integration_client, "9876501426")
    grant_provider_access(integration_client, patient, provider)
    plan = _plan(integration_client, patient, provider, title="Temperature Monitoring")
    advisory = _add(
        integration_client,
        plan,
        provider,
        concept_id="demo_term_temperature",
        term="Temperature",
        tag="measurement",
        configuration=_common(
            measurement_unit="°F",
            non_response_warning={
                "clinical_grace_minutes": 90,
                "notification": "immediate",
                "severity": "medium",
            },
            value_warning={
                "condition": "more_than",
                "threshold_value": 101,
                "measurement_unit": "°F",
                "notification": "immediate",
                "severity": "critical",
            },
        ),
    )
    _publish(integration_client, plan, advisory, provider)
    task = integration_client.get("/me/tasks", headers=headers(patient)).json()["data"]["tasks"][0]

    response = integration_client.post(
        f"/tasks/{task['task_id']}/responses",
        json={"response_status": "recorded", "numeric_value": 102.5, "measurement_unit": "°F"},
        headers=headers(patient),
    )
    assert response.status_code == 201

    provider_timeline = integration_client.get(
        f"/postoffice/timeline?patient_id={patient['user']['id']}",
        headers=headers(provider),
    )
    assert provider_timeline.status_code == 200
    events = provider_timeline.json()["data"]["events"]
    labels = [event["label"] for event in events]
    assert "Advisory Published" in labels
    assert "Care Plan Delivered" in labels
    assert "Temperature Received" in labels
    assert "Temperature Above Threshold" in labels
    alert_event = next(event for event in events if event["label"] == "Temperature Above Threshold")
    assert alert_event["event_type"] == "event.alert.trigger"
    assert set(alert_event["cep"]) == {"header", "context", "body"}
    assert alert_event["cep"]["body"]["reason"] == "threshold_exceeded"
    assert alert_event["cep"]["body"]["recorded_value"] == "102.5 °F"

    patient_timeline = integration_client.get(
        f"/postoffice/timeline?patient_id={patient['user']['id']}",
        headers=headers(patient),
    )
    patient_labels = [event["label"] for event in patient_timeline.json()["data"]["events"]]
    assert "Care Plan Received" in patient_labels
    assert "Temperature Submitted" in patient_labels

    feed = integration_client.get("/provider/dashboard-feed", headers=headers(provider))
    assert feed.status_code == 200
    data = feed.json()["data"]
    assert data["active_alerts"][0]["display"]["title"] == "Temperature Above Threshold"
    assert data["active_alerts"][0]["display"]["recorded_value"] == "102.5 °F"
    assert data["patient_status"][0]["label"] == "Alert Present"
    assert data["patient_status"][0]["color"] == "red"
    assert data["recent_responses"][0]["response"]["value"]["numeric_value"] == 102.5


def test_investigation_report_upload_is_private_validated_and_hash_verified(
    integration_client, tmp_path
):
    original_storage = settings.attachment_storage_path
    settings.attachment_storage_path = tmp_path / "private"
    try:
        patient = register_patient(integration_client, "9876501431")
        provider = register_provider(integration_client, "9876501432")
        outsider = register_provider(integration_client, "9876501433", "Dr Outsider")
        grant_provider_access(integration_client, patient, provider)
        plan = _plan(integration_client, patient, provider)
        advisory = _add(
            integration_client,
            plan,
            provider,
            concept_id="demo_term_hba1c",
            term="HbA1c",
            tag="investigation",
            configuration=_common(
                priority="urgent",
                due_date=(date.today() + timedelta(days=1)).isoformat(),
                upload_required=True,
                alert_if_not_uploaded=True,
                grace_period_value=2,
                grace_period_unit="days",
            ),
        )
        _publish(integration_client, plan, advisory, provider)
        task = integration_client.get("/me/tasks", headers=headers(patient)).json()["data"]["tasks"][0]

        fake_pdf = integration_client.post(
            f"/tasks/{task['task_id']}/upload",
            files={"file": ("report.pdf", b"not really pdf", "application/pdf")},
            headers=headers(patient),
        )
        assert fake_pdf.status_code == 400

        content = b"%PDF-1.4\nSVASTRA test report\n%%EOF"
        uploaded = integration_client.post(
            f"/tasks/{task['task_id']}/upload",
            files={"file": ("HbA1c Report.pdf", content, "application/pdf")},
            headers=headers(patient),
        )
        assert uploaded.status_code == 201, uploaded.text
        data = uploaded.json()["data"]
        assert data["task"]["execution_status"] == "completed"
        attachment_id = data["attachment"]["attachment_id"]

        patient_download = integration_client.get(
            f"/attachments/{attachment_id}", headers=headers(patient)
        )
        assert patient_download.status_code == 200
        assert patient_download.content == content
        assert patient_download.headers["x-content-sha256"] == data["attachment"]["sha256"]

        provider_download = integration_client.get(
            f"/attachments/{attachment_id}", headers=headers(provider)
        )
        assert provider_download.status_code == 200
        denied = integration_client.get(
            f"/attachments/{attachment_id}", headers=headers(outsider)
        )
        assert denied.status_code == 403

        db = integration_client.testing_session_local()
        try:
            attachment = db.query(ClinicalAttachment).one()
            assert attachment.storage_path.startswith(str(settings.attachment_storage_path))
            assert db.query(TaskResponse).one().response_status == "uploaded"
            assert db.query(TimelineEvent).filter(TimelineEvent.event_type == "attachment.upload").count() == 1
            assert db.query(ClinicalAlert).count() == 0
        finally:
            db.close()
    finally:
        settings.attachment_storage_path = original_storage


def test_investigation_overdue_is_passive_and_does_not_alert(integration_client):
    patient = register_patient(integration_client, "9876501435")
    provider = register_provider(integration_client, "9876501436")
    grant_provider_access(integration_client, patient, provider)
    plan = _plan(integration_client, patient, provider)
    advisory = _add(
        integration_client,
        plan,
        provider,
        concept_id="demo_term_cbc",
        term="CBC",
        tag="investigation",
        configuration=_common(
            priority="urgent",
            due_date=(date.today() + timedelta(days=1)).isoformat(),
            upload_required=True,
            alert_if_not_uploaded=True,
            grace_period_value=2,
            grace_period_unit="days",
        ),
    )
    _publish(integration_client, plan, advisory, provider)
    db = integration_client.testing_session_local()
    try:
        task = db.query(CareTask).one()
        task.grace_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    evaluated = integration_client.post(
        "/provider/tasks/evaluate-overdue",
        json={"patient_id": patient["user"]["id"]},
        headers=headers(provider),
    )
    assert evaluated.status_code == 200
    assert evaluated.json()["data"]["evaluated"] == 1
    assert evaluated.json()["data"]["alerts"] == []

    db = integration_client.testing_session_local()
    try:
        assert db.query(ClinicalAlert).count() == 0
        assert db.query(TimelineEvent).filter(TimelineEvent.event_type == "alert.trigger").count() == 0
        assert db.query(CareTask).one().execution_status == "missed"
    finally:
        db.close()


def test_overdue_evaluation_marks_missed_alerts_once_and_provider_acknowledges(
    integration_client
):
    patient = register_patient(integration_client, "9876501441")
    provider = register_provider(integration_client, "9876501442")
    grant_provider_access(integration_client, patient, provider)
    plan = _plan(integration_client, patient, provider)
    advisory = _add(
        integration_client,
        plan,
        provider,
        concept_id="demo_term_walking_exercise",
        term="Walking Exercise",
        tag="recommendation",
        configuration=_common(
            non_response_warning={"clinical_grace_minutes": 1, "notification": "immediate"}
        ),
    )
    _publish(integration_client, plan, advisory, provider)
    db = integration_client.testing_session_local()
    try:
        task = db.query(CareTask).one()
        task.grace_expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    evaluated = integration_client.post(
        "/provider/tasks/evaluate-overdue",
        json={"patient_id": patient["user"]["id"]},
        headers=headers(provider),
    )
    assert evaluated.status_code == 200
    assert evaluated.json()["data"]["evaluated"] == 1
    alert = evaluated.json()["data"]["alerts"][0]

    repeated = integration_client.post(
        "/provider/tasks/evaluate-overdue",
        json={"patient_id": patient["user"]["id"]},
        headers=headers(provider),
    )
    assert repeated.json()["data"]["evaluated"] == 0

    acknowledged = integration_client.post(
        f"/provider/alerts/{alert['alert_id']}/acknowledge",
        json={"confirmed": True},
        headers=headers(provider),
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["data"]["status"] == "ACKNOWLEDGED"
