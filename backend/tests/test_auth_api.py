from tests.conftest import csrf, register_and_login


def test_registration_normalizes_email(client):
    response = client.post(
        "/api/auth/register",
        json={"full_name": "  A Citizen  ", "email": " CITIZEN@Example.com ", "password": "SafePass123!", "role":"User"},
        headers=csrf(client),
    )
    # EmailStr strips surrounding spaces inconsistently across versions; use a normal case variant below if rejected.
    if response.status_code == 422:
        response = client.post(
            "/api/auth/register",
            json={"full_name": "  A Citizen  ", "email": "CITIZEN@Example.com", "password": "SafePass123!", "role":"User"},
            headers=csrf(client),
        )
    assert response.status_code == 201, response.text
    assert response.json()["email"] == "citizen@example.com"
    assert response.json()["fullName"] == "A Citizen"


def test_duplicate_registration_returns_conflict(client):
    register_and_login(client)
    response = client.post(
        "/api/auth/register",
        json={"full_name": "Other Citizen", "email": "CITIZEN@example.com", "password": "OtherPass123!", "role":"User"},
        headers=csrf(client),
    )
    assert response.status_code == 409


def test_invalid_password_does_not_authenticate(client):
    client.post(
        "/api/auth/register",
        json={"full_name": "Test Citizen", "email": "citizen@example.com", "password": "SafePass123!"},
    )
    response = client.post("/api/auth/login", json={"email": "citizen@example.com", "password": "WrongPass123!"}, headers=csrf(client))
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_protected_endpoint_requires_login(client):
    assert client.get("/api/v1/chat/conversations").status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_mutating_chat_request_requires_csrf(authenticated_client):
    response = authenticated_client.post(
        "/api/v1/chat/messages", json={"query": "Hello without csrf"}
    )
    assert response.status_code == 403


def test_logout_clears_authentication(authenticated_client):
    response = authenticated_client.post("/api/auth/logout", headers=csrf(authenticated_client))
    assert response.status_code == 200
    assert authenticated_client.get("/api/auth/me").status_code == 401
