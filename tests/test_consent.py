import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import otp_provider
from app.database import Base, get_db
from app.main import app
from app.models import audit, consent, rbac, session, user  # noqa: F401


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
            "gender": "Female",
            "preferred_language": "English",
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
            "professional_category": "Physician",
            "registration_number": "REG-123",
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
        "/consent/request/demo-request/grant",
        json={"otp": "123456"},
        headers=headers,
    )
    assert grant_response.status_code == 403
    assert grant_response.json()["error"]["code"] == "FORBIDDEN"


def test_relationship_consent_request_placeholders_require_otp(client):
    registered = _register_patient(client, mobile_number="9876543293")
    headers = {"X-Session-Token": registered["session"]["session_token"]}

    requests_response = client.get("/consent/requests", headers=headers)
    assert requests_response.status_code == 200
    assert requests_response.json()["data"]["requests"] == []

    invalid_grant_response = client.post(
        "/consent/request/demo-request/grant",
        json={"otp": "000000"},
        headers=headers,
    )
    assert invalid_grant_response.status_code == 400

    grant_response = client.post(
        "/consent/request/demo-request/grant",
        json={"otp": "123456"},
        headers=headers,
    )
    assert grant_response.status_code == 200
    assert grant_response.json()["data"]["status"] == "GRANTED"

    reject_response = client.post(
        "/consent/request/demo-request/reject",
        json={"otp": "123456"},
        headers=headers,
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["data"]["status"] == "REJECTED"
