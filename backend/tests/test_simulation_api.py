def _auth(manufacturer_id, capabilities="*", actor="alice"):
    return {"Authorization": f"Bearer dev:{manufacturer_id}:{actor}:{capabilities}"}


def _manufacturer(api_client, name="Simulation API Test Co"):
    response = api_client.post("/api/v1/manufacturers", json={"name": name})
    assert response.status_code == 201
    return response.json()


def test_scenario_catalogue_is_public_and_lists_every_scenario(api_client):
    response = api_client.get("/api/v1/simulations/catalogue")
    assert response.status_code == 200
    scenario_types = {entry["scenario_type"] for entry in response.json()}
    assert scenario_types == {
        "LEGITIMATE_BASELINE",
        "FULL_COUNTERFEIT",
        "CODE_CLONING",
        "REFILLING",
        "DIVERSION",
        "COMBINED_MULTI_SIGNAL",
        "BENIGN_ANOMALY",
    }


def test_creating_a_simulation_requires_the_capability(api_client):
    manufacturer = _manufacturer(api_client)
    response = api_client.post(
        "/api/v1/simulations",
        json={"scenario_type": "LEGITIMATE_BASELINE", "seed": 1, "identity_count": 2},
        headers=_auth(manufacturer["id"], "CREATE_PRODUCTION_ORDER"),
    )
    assert response.status_code == 403


def test_create_and_fetch_a_simulation_run(api_client):
    manufacturer = _manufacturer(api_client)
    headers = _auth(manufacturer["id"])

    created = api_client.post(
        "/api/v1/simulations",
        json={"scenario_type": "DIVERSION", "seed": 321, "identity_count": 6},
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "COMPLETED"
    assert len(body["ground_truth"]) == 6
    assert body["latest_evaluation"] is not None
    assert body["latest_evaluation"]["true_positive_count"] >= 1

    run_id = body["id"]

    fetched = api_client.get(f"/api/v1/simulations/{run_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == run_id

    ground_truth = api_client.get(
        f"/api/v1/simulations/{run_id}/ground-truth", headers=headers
    )
    assert ground_truth.status_code == 200
    assert len(ground_truth.json()) == 6

    evaluation = api_client.get(f"/api/v1/simulations/{run_id}/evaluation", headers=headers)
    assert evaluation.status_code == 200
    assert evaluation.json()["sequence"] == 1


def test_recompute_evaluation_appends_a_new_version(api_client):
    manufacturer = _manufacturer(api_client)
    headers = _auth(manufacturer["id"])

    created = api_client.post(
        "/api/v1/simulations",
        json={"scenario_type": "CODE_CLONING", "seed": 55, "identity_count": 6},
        headers=headers,
    )
    run_id = created.json()["id"]

    recomputed = api_client.post(f"/api/v1/simulations/{run_id}/evaluation", headers=headers)
    assert recomputed.status_code == 201
    assert recomputed.json()["sequence"] == 2


def test_invalid_identity_count_is_rejected(api_client):
    manufacturer = _manufacturer(api_client)
    headers = _auth(manufacturer["id"])

    response = api_client.post(
        "/api/v1/simulations",
        json={"scenario_type": "LEGITIMATE_BASELINE", "identity_count": 0},
        headers=headers,
    )
    assert response.status_code == 422


def test_a_simulation_run_is_not_visible_to_a_different_manufacturer(api_client):
    manufacturer_a = _manufacturer(api_client, name="Simulation API Tenant A")
    manufacturer_b = _manufacturer(api_client, name="Simulation API Tenant B")

    created = api_client.post(
        "/api/v1/simulations",
        json={"scenario_type": "LEGITIMATE_BASELINE", "seed": 1, "identity_count": 2},
        headers=_auth(manufacturer_a["id"]),
    )
    run_id = created.json()["id"]

    response = api_client.get(
        f"/api/v1/simulations/{run_id}", headers=_auth(manufacturer_b["id"])
    )
    assert response.status_code == 404
