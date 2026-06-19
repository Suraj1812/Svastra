from app.models.audit import AuditLog
from app.models.postoffice import OutboundEvent, PostOfficeAcknowledgement, ReceivedEvent, TimelineEvent
from tests.helpers import grant_provider_access, headers, register_patient, register_provider


VALID_MEASUREMENT_CONFIG = {
    "frequency": "four_times_daily",
    "duration_value": 5,
    "duration_unit": "days",
    "measurement_unit": "°F",
    "target_value": "98.6",
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
                "instruction": "Walk for 20 minutes after breakfast",
            },
        },
        headers=headers(provider),
    )
    assert add_after_first_publish.status_code == 201

    patient_view = integration_client.get("/me/advisories", headers=headers(patient))
    assert patient_view.status_code == 200
    patient_advisory = patient_view.json()["data"]["advisories"][0]
    assert patient_advisory["advisory"] == "Temperature"
    assert "Target: 98.6" in patient_advisory["instruction"]
    assert "Record after resting for five minutes" in patient_advisory["instruction"]

    db = integration_client.testing_session_local()
    try:
        assert db.query(TimelineEvent).filter(TimelineEvent.event_type == "advisory.publish").count() == 1
        assert db.query(OutboundEvent).filter(OutboundEvent.event_id == body["event_id"]).count() == 0
        assert db.query(ReceivedEvent).filter(ReceivedEvent.event_id == body["event_id"]).count() == 1
        assert db.query(PostOfficeAcknowledgement).filter(
            PostOfficeAcknowledgement.event_id == body["event_id"]
        ).count() == 1
        assert db.query(AuditLog).filter(AuditLog.action == "advisory.published").count() == 1
    finally:
        db.close()


def test_medication_allergy_warning_is_non_blocking_and_visible(integration_client):
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
                "dose": "500 mg",
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
    assert warning["blocking"] is False


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
