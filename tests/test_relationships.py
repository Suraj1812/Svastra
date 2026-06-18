from app.models.audit import AuditLog
from app.models.consent import RelationshipConsent
from tests.helpers import (
    grant_caregiver_access,
    grant_provider_access,
    headers,
    register_caregiver,
    register_patient,
    register_provider,
)


def test_consent_grant_creates_both_relationship_types_and_lists_them(integration_client):
    patient = register_patient(integration_client)
    provider = register_provider(integration_client)
    caregiver = register_caregiver(integration_client)

    grant_provider_access(integration_client, patient, provider)
    grant_caregiver_access(integration_client, patient, caregiver)

    provider_list = integration_client.get("/relationships/patients", headers=headers(provider))
    caregiver_list = integration_client.get("/relationships/patients", headers=headers(caregiver))
    patient_providers = integration_client.get("/relationships/providers", headers=headers(patient))
    patient_caregivers = integration_client.get("/relationships/caregivers", headers=headers(patient))

    assert provider_list.status_code == 200
    assert provider_list.json()["data"]["relationships"][0]["relationship_status"] == "ACTIVE"
    assert caregiver_list.json()["data"]["relationships"][0]["relationship_type"] == "patient_caregiver"
    assert patient_providers.json()["data"]["relationships"][0]["alias"] == "Dr Meera"
    assert patient_caregivers.json()["data"]["relationships"][0]["linked_user"]["role"] == "caregiver"


def test_relationship_requires_active_consent_and_deactivation_preserves_consent(integration_client):
    patient = register_patient(integration_client, "9876501011")
    provider = register_provider(integration_client, "9876501012")

    denied = integration_client.post(
        "/relationships/provider-patient",
        json={"patient_id": patient["user"]["id"], "confirmed": True},
        headers=headers(provider),
    )
    assert denied.status_code == 400
    assert "Active patient consent" in denied.json()["error"]["message"]

    consent_id = grant_provider_access(integration_client, patient, provider)
    linked = integration_client.get("/relationships/patients", headers=headers(provider))
    relationship_id = linked.json()["data"]["relationships"][0]["id"]

    deactivated = integration_client.delete(
        f"/relationships/{relationship_id}", headers=headers(patient)
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["data"]["relationship_status"] == "INACTIVE"

    db = integration_client.testing_session_local()
    try:
        assert db.query(RelationshipConsent).filter(
            RelationshipConsent.id == consent_id,
            RelationshipConsent.status == "ACTIVE",
        ).count() == 1
        assert db.query(AuditLog).filter(AuditLog.action == "relationship.created").count() == 1
        assert db.query(AuditLog).filter(AuditLog.action == "relationship.deactivated").count() == 1
    finally:
        db.close()


def test_relationship_details_are_party_scoped_and_consent_revoke_ends_access(integration_client):
    patient = register_patient(integration_client, "9876501021")
    provider = register_provider(integration_client, "9876501022")
    outsider = register_provider(integration_client, "9876501023", "Dr Outsider")
    consent_id = grant_provider_access(integration_client, patient, provider)

    relationship = integration_client.get("/relationships/patients", headers=headers(provider)).json()["data"]["relationships"][0]
    outsider_view = integration_client.get(
        f"/relationships/{relationship['id']}", headers=headers(outsider)
    )
    assert outsider_view.status_code == 404

    revoked = integration_client.post(
        f"/consent/request/{consent_id}/revoke",
        json={"confirmed": True},
        headers=headers(patient),
    )
    assert revoked.status_code == 200
    after = integration_client.get("/relationships/patients", headers=headers(provider)).json()["data"]["relationships"][0]
    assert after["relationship_status"] == "INACTIVE"
