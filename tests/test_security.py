import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, Ticket


@pytest.fixture
def client():
    return TestClient(app)


def test_requester_cross_agency_blocked(client):
    """
    Test requirement 5:
    A Requester editing the URL to another agency's ticket must get 403 Forbidden.
    """
    db = SessionLocal()
    # Ticket 9 belongs to Global Gateways (agency_id = 2)
    ticket_other = db.query(Ticket).filter(Ticket.agency_id == 2).first()
    db.close()

    assert ticket_other is not None, "Target ticket must exist in database"

    # Log in as requester_skyline (agency_id = 1)
    login_resp = client.post(
        "/login",
        data={"username": "requester_skyline", "password": "password123"},
        follow_redirects=False,
    )
    assert login_resp.status_code == 303
    cookie = login_resp.headers.get("set-cookie")

    # Attempt to access ticket belonging to another agency
    resp = client.get(f"/tickets/{ticket_other.id}", headers={"cookie": cookie})
    assert resp.status_code == 403, f"Expected 403 Forbidden, got {resp.status_code}"
    assert "Forbidden" in resp.text or "permission" in resp.text


def test_agent_can_access_all_agencies(client):
    """
    Agents and Leads can access tickets across all travel agencies.
    """
    db = SessionLocal()
    ticket_other = db.query(Ticket).filter(Ticket.agency_id == 2).first()
    db.close()

    # Log in as agent_alice (Agent)
    login_resp = client.post(
        "/login",
        data={"username": "agent_alice", "password": "password123"},
        follow_redirects=False,
    )
    assert login_resp.status_code == 303
    cookie = login_resp.headers.get("set-cookie")

    resp = client.get(f"/tickets/{ticket_other.id}", headers={"cookie": cookie})
    # Should not be 403 (could be 200 once detail page is rendered)
    assert resp.status_code != 403
