from datetime import date, datetime, timedelta

import pytest

GTIN = "09520123456788"


def _auth(manufacturer_id, capabilities="*", actor="alice"):
    return {"Authorization": f"Bearer dev:{manufacturer_id}:{actor}:{capabilities}"}


@pytest.fixture()
def manufacturer(api_client):
    response = api_client.post("/api/v1/manufacturers", json={"name": "API Test Co"})
    assert response.status_code == 201
    return response.json()


def test_an_unauthenticated_request_is_rejected(api_client):
    assert api_client.get("/api/v1/products").status_code == 401


def test_a_malformed_credential_is_rejected(api_client):
    response = api_client.get(
        "/api/v1/products", headers={"Authorization": "Bearer nonsense"}
    )
    assert response.status_code == 401


def test_me_reports_the_resolved_actor(api_client, manufacturer):
    response = api_client.get(
        "/api/v1/me", headers=_auth(manufacturer["id"], "AUTHORIZE_SIGNING")
    )
    assert response.status_code == 200
    assert response.json()["actor_id"] == "alice"
    assert response.json()["capabilities"] == ["AUTHORIZE_SIGNING"]


def test_production_order_authority_does_not_grant_signing(api_client, manufacturer):
    headers = _auth(manufacturer["id"], "CREATE_PRODUCTION_ORDER")
    product = api_client.post(
        "/api/v1/products",
        json={"product_ref": "P-1", "name": "Test", "gtin": GTIN},
        headers=headers,
    )
    assert product.status_code == 201

    denied = api_client.post(
        "/api/v1/keys", json={"key_version": 1}, headers=headers
    )
    assert denied.status_code == 403


def test_full_production_and_verification_flow(api_client, manufacturer):
    headers = _auth(manufacturer["id"])

    key = api_client.post("/api/v1/keys", json={"key_version": 1}, headers=headers)
    assert key.status_code == 201
    key_body = key.json()

    product = api_client.post(
        "/api/v1/products",
        json={"product_ref": "P-1", "name": "Test Product", "gtin": GTIN},
        headers=headers,
    )
    assert product.status_code == 201

    batch = api_client.post(
        "/api/v1/batches",
        json={
            "product_id": product.json()["id"],
            "batch_ref": "B-1",
            "manufacturing_date": date(2026, 1, 1).isoformat(),
            "expiry_date": date(2028, 1, 1).isoformat(),
        },
        headers=headers,
    )
    assert batch.status_code == 201

    reserved = api_client.post(
        "/api/v1/identities/reserve",
        json={"batch_id": batch.json()["id"], "count": 2},
        headers=headers,
    )
    assert reserved.status_code == 201
    identities = reserved.json()
    assert len(identities) == 2
    assert len({i["serial"] for i in identities}) == 2
    assert all(len(i["serial"]) == 26 for i in identities)

    identity_id = identities[0]["id"]
    signed = api_client.post(
        f"/api/v1/identities/{identity_id}/sign",
        json={
            "manufacturer_key_id": key_body["key"]["id"],
            "key_handle": key_body["key_handle"],
        },
        headers=headers,
    )
    assert signed.status_code == 200
    assert signed.json()["lifecycle_state"] == "SIGNED"

    for state in ["PRINTED", "PRINT_VERIFIED", "RECONCILED", "ACTIVATED"]:
        moved = api_client.post(
            f"/api/v1/identities/{identity_id}/transition",
            json={"new_state": state},
            headers=headers,
        )
        assert moved.status_code == 200, moved.text
    assert moved.json()["lifecycle_state"] == "ACTIVATED"

    link = api_client.get(
        f"/api/v1/identities/{identity_id}/digital-link", headers=headers
    )
    assert link.status_code == 200
    assert f"/01/{GTIN}" in link.json()["uri"]
    assert "bhs=" in link.json()["uri"]

    verified = api_client.post(
        "/api/v1/verify", json={"digital_link": link.json()["uri"]}
    )
    assert verified.status_code == 200
    assert verified.json()["state"] == "GENUINE"


def test_an_unactivated_identity_does_not_verify_as_genuine(api_client, manufacturer):
    headers = _auth(manufacturer["id"])
    key = api_client.post("/api/v1/keys", json={"key_version": 1}, headers=headers).json()
    product = api_client.post(
        "/api/v1/products",
        json={"product_ref": "P-2", "name": "Test", "gtin": GTIN},
        headers=headers,
    ).json()
    batch = api_client.post(
        "/api/v1/batches",
        json={
            "product_id": product["id"],
            "batch_ref": "B-2",
            "manufacturing_date": date(2026, 1, 1).isoformat(),
        },
        headers=headers,
    ).json()
    identity = api_client.post(
        "/api/v1/identities/reserve",
        json={"batch_id": batch["id"], "count": 1},
        headers=headers,
    ).json()[0]
    api_client.post(
        f"/api/v1/identities/{identity['id']}/sign",
        json={"manufacturer_key_id": key["key"]["id"], "key_handle": key["key_handle"]},
        headers=headers,
    )

    verified = api_client.post("/api/v1/verify", json={"serial": identity["serial"]})
    assert verified.json()["state"] == "INVALID"


def test_an_illegal_lifecycle_transition_is_a_conflict(api_client, manufacturer):
    headers = _auth(manufacturer["id"])
    product = api_client.post(
        "/api/v1/products",
        json={"product_ref": "P-3", "name": "Test"},
        headers=headers,
    ).json()
    batch = api_client.post(
        "/api/v1/batches",
        json={
            "product_id": product["id"],
            "batch_ref": "B-3",
            "manufacturing_date": date(2026, 1, 1).isoformat(),
        },
        headers=headers,
    ).json()
    identity = api_client.post(
        "/api/v1/identities/reserve",
        json={"batch_id": batch["id"], "count": 1},
        headers=headers,
    ).json()[0]

    response = api_client.post(
        f"/api/v1/identities/{identity['id']}/transition",
        json={"new_state": "ACTIVATED"},
        headers=headers,
    )
    assert response.status_code == 409


def test_a_product_without_a_gtin_cannot_produce_a_digital_link(api_client, manufacturer):
    headers = _auth(manufacturer["id"])
    product = api_client.post(
        "/api/v1/products",
        json={"product_ref": "P-4", "name": "No GTIN"},
        headers=headers,
    ).json()
    batch = api_client.post(
        "/api/v1/batches",
        json={
            "product_id": product["id"],
            "batch_ref": "B-4",
            "manufacturing_date": date(2026, 1, 1).isoformat(),
        },
        headers=headers,
    ).json()
    identity = api_client.post(
        "/api/v1/identities/reserve",
        json={"batch_id": batch["id"], "count": 1},
        headers=headers,
    ).json()[0]

    response = api_client.get(
        f"/api/v1/identities/{identity['id']}/digital-link", headers=headers
    )
    assert response.status_code == 409


def test_another_manufacturers_resource_is_not_found_rather_than_forbidden(
    api_client, manufacturer
):
    other = api_client.post(
        "/api/v1/manufacturers", json={"name": "Other Co"}
    ).json()

    product = api_client.post(
        "/api/v1/products",
        json={"product_ref": "P-5", "name": "Owned"},
        headers=_auth(manufacturer["id"]),
    ).json()

    response = api_client.post(
        "/api/v1/batches",
        json={
            "product_id": product["id"],
            "batch_ref": "B-5",
            "manufacturing_date": date(2026, 1, 1).isoformat(),
        },
        headers=_auth(other["id"], actor="mallory"),
    )
    assert response.status_code == 404


def test_the_public_response_never_carries_internal_detail(api_client, manufacturer):
    response = api_client.post("/api/v1/verify", json={"serial": "AAAAAAAAAAAAAAAAAAAAAAAAAA"})
    assert set(response.json()) == {"state", "message", "checked_at"}


def test_an_unknown_and_a_malformed_serial_are_indistinguishable(api_client):
    unknown = api_client.post(
        "/api/v1/verify", json={"serial": "AAAAAAAAAAAAAAAAAAAAAAAAAA"}
    ).json()
    malformed = api_client.post("/api/v1/verify", json={"serial": "nope"}).json()
    assert unknown["state"] == malformed["state"] == "INVALID"
    assert unknown["message"] == malformed["message"]


def test_supply_chain_events_and_custodian_projection(api_client, manufacturer):
    headers = _auth(manufacturer["id"])
    key = api_client.post("/api/v1/keys", json={"key_version": 1}, headers=headers).json()
    product = api_client.post(
        "/api/v1/products",
        json={"product_ref": "P-6", "name": "Test", "gtin": GTIN},
        headers=headers,
    ).json()
    batch = api_client.post(
        "/api/v1/batches",
        json={
            "product_id": product["id"],
            "batch_ref": "B-6",
            "manufacturing_date": date(2026, 1, 1).isoformat(),
        },
        headers=headers,
    ).json()
    identity = api_client.post(
        "/api/v1/identities/reserve",
        json={"batch_id": batch["id"], "count": 1},
        headers=headers,
    ).json()[0]
    api_client.post(
        f"/api/v1/identities/{identity['id']}/sign",
        json={"manufacturer_key_id": key["key"]["id"], "key_handle": key["key_handle"]},
        headers=headers,
    )

    depot = api_client.post(
        "/api/v1/supply-chain/participants",
        json={"participant_ref": "D-1", "name": "Depot", "role": "DEPOT"},
        headers=headers,
    )
    assert depot.status_code == 201

    event = api_client.post(
        "/api/v1/supply-chain/events",
        json={
            "identity_id": identity["id"],
            "event_type": "DISPATCH",
            "occurred_at": (datetime.now().astimezone() - timedelta(days=1)).isoformat(),
            "destination_participant_id": depot.json()["id"],
        },
        headers=headers,
    )
    assert event.status_code == 201, event.text

    custodian = api_client.get(
        f"/api/v1/supply-chain/identities/{identity['id']}/custodian", headers=headers
    )
    assert custodian.json()["custodian_id"] == depot.json()["id"]
