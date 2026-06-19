from datetime import datetime, timezone
from uuid import uuid4

from app.config import settings
from tests.helpers import (
    grant_caregiver_access,
    grant_provider_access,
    headers,
    register_caregiver,
    register_patient,
    register_provider,
)


def _message_event(patient, provider, *, event_id=None, message="Private clinical follow-up"):
    return {
        "event_type": "message.send",
        "event_id": event_id or f"evt_{uuid4().hex}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "mantrana_mitra",
        "payload": {
            "actor_id": provider["user"]["id"],
            "patient_id": patient["user"]["id"],
            "message_id": f"msg_{uuid4().hex}",
            "message_text": message,
        },
    }


def test_event_monitor_is_scoped_paginated_and_integrity_checked(integration_client):
    patient = register_patient(integration_client, "9876501301")
    provider = register_provider(integration_client, "9876501302")
    grant_provider_access(integration_client, patient, provider)
    event = _message_event(patient, provider)
    sent = integration_client.post("/postoffice/send", json=event, headers=headers(provider))
    assert sent.status_code == 202

    query = f"patient_id={patient['user']['id']}&limit=2"
    first_page = integration_client.get(
        f"/postoffice/monitor/events?{query}", headers=headers(provider)
    )
    assert first_page.status_code == 200
    page_data = first_page.json()["data"]
    assert page_data["page"]["count"] == 2
    assert page_data["page"]["has_more"] is True
    assert page_data["page"]["next_cursor"]
    assert all(item["integrity_status"] == "verified" for item in page_data["events"])
    assert all("payload" not in item for item in page_data["events"])

    second_page = integration_client.get(
        "/postoffice/monitor/events",
        params={
            "patient_id": patient["user"]["id"],
            "limit": 2,
            "cursor": page_data["page"]["next_cursor"],
        },
        headers=headers(provider),
    )
    assert second_page.status_code == 200
    first_ids = {item["event_id"] for item in page_data["events"]}
    second_ids = {item["event_id"] for item in second_page.json()["data"]["events"]}
    assert first_ids.isdisjoint(second_ids)

    summary = integration_client.get(
        "/postoffice/monitor/summary",
        params={"patient_id": patient["user"]["id"]},
        headers=headers(provider),
    )
    assert summary.status_code == 200
    summary_data = summary.json()["data"]
    assert summary_data["total_events"] >= 4
    assert summary_data["delivery_counts"]["sent"] >= 1
    assert summary_data["integrity_counts"]["mismatch"] == 0

    detail = integration_client.get(
        f"/postoffice/monitor/events/{event['event_id']}",
        params={"patient_id": patient["user"]["id"]},
        headers=headers(provider),
    )
    assert detail.status_code == 200
    detail_data = detail.json()["data"]
    assert detail_data["payload"]["message_text"] == "Private clinical follow-up"
    assert detail_data["payload_sha256"]
    assert detail_data["integrity_status"] == "verified"
    assert detail_data["lifecycle"][0]["state"] == "recorded"


def test_monitor_redacts_caregiver_payload_and_blocks_unlinked_users(integration_client):
    patient = register_patient(integration_client, "9876501311")
    provider = register_provider(integration_client, "9876501312")
    caregiver = register_caregiver(integration_client, "9876501313")
    outsider = register_provider(integration_client, "9876501314", "Dr Outsider")
    grant_provider_access(integration_client, patient, provider)
    grant_caregiver_access(integration_client, patient, caregiver)
    provider_event = _message_event(patient, provider, message="Provider-only instruction")
    assert integration_client.post(
        "/postoffice/send", json=provider_event, headers=headers(provider)
    ).status_code == 202
    event = _message_event(patient, caregiver, message="Sensitive patient instruction")
    event["source"] = "sahay_mitra"
    assert integration_client.post(
        "/postoffice/send", json=event, headers=headers(caregiver)
    ).status_code == 202

    caregiver_detail = integration_client.get(
        f"/postoffice/monitor/events/{event['event_id']}",
        params={"patient_id": patient["user"]["id"]},
        headers=headers(caregiver),
    )
    assert caregiver_detail.status_code == 200
    caregiver_data = caregiver_detail.json()["data"]
    assert caregiver_data["payload"]["message_text"] == "[REDACTED]"
    assert "payload.message_text" in caregiver_data["redacted_fields"]

    caregiver_stream = integration_client.get(
        "/postoffice/monitor/events",
        params={"patient_id": patient["user"]["id"]},
        headers=headers(caregiver),
    )
    assert caregiver_stream.status_code == 200
    visible_ids = {item["event_id"] for item in caregiver_stream.json()["data"]["events"]}
    assert event["event_id"] in visible_ids
    assert provider_event["event_id"] not in visible_ids

    denied = integration_client.get(
        "/postoffice/monitor/events",
        params={"patient_id": patient["user"]["id"]},
        headers=headers(outsider),
    )
    assert denied.status_code == 403


def test_monitor_rejects_tampered_cursor_unknown_filters_and_event_id_reuse(integration_client):
    patient = register_patient(integration_client, "9876501321")
    provider = register_provider(integration_client, "9876501322")
    grant_provider_access(integration_client, patient, provider)
    event = _message_event(patient, provider)
    assert integration_client.post(
        "/postoffice/send", json=event, headers=headers(provider)
    ).status_code == 202

    page = integration_client.get(
        "/postoffice/monitor/events",
        params={"patient_id": patient["user"]["id"], "limit": 1},
        headers=headers(provider),
    ).json()["data"]
    cursor = page["page"]["next_cursor"]
    assert cursor
    tampered = f"{cursor[:-1]}{'0' if cursor[-1] != '0' else '1'}"
    rejected_cursor = integration_client.get(
        "/postoffice/monitor/events",
        params={"patient_id": patient["user"]["id"], "limit": 1, "cursor": tampered},
        headers=headers(provider),
    )
    assert rejected_cursor.status_code == 400

    unknown_filter = integration_client.get(
        "/postoffice/monitor/events",
        params={"patient_id": patient["user"]["id"], "secret_filter": "yes"},
        headers=headers(provider),
    )
    assert unknown_filter.status_code == 422

    conflicting = _message_event(
        patient,
        provider,
        event_id=event["event_id"],
        message="Changed immutable content",
    )
    conflicting["payload"]["message_id"] = event["payload"]["message_id"]
    conflict_response = integration_client.post(
        "/postoffice/send", json=conflicting, headers=headers(provider)
    )
    assert conflict_response.status_code == 400


def test_duplicate_acknowledgement_still_requires_scope_and_retry_is_bounded(
    integration_client, monkeypatch
):
    patient = register_patient(integration_client, "9876501331")
    provider = register_provider(integration_client, "9876501332")
    outsider = register_provider(integration_client, "9876501333", "Dr Outsider")
    grant_provider_access(integration_client, patient, provider)
    event = _message_event(patient, provider)
    assert integration_client.post(
        "/postoffice/send", json=event, headers=headers(provider)
    ).status_code == 202
    ack_body = {
        "event_id": event["event_id"],
        "received_by": "rogi_mitra",
        "status": "received",
    }
    assert integration_client.post(
        "/postoffice/acknowledge", json=ack_body, headers=headers(provider)
    ).status_code == 200
    denied_duplicate = integration_client.post(
        "/postoffice/acknowledge", json=ack_body, headers=headers(outsider)
    )
    assert denied_duplicate.status_code == 403

    retry_event = _message_event(patient, provider)
    assert integration_client.post(
        "/postoffice/send", json=retry_event, headers=headers(provider)
    ).status_code == 202
    monkeypatch.setattr(settings, "postoffice_max_retries", 1)
    bounded = integration_client.post(
        f"/postoffice/events/{retry_event['event_id']}/retry",
        headers=headers(provider),
    )
    assert bounded.status_code == 400


def test_security_headers_and_request_size_limit(integration_client):
    response = integration_client.get("/")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert response.headers["x-request-id"]
    assert float(response.headers["x-process-time-ms"]) >= 0

    too_large = integration_client.post(
        "/auth/otp/send",
        content=b"{}",
        headers={"Content-Type": "application/json", "Content-Length": str(settings.max_request_bytes + 1)},
    )
    assert too_large.status_code == 413
    assert too_large.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
