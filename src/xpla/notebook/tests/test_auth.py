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
    assert "xpln_session" in response.cookies

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
