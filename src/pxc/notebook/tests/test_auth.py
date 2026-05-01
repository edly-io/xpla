from fastapi.testclient import TestClient


def test_me_unauthenticated(client: TestClient) -> None:
    response = client.get("/api/me")
    assert response.status_code == 401


def test_signup_creates_account_and_sets_cookie(client: TestClient) -> None:
    response = client.post(
        "/api/auth/signup",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "alice@example.com"
    assert body["id"]
    assert "notebook_session" in response.cookies

    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


def test_signup_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/signup",
        json={"email": "short@example.com", "password": "short"},
    )
    assert response.status_code == 400


def test_signup_rejects_invalid_email(client: TestClient) -> None:
    response = client.post(
        "/api/auth/signup",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert response.status_code == 400


def test_signup_rejects_duplicate_email(client: TestClient) -> None:
    client.post(
        "/api/auth/signup",
        json={"email": "dup@example.com", "password": "password123"},
    )
    client.cookies.clear()
    response = client.post(
        "/api/auth/signup",
        json={"email": "dup@example.com", "password": "password123"},
    )
    assert response.status_code == 409


def test_login_with_valid_credentials(client: TestClient) -> None:
    client.post(
        "/api/auth/signup",
        json={"email": "bob@example.com", "password": "password123"},
    )
    client.cookies.clear()
    response = client.post(
        "/api/auth/login",
        json={"email": "bob@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "bob@example.com"
    assert client.get("/api/me").status_code == 200


def test_login_rejects_wrong_password(client: TestClient) -> None:
    client.post(
        "/api/auth/signup",
        json={"email": "carol@example.com", "password": "password123"},
    )
    client.cookies.clear()
    response = client.post(
        "/api/auth/login",
        json={"email": "carol@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_rejects_unknown_email(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "password123"},
    )
    assert response.status_code == 401


def test_logout_clears_session(client: TestClient) -> None:
    client.post(
        "/api/auth/signup",
        json={"email": "dave@example.com", "password": "password123"},
    )
    assert client.get("/api/me").status_code == 200
    response = client.post("/api/auth/logout")
    assert response.status_code == 204
    client.cookies.clear()
    assert client.get("/api/me").status_code == 401


def test_email_is_normalized_lowercase(client: TestClient) -> None:
    client.post(
        "/api/auth/signup",
        json={"email": "Eve@Example.COM", "password": "password123"},
    )
    client.cookies.clear()
    response = client.post(
        "/api/auth/login",
        json={"email": "eve@example.com", "password": "password123"},
    )
    assert response.status_code == 200


def test_signup_creates_api_token(client: TestClient) -> None:
    client.post(
        "/api/auth/signup",
        json={"email": "token@example.com", "password": "password123"},
    )
    response = client.get("/api/settings/api-token")
    assert response.status_code == 200
    assert "token" in response.json()
    assert len(response.json()["token"]) > 0


def test_login_ensures_api_token(client: TestClient) -> None:
    client.post(
        "/api/auth/signup",
        json={"email": "login_token@example.com", "password": "password123"},
    )
    client.cookies.clear()
    client.post(
        "/api/auth/login",
        json={"email": "login_token@example.com", "password": "password123"},
    )
    response = client.get("/api/settings/api-token")
    assert response.status_code == 200
    assert "token" in response.json()


def test_bearer_token_authenticates(client: TestClient) -> None:
    client.post(
        "/api/auth/signup",
        json={"email": "bearer@example.com", "password": "password123"},
    )
    token = client.get("/api/settings/api-token").json()["token"]
    client.cookies.clear()

    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "bearer@example.com"


def test_bearer_token_invalid_returns_401(client: TestClient) -> None:
    response = client.get("/api/me", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401


def test_regenerate_api_token(client: TestClient) -> None:
    client.post(
        "/api/auth/signup",
        json={"email": "regen@example.com", "password": "password123"},
    )
    old_token = client.get("/api/settings/api-token").json()["token"]

    response = client.post("/api/settings/api-token")
    assert response.status_code == 200
    new_token = response.json()["token"]
    assert new_token != old_token

    # Old token no longer valid
    client.cookies.clear()
    assert (
        client.get(
            "/api/me", headers={"Authorization": f"Bearer {old_token}"}
        ).status_code
        == 401
    )
    # New token works
    assert (
        client.get(
            "/api/me", headers={"Authorization": f"Bearer {new_token}"}
        ).status_code
        == 200
    )
