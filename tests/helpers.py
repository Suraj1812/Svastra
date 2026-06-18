from app.reference_terms import get_reference_term


GENDER_FEMALE = get_reference_term("gender", "Female")
LANGUAGE_ENGLISH = get_reference_term("language", "English")
LANGUAGE_HINDI = get_reference_term("language", "Hindi")
OCCUPATION_PHYSICIAN = get_reference_term("occupation", "Physician")
RELATIONSHIP_FAMILY = get_reference_term("relationship", "Family member")


def _verify(client, mobile_number):
    assert client.post("/auth/otp/send", json={"mobile_number": mobile_number}).status_code == 200
    assert client.post(
        "/auth/otp/verify",
        json={"mobile_number": mobile_number, "otp": "123456"},
    ).status_code == 200


def register_patient(client, mobile_number="9876501001", full_name="Asha Patient"):
    _verify(client, mobile_number)
    response = client.post(
        "/auth/register/patient",
        json={
            "full_name": full_name,
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


def register_provider(client, mobile_number="9876501002", full_name="Dr Meera"):
    _verify(client, mobile_number)
    response = client.post(
        "/auth/register/provider",
        json={
            "full_name": full_name,
            "mobile_number": mobile_number,
            "professional_category": OCCUPATION_PHYSICIAN,
            "registration_number": f"REG-{mobile_number[-4:]}",
            "terms_accepted": True,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def register_caregiver(client, mobile_number="9876501003", full_name="Ravi Caregiver"):
    _verify(client, mobile_number)
    response = client.post(
        "/auth/register/caregiver",
        json={
            "full_name": full_name,
            "mobile_number": mobile_number,
            "relationship_to_patient": RELATIONSHIP_FAMILY,
            "preferred_language": LANGUAGE_HINDI,
            "terms_accepted": True,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def headers(auth_result):
    return {"X-Session-Token": auth_result["session"]["session_token"]}


def grant_provider_access(client, patient, provider):
    created = client.post(
        "/consent/request",
        json={"patient_id": patient["user"]["id"], "consent_type": "provider_access"},
        headers=headers(provider),
    )
    assert created.status_code == 201
    consent_id = created.json()["data"]["id"]
    granted = client.post(
        f"/consent/request/{consent_id}/grant",
        json={"confirmed": True},
        headers=headers(patient),
    )
    assert granted.status_code == 200
    return consent_id


def grant_caregiver_access(client, patient, caregiver):
    created = client.post(
        "/consent/request",
        json={"patient_id": patient["user"]["id"], "consent_type": "caregiver_access"},
        headers=headers(caregiver),
    )
    assert created.status_code == 201
    consent_id = created.json()["data"]["id"]
    granted = client.post(
        f"/consent/request/{consent_id}/grant",
        json={"confirmed": True},
        headers=headers(patient),
    )
    assert granted.status_code == 200
    return consent_id
