import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import auth_service, otp_provider
from app.database import Base, get_db
from app.main import app
from app.models import audit, consent, rbac, session, user  # noqa: F401
from app.rbac.permission_validator import check_permission
from app.rbac.rbac_service import get_role_permissions
from app.schemas.registration import ProviderRegistration


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


def _register_provider(client, mobile_number="9876543291"):
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


def test_role_permissions_matrix_matches_tuesday_spec():
    provider_permissions = {permission.code for permission in get_role_permissions("provider")}
    patient_permissions = {permission.code for permission in get_role_permissions("patient")}
    caregiver_permissions = {permission.code for permission in get_role_permissions("caregiver")}
    admin_permissions = {permission.code for permission in get_role_permissions("admin")}

    assert provider_permissions == {
        "VIEW_PATIENTS",
        "CREATE_CARE_PLANS",
        "VIEW_TIMELINE",
        "VIEW_ALERTS",
        "REQUEST_PATIENT_ACCESS",
    }
    assert patient_permissions == {
        "VIEW_TASKS",
        "RESPOND_TO_TASKS",
        "VIEW_TIMELINE",
        "MANAGE_CONSENT",
    }
    assert caregiver_permissions == {
        "VIEW_PATIENT_STATUS",
        "VIEW_TIMELINE",
        "RECEIVE_NOTIFICATIONS",
        "REQUEST_CAREGIVER_ACCESS",
    }
    assert admin_permissions == {"SYSTEM_ADMINISTRATION"}
    assert check_permission("provider", "VIEW_PATIENTS") is True
    assert check_permission("provider", "MANAGE_CONSENT") is False


def test_me_permissions_requires_valid_session_and_returns_role_permissions(client):
    missing_session = client.get("/me/permissions")
    assert missing_session.status_code == 401
    assert missing_session.json()["error"]["code"] == "UNAUTHORIZED"

    registered = _register_provider(client)
    response = client.get(
        "/me/permissions",
        headers={"X-Session-Token": registered["session"]["session_token"]},
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["role"] == "provider"
    permission_codes = {permission["code"] for permission in body["permissions"]}
    assert "VIEW_PATIENTS" in permission_codes
    assert "REQUEST_PATIENT_ACCESS" in permission_codes
