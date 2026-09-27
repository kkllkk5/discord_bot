import os
import sys

from fastapi.testclient import TestClient

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from server import app


client = TestClient(app)


def test_dashboard_overview_exposes_prototype_state():
    response = client.get("/api/dashboard/overview")

    assert response.status_code == 200
    assert response.json()["service_status"] == "online"
    assert response.json()["bot_status"] == "not_connected"
    assert response.json()["feature_count"] >= 1


def test_dashboard_read_only_endpoints_return_expected_data():
    status = client.get("/api/dashboard/bot-status")
    features = client.get("/api/dashboard/features")
    logs = client.get("/api/dashboard/logs")

    assert status.status_code == 200
    assert status.json()["status"] == "not_connected"
    assert features.status_code == 200
    assert any(feature["name"] == "食事画像のAI解析" for feature in features.json())
    assert logs.status_code == 200
    assert logs.json()[0]["level"] == "INFO"


def test_dashboard_page_is_available_in_a_browser():
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "Discord Bot Dashboard" in response.text
