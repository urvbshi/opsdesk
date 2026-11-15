import pytest
from app.database import SessionLocal
from app.models import Ticket, User
from app.linking import find_related_tickets


@pytest.fixture
def db_session():
    session = SessionLocal()
    yield session
    session.close()


def test_strong_link_same_tboh(db_session):
    """
    Test requirement 3: Strong = same TBOH (booking reference).
    In seed data, Tickets 1, 2, and 3 share TBOH 'TBOH-7701-DXB'.
    """
    ticket1 = db_session.query(Ticket).filter(Ticket.tboh == "TBOH-7701-DXB").first()
    assert ticket1 is not None

    related = find_related_tickets(ticket1, db_session)
    strong_list = related["strong"]

    # At least 1 other ticket should match same TBOH
    assert len(strong_list) >= 1
    for match in strong_list:
        assert match["ticket"].tboh == "TBOH-7701-DXB"
        assert match["ticket"].id != ticket1.id
        assert "Same booking reference" in match["reason"]


def test_weak_link_same_agency_same_intent(db_session):
    """
    Test requirement 3: Weak = same agency + same intent.
    Skyline Travels (agency 1) has multiple Refund and Date Change tickets with different TBOHs.
    """
    ticket4 = db_session.query(Ticket).filter(Ticket.tboh == "TBOH-8802-HTL").first()
    assert ticket4 is not None
    assert ticket4.intent == "Refund"

    related = find_related_tickets(ticket4, db_session)
    weak_list = related["weak"]

    assert len(weak_list) >= 1
    for match in weak_list:
        assert match["ticket"].agency_id == ticket4.agency_id
        assert match["ticket"].intent == ticket4.intent
        assert match["ticket"].tboh != ticket4.tboh
        assert "Same agency" in match["reason"]


def test_exclusivity_strong_not_duplicated_as_weak(db_session):
    """
    Tickets sharing the same TBOH should be classified as Strong links
    and must not be redundantly duplicated in Weak links.
    """
    ticket1 = db_session.query(Ticket).filter(Ticket.tboh == "TBOH-7701-DXB").first()
    related = find_related_tickets(ticket1, db_session)

    strong_ids = {m["ticket"].id for m in related["strong"]}
    weak_ids = {m["ticket"].id for m in related["weak"]}

    intersection = strong_ids.intersection(weak_ids)
    assert len(intersection) == 0, f"Tickets appeared in both strong and weak links: {intersection}"


def test_requester_linking_scoped_to_own_agency(db_session):
    """
    A Requester from Agency 1 should never see linked tickets from Agency 2.
    """
    requester = db_session.query(User).filter(User.username == "requester_skyline").first()
    ticket1 = db_session.query(Ticket).filter(Ticket.agency_id == 1).first()

    related = find_related_tickets(ticket1, db_session, viewer=requester)

    for match in related["strong"] + related["weak"]:
        assert match["ticket"].agency_id == 1
