from pathlib import Path

from app.main import app


def test_api_contract_documents_every_live_operation():
    contract = Path("api_contract.md").read_text(encoding="utf-8")
    missing = []
    for path, operations in app.openapi()["paths"].items():
        for method in operations:
            if method in {"get", "post", "put", "delete", "patch"}:
                signature = f"{method.upper()} {path}"
                if signature not in contract:
                    missing.append(signature)
    assert missing == []


def test_api_contract_uses_revised_session_consent_model():
    contract = Path("api_contract.md").read_text(encoding="utf-8")
    assert "Body: `{'confirmed':true}`" not in contract  # Guard against invalid single-quoted JSON.
    assert "`confirmed: true`" in contract
    assert "do not request a second OTP" in contract
    assert "/consent/send-otp" not in contract
    assert "/consent/verify-otp" not in contract
