from uuid import uuid4

from app.models.audit import AuditLog
from app.models.postoffice import OutboundEvent, PostOfficeAcknowledgement, TimelineEvent
from tests.helpers import grant_provider_access, headers, register_patient, register_provider


def _message_event(patient, provider, event_id=None):
    return {
        "event_type": "message.send",
        "event_id": event_id or f"evt_{uuid4().hex}",
        "timestamp": "2026-06-18T10:00:00+05:30",
        "source": "mantrana_mitra",
        "payload": {
            "actor_id": provider["user"]["id"],
            "patient_id": patient["user"]["id"],
            "message_id": f"msg_{uuid4().hex}",
            "message_text": "Please repeat the temperature after 30 minutes.",
        },
    }


def test_postoffice_validates_routes_acknowledges_and_preserves_timeline(integration_client):
    patient = register_patient(integration_client, "9876501101")
    provider = register_provider(integration_client, "9876501102")
    grant_provider_access(integration_client, patient, provider)
    event = _message_event(patient, provider)

    sent = integration_client.post("/postoffice/send", json=event, headers=headers(provider))
    assert sent.status_code == 202
    assert sent.json()["data"]["handler"] == "message_handler"
    assert sent.json()["data"]["target_app"] == "rogi_mitra"
    assert sent.json()["data"]["status"] == "sent"

    wrong_ack = integration_client.post(
        "/postoffice/acknowledge",
        json={"event_id": event["event_id"], "received_by": "wrong_app", "status": "received"},
        headers=headers(provider),
    )
    assert wrong_ack.status_code == 403

    acknowledged = integration_client.post(
        "/postoffice/acknowledge",
        json={"event_id": event["event_id"], "received_by": "rogi_mitra", "status": "received"},
        headers=headers(provider),
    )
    assert acknowledged.status_code == 200

    db = integration_client.testing_session_local()
    try:
        assert db.query(OutboundEvent).filter(OutboundEvent.event_id == event["event_id"]).count() == 0
        assert db.query(TimelineEvent).filter(TimelineEvent.event_id == event["event_id"]).count() == 1
        assert db.query(PostOfficeAcknowledgement).filter(
            PostOfficeAcknowledgement.event_id == event["event_id"]
        ).count() == 1
        assert db.query(AuditLog).filter(AuditLog.action == "postoffice.acknowledged").count() == 1
    finally:
        db.close()


def test_postoffice_is_idempotent_and_blocks_actor_spoofing(integration_client):
    patient = register_patient(integration_client, "9876501111")
    provider = register_provider(integration_client, "9876501112")
    grant_provider_access(integration_client, patient, provider)
    event = _message_event(patient, provider)

    first = integration_client.post("/postoffice/send", json=event, headers=headers(provider))
    second = integration_client.post("/postoffice/send", json=event, headers=headers(provider))
    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["data"]["duplicate"] is True

    spoofed = _message_event(patient, provider)
    spoofed["payload"]["actor_id"] = patient["user"]["id"]
    denied = integration_client.post("/postoffice/send", json=spoofed, headers=headers(provider))
    assert denied.status_code == 403


def test_postoffice_rejects_malformed_event_payloads(integration_client):
    patient = register_patient(integration_client, "9876501121")
    provider = register_provider(integration_client, "9876501122")
    grant_provider_access(integration_client, patient, provider)
    event = _message_event(patient, provider)
    del event["payload"]["message_text"]

    rejected = integration_client.post("/postoffice/send", json=event, headers=headers(provider))
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "VALIDATION_ERROR"
