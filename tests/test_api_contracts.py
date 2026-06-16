import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import otp_provider
from app.database import Base, get_db
from app.main import app
from app.models import audit, consent, session, user  # noqa: F401


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


def test_patient_api_flow_enforces_consent_and_sessions(client):
    otp_response = client.post("/auth/otp/send", json={"mobile_number": "9876543200"})
    assert otp_response.status_code == 200
    assert otp_response.json()["success"] is True

    verify_response = client.post(
        "/auth/otp/verify",
        json={"mobile_number": "9876543200", "otp": "123456"},
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["data"]["otp_verified"] is True

    rejected_response = client.post(
        "/auth/register/patient",
        json={
            "full_name": "Asha Patient",
            "mobile_number": "9876543200",
            "date_of_birth": "1992-05-17",
            "gender": "Female",
            "preferred_language": "English",
            "terms_accepted": True,
            "unified_consent_accepted": False,
        },
    )
    assert rejected_response.status_code == 422
    assert rejected_response.json()["success"] is False
    assert rejected_response.json()["error"]["code"] == "VALIDATION_ERROR"

    registered_response = client.post(
        "/auth/register/patient",
        json={
            "full_name": "Asha Patient",
            "mobile_number": "9876543200",
            "date_of_birth": "1992-05-17",
            "gender": "Female",
            "preferred_language": "English",
            "terms_accepted": True,
            "unified_consent_accepted": True,
        },
    )
    assert registered_response.status_code == 201
    registered = registered_response.json()["data"]
    assert registered["user"]["role"] == "patient"
    assert registered["dashboard_route"] == "/dashboards/rogi"
    assert registered["consent"]["patient_id"] == registered["user"]["id"]

    status_response = client.get(f"/consent/patients/{registered['user']['id']}/status")
    assert status_response.status_code == 200
    assert status_response.json()["data"]["accepted"] is True

    validate_response = client.post(
        "/auth/session/validate",
        json={"session_token": registered["session"]["session_token"]},
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["data"]["dashboard_route"] == "/dashboards/rogi"

    logout_response = client.post(
        "/auth/logout",
        json={"session_token": registered["session"]["session_token"]},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()["data"]["logged_out"] is True

    invalid_session_response = client.post(
        "/auth/session/validate",
        json={"session_token": registered["session"]["session_token"]},
    )
    assert invalid_session_response.status_code == 401
    assert invalid_session_response.json()["error"]["code"] == "UNAUTHORIZED"


def test_invalid_otp_returns_structured_error(client):
    client.post("/auth/otp/send", json={"mobile_number": "9876543204"})
    response = client.post(
        "/auth/otp/verify",
        json={"mobile_number": "9876543204", "otp": "000000"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "BAD_REQUEST"
    assert body["error"]["request_id"]


def test_provider_and_caregiver_api_flows_route_to_expected_dashboards(client):
    client.post("/auth/otp/send", json={"mobile_number": "9876543205"})
    client.post("/auth/otp/verify", json={"mobile_number": "9876543205", "otp": "123456"})
    provider_response = client.post(
        "/auth/register/provider",
        json={
            "full_name": "Dr Meera",
            "mobile_number": "9876543205",
            "professional_category": "Physician",
            "registration_number": "REG-123",
            "terms_accepted": True,
        },
    )

    assert provider_response.status_code == 201
    provider = provider_response.json()["data"]
    assert provider["dashboard_route"] == "/dashboards/mantrana"

    client.post("/auth/otp/send", json={"mobile_number": "9876543206"})
    client.post("/auth/otp/verify", json={"mobile_number": "9876543206", "otp": "123456"})
    caregiver_response = client.post(
        "/auth/register/caregiver",
        json={
            "full_name": "Ravi Caregiver",
            "mobile_number": "9876543206",
            "relationship_to_patient": "Family member",
            "preferred_language": "Hindi",
            "terms_accepted": True,
        },
    )

    assert caregiver_response.status_code == 201
    caregiver = caregiver_response.json()["data"]
    assert caregiver["dashboard_route"] == "/dashboards/sahay"
