import pytest

from app.api.v1.accounts import get_auth_rate_limiter
from app.core.config import Settings, get_settings
from app.core.ratelimit import RateLimiter
from app.domains.accounts import hash_password, verify_password
from app.main import app

PASSWORD = "correct horse 42"


class _Unlimited(RateLimiter):
    def allow(self, key: str) -> bool:
        return True


@pytest.fixture()
def client(api_client):
    app.dependency_overrides[get_auth_rate_limiter] = lambda: _Unlimited()
    yield api_client


def _register(client, email="owner@example.com", company="Kisan Crop Sciences"):
    return client.post(
        "/api/v1/auth/register",
        json={"company_name": company, "email": email, "password": PASSWORD},
    )


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_a_password_hash_verifies_only_the_password_it_was_made_from():
    stored = hash_password(PASSWORD)
    assert verify_password(PASSWORD, stored)
    assert not verify_password("correct horse 43", stored)
    assert PASSWORD not in stored


def test_registering_creates_a_manufacturer_and_signs_its_owner_in(client):
    response = _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["token"].startswith("bt_")
    assert body["manufacturer"]["name"] == "Kisan Crop Sciences"

    me = client.get("/api/v1/me", headers=_bearer(body["token"]))
    assert me.status_code == 200
    assert me.json()["actor_id"] == "owner@example.com"
    assert me.json()["manufacturer_id"] == body["manufacturer"]["id"]
    assert "MANAGE_KEYS" in me.json()["capabilities"]


def test_an_email_can_register_only_once(client):
    assert _register(client).status_code == 201
    assert _register(client, email="OWNER@example.com", company="Other").status_code == 409


@pytest.mark.parametrize(
    "body",
    [
        {"company_name": "Acme", "email": "not-an-email", "password": PASSWORD},
        {"company_name": "Acme", "email": "a@example.com", "password": "short"},
        {"company_name": " ", "email": "a@example.com", "password": PASSWORD},
    ],
)
def test_registration_rejects_bad_details(client, body):
    assert client.post("/api/v1/auth/register", json=body).status_code == 400


def test_signing_in_needs_the_right_password(client):
    _register(client)
    wrong = client.post(
        "/api/v1/auth/sign-in", json={"email": "owner@example.com", "password": "nope nope nope"}
    )
    assert wrong.status_code == 401
    unknown = client.post(
        "/api/v1/auth/sign-in", json={"email": "nobody@example.com", "password": PASSWORD}
    )
    assert unknown.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]

    right = client.post(
        "/api/v1/auth/sign-in", json={"email": "Owner@Example.com", "password": PASSWORD}
    )
    assert right.status_code == 200


def test_a_session_only_reaches_its_own_manufacturer(client):
    first = _register(client).json()
    second = _register(client, email="other@example.com", company="Other Co").json()
    client.post(
        "/api/v1/products",
        json={"product_ref": "P-1", "name": "First only"},
        headers=_bearer(first["token"]),
    )
    seen = client.get("/api/v1/products", headers=_bearer(second["token"])).json()
    assert seen == []


def test_signing_out_ends_the_session(client):
    token = _register(client).json()["token"]
    assert client.post("/api/v1/auth/sign-out", headers=_bearer(token)).status_code == 204
    assert client.get("/api/v1/me", headers=_bearer(token)).status_code == 401


def test_an_unknown_token_is_refused(client):
    assert client.get("/api/v1/me", headers=_bearer("bt_made_up")).status_code == 401


def test_production_refuses_development_credentials_but_accepts_sessions(client):
    token = _register(client).json()["token"]
    manufacturer_id = client.get("/api/v1/me", headers=_bearer(token)).json()["manufacturer_id"]
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, environment="production"
    )

    dev = client.get("/api/v1/me", headers=_bearer(f"dev:{manufacturer_id}:mallory:*"))
    assert dev.status_code == 401
    assert client.get("/api/v1/me", headers=_bearer(token)).status_code == 200


def test_signing_with_a_handle_that_is_not_the_keys_is_refused(client):
    token = _register(client).json()["token"]
    headers = _bearer(token)
    product = client.post(
        "/api/v1/products",
        json={"product_ref": "P-1", "name": "Test", "gtin": "09520123456788"},
        headers=headers,
    ).json()
    batch = client.post(
        "/api/v1/batches",
        json={"product_id": product["id"], "batch_ref": "B-1", "manufacturing_date": "2026-10-01"},
        headers=headers,
    ).json()
    key = client.post("/api/v1/keys", json={"key_version": 1}, headers=headers).json()
    identity = client.post(
        "/api/v1/identities/reserve", json={"batch_id": batch["id"], "count": 1}, headers=headers
    ).json()[0]

    refused = client.post(
        f"/api/v1/identities/{identity['id']}/sign",
        json={"manufacturer_key_id": key["key"]["id"], "key_handle": "not-this-keys-handle"},
        headers=headers,
    )
    assert refused.status_code == 400

    signed = client.post(
        f"/api/v1/identities/{identity['id']}/sign",
        json={"manufacturer_key_id": key["key"]["id"], "key_handle": key["key_handle"]},
        headers=headers,
    )
    assert signed.status_code == 200
