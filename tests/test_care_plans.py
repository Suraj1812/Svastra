import json

from app.models.audit import AuditLog
from app.models.postoffice import OutboundEvent, PostOfficeAcknowledgement, ReceivedEvent, TimelineEvent
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
    assert {item["term"] for item in search.json()["data"]["terms"]} == {
        "Body Temperature",
        "Temperature",
    }
    options = integration_client.get(
        "/terminology/provider-terms/demo_term_temperature/advisory-options",
        headers=headers(provider),
    )
    assert options.status_code == 200
    assert options.json()["data"]["options"]["measurement_units"] == ["°C", "°F"]

    drug_search = integration_client.get(
        "/terminology/provider-terms?query=levaz", headers=headers(provider)
    )
    assert drug_search.status_code == 200
    assert drug_search.json()["data"]["terms"][0]["term"] == "Levaz 500 mg oral tablet"
    drug_options = integration_client.get(
        "/terminology/provider-terms/2647801000189105/advisory-options",
        headers=headers(provider),
    )
    assert drug_options.status_code == 200
    assert drug_options.json()["data"]["options"]["dose_units"] == ["tablet"]
    assert drug_options.json()["data"]["options"]["routes"] == ["oral"]
    assert drug_options.json()["data"]["options"]["medication_details"]["generic"] == "Levofloxacin"

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
    assert valid.json()["data"]["execution_status"] == "pending"


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
    assert body["advisories"][0]["execution_status"] == "pending"
    assert body["event_id"].startswith("evt_")

    republish = integration_client.post(
        f"/care-plans/{plan['id']}/publish",
        json={"confirmed": True},
        headers=headers(provider),
    )
    assert republish.status_code == 400

    add_after_first_publish = integration_client.post(
        f"/care-plans/{plan['id']}/advisories",
        json={
            "concept_id": "demo_term_exercise",
            "term": "Exercise",
            "tag": "recommendation",
            "configuration": {
                "frequency": "once_daily",
                "duration_value": 7,
                "duration_unit": "days",
                "additional_instructions": "Walk for 20 minutes after breakfast",
            },
        },
        headers=headers(provider),
    )
    assert add_after_first_publish.status_code == 201

    patient_view = integration_client.get("/me/advisories", headers=headers(patient))
    assert patient_view.status_code == 200
    patient_advisory = patient_view.json()["data"]["advisories"][0]
    assert patient_advisory["advisory"] == "Temperature"
    assert "Record after resting for five minutes" in patient_advisory["instruction"]
    assert patient_advisory["execution_status"] == "pending"

    patient_monitor = integration_client.get(
        f"/postoffice/monitor/events/{body['event_id']}",
        params={"patient_id": patient["user"]["id"]},
        headers=headers(patient),
    )
    assert patient_monitor.status_code == 200
    monitor_data = patient_monitor.json()["data"]
    assert monitor_data["payload"]["advisories"][0]["concept_id"] == "[REDACTED]"
    assert "payload.advisories[].concept_id" in monitor_data["redacted_fields"]

    db = integration_client.testing_session_local()
    try:
        timeline = db.query(TimelineEvent).filter(
            TimelineEvent.event_type == "advisory.publish"
        ).one()
        cep_payload = json.loads(timeline.payload_json)["payload"]
        assert cep_payload["execution_status"] == "pending"
        assert cep_payload["advisories"][0]["execution_status"] == "pending"
        assert cep_payload["advisories"][0]["concept_id"] == "demo_term_temperature"
        assert db.query(OutboundEvent).filter(OutboundEvent.event_id == body["event_id"]).count() == 0
        assert db.query(ReceivedEvent).filter(ReceivedEvent.event_id == body["event_id"]).count() == 1
        assert db.query(PostOfficeAcknowledgement).filter(
            PostOfficeAcknowledgement.event_id == body["event_id"]
        ).count() == 1
        assert db.query(AuditLog).filter(AuditLog.action == "advisory.published").count() == 1
        assert db.query(AuditLog).filter(AuditLog.action == "advisory.created").count() == 2
    finally:
        db.close()


def test_medication_allergy_warning_is_blocking_and_visible(integration_client):
    patient = register_patient(integration_client, "9876501231")
    provider = register_provider(integration_client, "9876501232")
    allergy = integration_client.post(
        "/me/allergies",
        json={"allergen_term": "Paracetamol"},
        headers=headers(patient),
    )
    assert allergy.status_code == 201
    denied_provider_write = integration_client.post(
        "/me/allergies",
        json={"allergen_term": "Penicillin"},
        headers=headers(provider),
    )
    assert denied_provider_write.status_code == 403

    grant_provider_access(integration_client, patient, provider)
    plan = _create_plan(integration_client, patient, provider)
    advisory = integration_client.post(
        f"/care-plans/{plan['id']}/advisories",
        json={
            "concept_id": "demo_term_paracetamol",
            "term": "Paracetamol",
            "tag": "medication",
            "configuration": {
                "dose_value": 500,
                "dose_unit": "mg",
                "route": "oral",
                "frequency": "once_daily",
                "duration_value": 3,
                "duration_unit": "days",
            },
        },
        headers=headers(provider),
    )
    assert advisory.status_code == 201
    warning = advisory.json()["data"]["allergy_warnings"][0]
    assert warning["code"] == "POTENTIAL_ALLERGY"
    assert warning["blocking"] is True


def test_care_plan_update_and_archive_are_owner_scoped(integration_client):
    patient = register_patient(integration_client, "9876501241")
    provider = register_provider(integration_client, "9876501242")
    outsider = register_provider(integration_client, "9876501243", "Dr No Access")
    grant_provider_access(integration_client, patient, provider)
    plan = _create_plan(integration_client, patient, provider)

    denied = integration_client.put(
        f"/care-plans/{plan['id']}",
        json={"title": "Stolen edit", "diagnosis": None},
        headers=headers(outsider),
    )
    assert denied.status_code == 403

    updated = integration_client.put(
        f"/care-plans/{plan['id']}",
        json={"title": "Updated monitoring plan", "diagnosis": "Recovery monitoring"},
        headers=headers(provider),
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["title"] == "Updated monitoring plan"

    archived = integration_client.delete(
        f"/care-plans/{plan['id']}",
        headers=headers(provider),
    )
    assert archived.status_code == 200
    assert archived.json()["data"]["status"] == "INACTIVE"

    blocked_edit = integration_client.put(
        f"/care-plans/{plan['id']}",
        json={"title": "Should fail", "diagnosis": None},
        headers=headers(provider),
    )
    assert blocked_edit.status_code == 400


def test_type_specific_advisory_rules_reject_forged_fields_and_units(integration_client):
    patient = register_patient(integration_client, "9876501251")
    provider = register_provider(integration_client, "9876501252")
    grant_provider_access(integration_client, patient, provider)
    plan = _create_plan(integration_client, patient, provider)

    mismatched_warning_unit = integration_client.post(
        f"/care-plans/{plan['id']}/advisories",
        json={
            "concept_id": "demo_term_temperature",
            "term": "Temperature",
            "tag": "measurement",
            "configuration": {
                **VALID_MEASUREMENT_CONFIG,
                "value_warning": {
                    "condition": "more_than",
                    "threshold_value": 100.4,
                    "measurement_unit": "°C",
                    "notification": "immediate",
                },
            },
        },
        headers=headers(provider),
    )
    assert mismatched_warning_unit.status_code == 400

    forged_catalog_unit = integration_client.post(
        f"/care-plans/{plan['id']}/advisories",
        json={
            "concept_id": "2647801000189105",
            "term": "Levaz 500 mg oral tablet",
            "tag": "medication",
            "configuration": {
                "dose_value": 1,
                "dose_unit": "mg",
                "route": "oral",
                "frequency": "once_daily",
                "duration_value": 5,
                "duration_unit": "days",
            },
        },
        headers=headers(provider),
    )
    assert forged_catalog_unit.status_code == 400

    extra_investigation_field = integration_client.post(
        f"/care-plans/{plan['id']}/advisories",
        json={
            "concept_id": "demo_term_hba1c",
            "term": "HbA1c",
            "tag": "investigation",
            "configuration": {
                "priority": "routine",
                "attachment_required": True,
                "frequency": "monthly",
                "duration_value": 3,
                "duration_unit": "months",
            },
        },
        headers=headers(provider),
    )
    assert extra_investigation_field.status_code == 400

    valid_recommendation = integration_client.post(
        f"/care-plans/{plan['id']}/advisories",
        json={
            "concept_id": "demo_term_walking_exercise",
            "term": "Walking Exercise",
            "tag": "recommendation",
            "configuration": {
                "frequency": "once_daily",
                "duration_value": 4,
                "duration_unit": "weeks",
                "non_response_warning": {
                    "clinical_grace_minutes": 90,
                    "notification": "daily_summary",
                },
            },
        },
        headers=headers(provider),
    )
    assert valid_recommendation.status_code == 201
    assert valid_recommendation.json()["data"]["execution_status"] == "pending"


def test_advisory_execution_status_is_server_owned(integration_client):
    patient = register_patient(integration_client, "9876501261")
    provider = register_provider(integration_client, "9876501262")
    grant_provider_access(integration_client, patient, provider)
    plan = _create_plan(integration_client, patient, provider)

    response = integration_client.post(
        f"/care-plans/{plan['id']}/advisories",
        json={
            "concept_id": "demo_term_exercise",
            "term": "Exercise",
            "tag": "recommendation",
            "execution_status": "completed",
            "configuration": {
                "frequency": "once_daily",
                "duration_value": 7,
                "duration_unit": "days",
            },
        },
        headers=headers(provider),
    )
    assert response.status_code == 422
