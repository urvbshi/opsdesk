from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models import Ticket, User


def find_related_tickets(
    ticket: Ticket,
    db: Session,
    viewer: Optional[User] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Discovers related tickets for a given ticket based on context rules:
    
    1. Strong Match:
       - Same TBOH (Booking Reference).
       - Reason: "Same booking reference ({tboh})"
       
    2. Weak Match:
       - Same Agency AND Same Intent (with different TBOH).
       - Reason: "Same agency ({agency}) & intent category ({intent})"

    Security Scoping:
    - If the viewer is a Requester, candidates from other agencies are excluded.
    - Excludes the ticket itself.
    - Sorts by creation time descending (most recent first).
    """
    # Exclude the current ticket itself
    query = db.query(Ticket).filter(Ticket.id != ticket.id)

    # If the current ticket is already saved, prioritize older tickets
    if ticket.id is not None and ticket.created_at is not None:
        query = query.filter(Ticket.created_at <= ticket.created_at)

    # Requester visibility boundary
    if viewer and viewer.role == "Requester":
        query = query.filter(Ticket.agency_id == viewer.agency_id)

    candidates = query.order_by(Ticket.created_at.desc()).all()

    strong_matches: List[Dict[str, Any]] = []
    weak_matches: List[Dict[str, Any]] = []

    target_tboh = (ticket.tboh or "").strip().upper()

    for cand in candidates:
        cand_tboh = (cand.tboh or "").strip().upper()

        if cand_tboh == target_tboh:
            strong_matches.append({
                "ticket": cand,
                "type": "Strong",
                "reason": f"Same booking reference ({cand.tboh})",
            })
        elif cand.agency_id == ticket.agency_id and cand.intent == ticket.intent:
            agency_name = cand.agency.name if cand.agency else f"Agency #{cand.agency_id}"
            weak_matches.append({
                "ticket": cand,
                "type": "Weak",
                "reason": f"Same agency ({agency_name}) and same intent ({cand.intent})",
            })

    return {
        "strong": strong_matches,
        "weak": weak_matches,
    }
