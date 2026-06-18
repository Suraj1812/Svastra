from app.models.audit import AuditLog
from app.models.postoffice import OutboundEvent, TimelineEvent
from tests.helpers import grant_provider_access, headers, register_patient, register_provider


VALID_MEASUREMENT_CONFIG = {
    "frequency": "four_times_daily",
    "duration_value": 5,
    "duration_unit": "days",
    "measurement_unit": "°F",
    "additional_instructions": "Record after resting for five minutes",
}


def _create_plan(client, patient, provider):
    response = client.post(
        "/care-plans",
        json={
            "patient_id": patient["user"]["id"],
            "title": "Post-operative monitoring",
            "diagnosis": "Post appendicectomy",
        },
        headers=headers(provider),
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_care_plan_requires_active_provider_relationship(integration_client):
    patient = register_patient(integration_client, "9876501201")
    provider = register_provider(integration_client, "9876501202")
    denied = integration_client.post(
        "/care-plans",
        json={"patient_id": patient["user"]["id"], "title": "Unsafe draft"},
        headers=headers(provider),
    )
    assert denied.status_code == 403


def test_terminology_tag_and_advisory_configuration_are_server_validated(integration_client):
    patient = register_patient(integration_client, "9876501211")
    provider = register_provider(integration_client, "9876501212")
    grant_provider_access(integration_client, patient, provider)
    plan = _create_plan(integration_client, patient, provider)

    search = integration_client.get(
        "/terminology/provider-terms?query=temp", headers=headers(provider)
    )
    assert search.status_code == 200
    assert search.json()["data"]["terms"] == [
        {"conceptId": "demo_term_temperature", "term": "Temperature", "tag": "measurement"}
    ]

    tampered = integration_client.post(
        f"/care-plans/{plan['id']}/advisories",
        json={
            "concept_id": "demo_term_temperature",
            "term": "Dolo 650 mg oral tablet",
            "tag": "medication",
            "configuration": {
                "frequency": "once_daily",
                "duration_value": 1,
                "duration_unit": "days",
                "dose": "650 mg",
            },
        },
        headers=headers(provider),
    )
    assert tampered.status_code == 400

    wrong_unit = integration_client.post(
        f"/care-plans/{plan['id']}/advisories",
        json={
            "concept_id": "demo_term_temperature",
            "term": "Temperature",
            "tag": "measurement",
            "configuration": {**VALID_MEASUREMENT_CONFIG, "measurement_unit": "kg"},
        },
        headers=headers(provider),
    )
    assert wrong_unit.status_code == 400

    valid = integration_client.post(
        f"/care-plans/{plan['id']}/advisories",
        json={
            "concept_id": "demo_term_temperature",
            "term": "Temperature",
            "tag": "measurement",
            "configuration": VALID_MEASUREMENT_CONFIG,
        },
        headers=headers(provider),
    )
    assert valid.status_code == 201
    assert valid.json()["data"]["advisory_type"] == "measurement"


def test_publish_is_immutable_and_generates_advisory_cep(integration_client):
    patient = register_patient(integration_client, "9876501221")
    provider = register_provider(integration_client, "9876501222")
    grant_provider_access(integration_client, patient, provider)
    plan = _create_plan(integration_client, patient, provider)
    integration_client.post(
        f"/care-plans/{plan['id']}/advisories",
        json={
            "concept_id": "demo_term_temperature",
            "term": "Temperature",
            "tag": "measurement",
            "configuration": VALID_MEASUREMENT_CONFIG,
        },
        headers=headers(provider),
    )

    published = integration_client.post(
        f"/care-plans/{plan['id']}/publish",
        json={"confirmed": True},
        headers=headers(provider),
    )
    assert published.status_code == 200
    body = published.json()["data"]
    assert body["status"] == "ACTIVE"
    assert body["advisories"][0]["status"] == "PUBLISHED"
    assert body["event_id"].startswith("evt_")

    republish = integration_client.post(
        f"/care-plans/{plan['id']}/publish",
        json={"confirmed": True},
        headers=headers(provider),
    )
    assert republish.status_code == 400

    edit_after_publish = integration_client.post(
        f"/care-plans/{plan['id']}/advisories",
        json={
            "concept_id": "demo_term_exercise",
            "term": "Exercise",
            "tag": "recommendation",
            "configuration": {
                "frequency": "once_daily",
                "duration_value": 7,
                "duration_unit": "days",
            },
        },
        headers=headers(provider),
    )
    assert edit_after_publish.status_code == 400

    db = integration_client.testing_session_local()
    try:
        assert db.query(TimelineEvent).filter(TimelineEvent.event_type == "advisory.publish").count() == 1
        assert db.query(OutboundEvent).filter(OutboundEvent.event_id == body["event_id"]).count() == 1
        assert db.query(AuditLog).filter(AuditLog.action == "care_plan.published").count() == 1
    finally:
        db.close()
