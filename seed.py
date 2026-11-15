import os
from datetime import date, datetime, timedelta, timezone
import bcrypt
from sqlalchemy.orm import Session

from app.database import Base, engine, SessionLocal
from app.models import Agency, User, Ticket, ActivityLog


def hash_pw(password: str) -> str:
    """Hashes a password with bcrypt salt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed_database():
    """
    Idempotent database seeder.
    Drops and recreates tables so running multiple times produces a clean, consistent state.
    """
    print("[1/5] Re-initializing database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        print("[2/5] Seeding 3 agencies...")
        agencies = [
            Agency(id=1, name="Skyline Travels"),
            Agency(id=2, name="Global Gateways"),
            Agency(id=3, name="Wanderlust Co."),
        ]
        db.add_all(agencies)
        db.commit()

        print("[3/5] Seeding demo users with hashed passwords...")
        default_pw = hash_pw("password123")
        users = [
            User(id=1, username="requester_skyline", hashed_password=default_pw, role="Requester", agency_id=1),
            User(id=2, username="requester_global", hashed_password=default_pw, role="Requester", agency_id=2),
            User(id=3, username="requester_wander", hashed_password=default_pw, role="Requester", agency_id=3),
            User(id=4, username="agent_alice", hashed_password=default_pw, role="Agent", agency_id=None),
            User(id=5, username="manager_bob", hashed_password=default_pw, role="Escalation Manager", agency_id=None),
            User(id=6, username="lead_charlie", hashed_password=default_pw, role="Lead", agency_id=None),
        ]
        db.add_all(users)
        db.commit()

        print("[4/5] Seeding ~20 tickets with strong & weak link relationships...")
        today = date.today()
        now = datetime.now(timezone.utc)

        tickets_data = [
            # --- TBOH-7701-DXB: 3 Refund tickets sharing one TBOH (Strong Link) ---
            {
                "title": "Refund requested for Emirates flight DXB-LHR",
                "description": "Passenger unable to travel due to medical emergency. Requesting full refund on unused ticket.",
                "agency_id": 1,
                "tboh": "TBOH-7701-DXB",
                "priority": "High",
                "intent": "Refund",
                "matched_keywords": "refund, ticket",
                "check_in_date": today + timedelta(days=10),
                "lcd": today + timedelta(days=3),
                "status": "Open",
                "created_by_user_id": 1,
            },
            {
                "title": "Duplicate charge refund request",
                "description": "Client card was billed twice for booking TBOH-7701-DXB during checkout. Please process refund for duplicate transaction.",
                "agency_id": 1,
                "tboh": "TBOH-7701-DXB",
                "priority": "Urgent",
                "intent": "Refund",
                "matched_keywords": "refund, transaction",
                "check_in_date": today + timedelta(days=10),
                "lcd": today + timedelta(days=3),
                "status": "Escalated",
                "created_by_user_id": 1,
            },
            {
                "title": "Tax and baggage fee refund follow-up",
                "description": "Customer was charged ancillary fees that should have been refunded per airline waiver policy.",
                "agency_id": 1,
                "tboh": "TBOH-7701-DXB",
                "priority": "Medium",
                "intent": "Refund",
                "matched_keywords": "refund, fee",
                "check_in_date": today + timedelta(days=10),
                "lcd": today + timedelta(days=3),
                "status": "New",
                "created_by_user_id": 1,
            },

            # --- Skyline Travels: Same agency + Same intent (Refund), different TBOH (Weak Link) ---
            {
                "title": "Hotel cancellation refund for missed connection",
                "description": "Guest arrived late and property charged full stay. Need refund for unused nights.",
                "agency_id": 1,
                "tboh": "TBOH-8802-HTL",
                "priority": "Medium",
                "intent": "Refund",
                "matched_keywords": "refund, cancellation",
                "check_in_date": today + timedelta(days=5),
                "lcd": today - timedelta(days=1),
                "status": "Pending",
                "created_by_user_id": 1,
            },
            {
                "title": "Date Change: Postpone departure by 3 days",
                "description": "Client requested change from 18th to 21st. Availability checked with carrier.",
                "agency_id": 1,
                "tboh": "TBOH-5511-SIN",
                "priority": "Medium",
                "intent": "Date Change",
                "matched_keywords": "date change, departure",
                "check_in_date": today + timedelta(days=7),
                "lcd": today + timedelta(days=2),
                "status": "Open",
                "created_by_user_id": 1,
            },
            {
                "title": "Date Change: Urgent flight reschedule",
                "description": "Corporate client meeting moved. Needs immediate date change for return leg.",
                "agency_id": 1,
                "tboh": "TBOH-5522-SIN",
                "priority": "Urgent",
                "intent": "Date Change",
                "matched_keywords": "date change, reschedule",
                "check_in_date": today + timedelta(days=4),
                "lcd": today + timedelta(days=1),
                "status": "Escalated",
                "created_by_user_id": 1,
            },
            {
                "title": "Cancellation: Entire itinerary cancel request",
                "description": "Traveler contracted influenza. Cancellation required before midnight LCD.",
                "agency_id": 1,
                "tboh": "TBOH-3310-AMS",
                "priority": "High",
                "intent": "Cancellation",
                "matched_keywords": "cancel, cancellation",
                "check_in_date": today + timedelta(days=2),
                "lcd": today + timedelta(days=1),
                "status": "New",
                "created_by_user_id": 1,
            },
            {
                "title": "Visa/Documents: Correct passport number mismatch",
                "description": "Typo in passport number on GDS PNR. Need supplier assistance to update passenger details.",
                "agency_id": 1,
                "tboh": "TBOH-4401-JFK",
                "priority": "Medium",
                "intent": "Visa/Documents",
                "matched_keywords": "passport, visa",
                "check_in_date": today + timedelta(days=14),
                "lcd": today + timedelta(days=7),
                "status": "Resolved",
                "created_by_user_id": 1,
            },

            # --- Global Gateways (Agency 2): Diverse tickets ---
            {
                "title": "Payment Issue: 3D Secure verification failed",
                "description": "Booking stuck in payment pending status due to OTP gateway timeout.",
                "agency_id": 2,
                "tboh": "TBOH-6601-PAR",
                "priority": "High",
                "intent": "Payment Issue",
                "matched_keywords": "payment, gateway",
                "check_in_date": today + timedelta(days=8),
                "lcd": today + timedelta(days=4),
                "status": "Open",
                "created_by_user_id": 2,
            },
            {
                "title": "Payment Issue: Credit line deduction discrepancy",
                "description": "B2B wallet balance deducted but voucher not generated.",
                "agency_id": 2,
                "tboh": "TBOH-6602-PAR",
                "priority": "Urgent",
                "intent": "Payment Issue",
                "matched_keywords": "payment, balance",
                "check_in_date": today + timedelta(days=6),
                "lcd": today + timedelta(days=3),
                "status": "Escalated",
                "created_by_user_id": 2,
            },
            {
                "title": "Supplier Issue: Hotel refuses to honor room booking",
                "description": "Guest arrived at hotel reception and property claims no booking found under voucher.",
                "agency_id": 2,
                "tboh": "TBOH-9901-BKK",
                "priority": "Urgent",
                "intent": "Supplier Issue",
                "matched_keywords": "supplier, hotel",
                "check_in_date": today,
                "lcd": today - timedelta(days=2),
                "status": "Open",
                "created_by_user_id": 2,
            },
            {
                "title": "Supplier Issue: Bed type not guaranteed",
                "description": "Family booked Twin Deluxe but supplier confirmed Single King bed.",
                "agency_id": 2,
                "tboh": "TBOH-9902-BKK",
                "priority": "Low",
                "intent": "Supplier Issue",
                "matched_keywords": "supplier, booking",
                "check_in_date": today + timedelta(days=20),
                "lcd": today + timedelta(days=15),
                "status": "New",
                "created_by_user_id": 2,
            },
            {
                "title": "Cancellation: Group trip cancel request",
                "description": "Corporate retreat cancelled. Requesting waiver of cancellation penalties.",
                "agency_id": 2,
                "tboh": "TBOH-2201-LON",
                "priority": "High",
                "intent": "Cancellation",
                "matched_keywords": "cancel, cancellation",
                "check_in_date": today + timedelta(days=12),
                "lcd": today + timedelta(days=5),
                "status": "Pending",
                "created_by_user_id": 2,
            },
            {
                "title": "Refund: Train ticket cancellation refund",
                "description": "Eurostar connection cancelled due to strike. Seeking standard refund.",
                "agency_id": 2,
                "tboh": "TBOH-2202-LON",
                "priority": "Low",
                "intent": "Refund",
                "matched_keywords": "refund, ticket",
                "check_in_date": today + timedelta(days=18),
                "lcd": today + timedelta(days=10),
                "status": "Closed",
                "created_by_user_id": 2,
            },

            # --- Wanderlust Co. (Agency 3): Diverse tickets ---
            {
                "title": "Visa/Documents: Urgent transit visa inquiry",
                "description": "Client transiting Doha needs transit visa confirmation for 14-hour layover.",
                "agency_id": 3,
                "tboh": "TBOH-1101-DOH",
                "priority": "High",
                "intent": "Visa/Documents",
                "matched_keywords": "transit visa, document",
                "check_in_date": today + timedelta(days=3),
                "lcd": today + timedelta(days=1),
                "status": "Open",
                "created_by_user_id": 3,
            },
            {
                "title": "Date Change: Extend stay by 2 nights in Tokyo",
                "description": "Guest wants to modify checkout date from Nov 24 to Nov 26.",
                "agency_id": 3,
                "tboh": "TBOH-1102-TYO",
                "priority": "Medium",
                "intent": "Date Change",
                "matched_keywords": "date change, checkout",
                "check_in_date": today + timedelta(days=9),
                "lcd": today + timedelta(days=5),
                "status": "New",
                "created_by_user_id": 3,
            },
            {
                "title": "Supplier Issue: Transfer pickup driver not found",
                "description": "Traveler waiting at arrivals hall; private transfer driver has not arrived.",
                "agency_id": 3,
                "tboh": "TBOH-1103-TYO",
                "priority": "Urgent",
                "intent": "Supplier Issue",
                "matched_keywords": "driver, transfer, supplier",
                "check_in_date": today,
                "lcd": today - timedelta(days=1),
                "status": "Escalated",
                "created_by_user_id": 3,
            },
            {
                "title": "Other: GST Invoice request with company VAT",
                "description": "Accounts department requires updated tax invoice with specific legal entity name.",
                "agency_id": 3,
                "tboh": "TBOH-1104-DEL",
                "priority": "Low",
                "intent": "Other",
                "matched_keywords": "invoice, vat",
                "check_in_date": today - timedelta(days=5),
                "lcd": today - timedelta(days=10),
                "status": "Resolved",
                "created_by_user_id": 3,
            },
            {
                "title": "Payment Issue: Overcharge on resort fee",
                "description": "Guest was billed mandatory resort fee locally despite voucher including all taxes.",
                "agency_id": 3,
                "tboh": "TBOH-1105-MIA",
                "priority": "Medium",
                "intent": "Payment Issue",
                "matched_keywords": "overcharge, payment",
                "check_in_date": today - timedelta(days=2),
                "lcd": today - timedelta(days=7),
                "status": "Closed",
                "created_by_user_id": 3,
            },
            {
                "title": "Refund: Cancelled safari excursion fee",
                "description": "National park closed due to severe weather. Tour operator acknowledged cancellation.",
                "agency_id": 3,
                "tboh": "TBOH-1106-NBO",
                "priority": "Medium",
                "intent": "Refund",
                "matched_keywords": "refund, tour",
                "check_in_date": today + timedelta(days=15),
                "lcd": today + timedelta(days=7),
                "status": "Open",
                "created_by_user_id": 3,
            },
        ]

        ticket_objects = []
        for t in tickets_data:
            obj = Ticket(**t)
            ticket_objects.append(obj)
        db.add_all(ticket_objects)
        db.commit()

        print("[5/5] Adding initial activity logs for tickets...")
        activities = []
        for ticket in ticket_objects:
            activities.append(
                ActivityLog(
                    ticket_id=ticket.id,
                    user_id=ticket.created_by_user_id,
                    action_type="CREATED",
                    details=f"Ticket #{ticket.id} created with priority '{ticket.priority}' and intent '{ticket.intent}'.",
                    created_at=now - timedelta(hours=2),
                )
            )
            if ticket.status != "New":
                activities.append(
                    ActivityLog(
                        ticket_id=ticket.id,
                        user_id=4,  # agent_alice
                        action_type="STATUS_CHANGE",
                        details=f"Status transitioned from 'New' to '{ticket.status}'.",
                        created_at=now - timedelta(minutes=45),
                    )
                )

        # Add LINKS_DETECTED activity log for tickets sharing TBOH-7701-DXB
        activities.append(
            ActivityLog(
                ticket_id=ticket_objects[1].id, # Ticket 2
                user_id=None,
                action_type="LINKS_DETECTED",
                details="Context engine detected Strong Link to Ticket #1 (same booking reference TBOH-7701-DXB).",
                created_at=now - timedelta(minutes=30),
            )
        )
        activities.append(
            ActivityLog(
                ticket_id=ticket_objects[2].id, # Ticket 3
                user_id=None,
                action_type="LINKS_DETECTED",
                details="Context engine detected Strong Links to Ticket #1 and Ticket #2 (same booking reference TBOH-7701-DXB).",
                created_at=now - timedelta(minutes=15),
            )
        )

        db.add_all(activities)
        db.commit()

        print(f"\n[OK] Database seeded successfully!")
        print(f"     - Agencies : {len(agencies)}")
        print(f"     - Users    : {len(users)} (Default password for all: 'password123')")
        print(f"     - Tickets  : {len(ticket_objects)}")
        print(f"     - Activities: {len(activities)}")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
