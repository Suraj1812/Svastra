import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import otp_provider
from app.database import Base, get_db
from app.main import app
from app.models import audit, consent, rbac, session, user  # noqa: F401
from app.reference_terms import get_reference_term


GENDER_FEMALE = get_reference_term("gender", "Female")
LANGUAGE_ENGLISH = get_reference_term("language", "English")
LANGUAGE_HINDI = get_reference_term("language", "Hindi")
OCCUPATION_PHYSICIAN = get_reference_term("occupation", "Physician")
RELATIONSHIP_FAMILY = get_reference_term("relationship", "Family member")


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    otp_provider.reset_verifications()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    otp_provider.reset_verifications()


def _register_patient(client, mobile_number="9876543292"):
    client.post("/auth/otp/send", json={"mobile_number": mobile_number})
    client.post("/auth/otp/verify", json={"mobile_number": mobile_number, "otp": "123456"})
    response = client.post(
        "/auth/register/patient",
        json={
            "full_name": "Asha Patient",
            "mobile_number": mobile_number,
            "date_of_birth": "1992-05-17",
            "gender": GENDER_FEMALE,
            "preferred_language": LANGUAGE_ENGLISH,
            "terms_accepted": True,
            "unified_consent_accepted": True,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def _register_provider(client, mobile_number="9876543294"):
    client.post("/auth/otp/send", json={"mobile_number": mobile_number})
    client.post("/auth/otp/verify", json={"mobile_number": mobile_number, "otp": "123456"})
    response = client.post(
        "/auth/register/provider",
        json={
            "full_name": "Dr Meera",
            "mobile_number": mobile_number,
            "professional_category": OCCUPATION_PHYSICIAN,
            "registration_number": "REG-123",
            "terms_accepted": True,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def _register_caregiver(client, mobile_number="9876543295"):
    client.post("/auth/otp/send", json={"mobile_number": mobile_number})
    client.post("/auth/otp/verify", json={"mobile_number": mobile_number, "otp": "123456"})
    response = client.post(
        "/auth/register/caregiver",
        json={
            "full_name": "Ravi Caregiver",
            "mobile_number": mobile_number,
            "relationship_to_patient": RELATIONSHIP_FAMILY,
            "preferred_language": LANGUAGE_HINDI,
            "terms_accepted": True,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_platform_consent_status_and_accept_endpoint(client):
    registered = _register_patient(client)
    headers = {"X-Session-Token": registered["session"]["session_token"]}

    status_response = client.get("/me/consent-status", headers=headers)
    assert status_response.status_code == 200
    status_data = status_response.json()["data"]
    assert status_data["accepted"] is True
    assert status_data["consent_status"] == "Accepted"
    assert status_data["current_consent_version"] == "v1"

    accept_response = client.post(
        "/consent/platform/accept",
        json={},
        headers=headers,
    )
    assert accept_response.status_code == 201
    assert accept_response.json()["data"]["consent_version"] == "v1"


def test_patient_consent_endpoints_reject_non_patient_sessions(client):
    registered = _register_provider(client)
    headers = {"X-Session-Token": registered["session"]["session_token"]}

    status_response = client.get("/me/consent-status", headers=headers)
    assert status_response.status_code == 403
    assert status_response.json()["error"]["code"] == "FORBIDDEN"

    requests_response = client.get("/consent/requests", headers=headers)
    assert requests_response.status_code == 403
    assert requests_response.json()["error"]["code"] == "FORBIDDEN"

    grant_response = client.post(
        "/consent/request/999999/grant",
        json={"otp": "123456"},
        headers=headers,
    )
    assert grant_response.status_code == 403
    assert grant_response.json()["error"]["code"] == "FORBIDDEN"


def test_relationship_consent_request_decision_and_revoke_flow(client):
    registered = _register_patient(client, mobile_number="9876543293")
    provider = _register_provider(client, mobile_number="9876543296")
    patient_headers = {"X-Session-Token": registered["session"]["session_token"]}
    provider_headers = {"X-Session-Token": provider["session"]["session_token"]}

    create_response = client.post(
        "/consent/request",
        json={
            "patient_id": registered["user"]["id"],
            "consent_type": "provider_access",
        },
        headers=provider_headers,
    )
    assert create_response.status_code == 201
    created = create_response.json()["data"]
    assert created["status"] == "PENDING"
    assert created["alias"] == "Dr Meera"

    requests_response = client.get("/consent/pending", headers=patient_headers)
    assert requests_response.status_code == 200
    assert requests_response.json()["data"]["requests"][0]["id"] == created["id"]

    legacy_requests_response = client.get("/consent/requests", headers=patient_headers)
    assert legacy_requests_response.status_code == 200
    assert legacy_requests_response.json()["data"]["requests"][0]["status"] == "PENDING"

    detail_response = client.get(f"/consent/{created['id']}", headers=patient_headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["mobile_number"] == provider["user"]["mobile_number"]

    alias_response = client.put(
        f"/consent/{created['id']}/alias",
        json={"alias": "Primary physician"},
        headers=patient_headers,
    )
    assert alias_response.status_code == 200
    assert alias_response.json()["data"]["alias"] == "Primary physician"

    otp_response = client.post(
        "/consent/send-otp",
        json={"consent_id": created["id"], "action": "grant"},
        headers=patient_headers,
    )
    assert otp_response.status_code == 200
    assert otp_response.json()["data"]["otp_sent"] is True

    invalid_grant_response = client.post(
        f"/consent/request/{created['id']}/grant",
        json={"otp": "000000"},
        headers=patient_headers,
    )
    assert invalid_grant_response.status_code == 400

    verify_response = client.post(
        "/consent/verify-otp",
        json={"consent_id": created["id"], "action": "grant", "otp": "123456"},
        headers=patient_headers,
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["data"]["otp_verified"] is True

    grant_response = client.post(
        f"/consent/request/{created['id']}/grant",
        json={"otp": "123456"},
        headers=patient_headers,
    )
    assert grant_response.status_code == 200
    assert grant_response.json()["data"]["status"] == "ACTIVE"

    active_response = client.get("/consent/active", headers=patient_headers)
    assert active_response.status_code == 200
    assert active_response.json()["data"]["consents"][0]["status"] == "ACTIVE"

    revoke_response = client.post(
        f"/consent/request/{created['id']}/revoke",
        json={"otp": "123456"},
        headers=patient_headers,
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["data"]["status"] == "REVOKED"

    inactive_response = client.get("/consent/inactive", headers=patient_headers)
    assert inactive_response.status_code == 200
    assert inactive_response.json()["data"]["consents"][0]["status"] == "REVOKED"


def test_relationship_consent_reject_flow(client):
    registered = _register_patient(client, mobile_number="9876543297")
    caregiver = _register_caregiver(client, mobile_number="9876543298")
    patient_headers = {"X-Session-Token": registered["session"]["session_token"]}
    caregiver_headers = {"X-Session-Token": caregiver["session"]["session_token"]}

    create_response = client.post(
        "/consent/request",
        json={
            "patient_id": registered["user"]["id"],
            "consent_type": "caregiver_access",
        },
        headers=caregiver_headers,
    )
    assert create_response.status_code == 201
    created = create_response.json()["data"]

    reject_response = client.post(
        f"/consent/request/{created['id']}/reject",
        json={"otp": "123456"},
        headers=patient_headers,
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["data"]["status"] == "REJECTED"

    inactive_response = client.get("/consent/inactive", headers=patient_headers)
    assert inactive_response.status_code == 200
    assert inactive_response.json()["data"]["consents"][0]["status"] == "REJECTED"

    requests_response = client.get("/consent/pending", headers=patient_headers)
    assert requests_response.status_code == 200
    assert requests_response.json()["data"]["requests"] == []
