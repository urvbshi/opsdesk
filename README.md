# OpsDesk - B2B Travel Operations Ticketing Platform (MVP-1)

OpsDesk is a context-rich ticketing MVP built for B2B travel operations. It streamlines communication between partner travel agencies and internal support teams (Agents, Escalation Managers, Leads) by surfacing context, auto-classifying issue intents with explainable rules, linking related historical bookings, and recording a full activity timeline.

---

## 🛠 Tech Stack

- **Backend:** Python 3.11+, FastAPI (REST endpoints, HTML routes, dependency injection)
- **Database:** SQLite with SQLAlchemy 2.0 ORM (persisted to `opsdesk.db`)
- **Frontend / Templating:** Jinja2 server-rendered templates, minimal Vanilla JS (debounced auto-suggest)
- **Authentication & Security:** Cookie-based sessions with HMAC-SHA256 tamper-proof signing, bcrypt password hashing
- **Validation:** Pydantic 2.x schemas for server-side form validation
- **Testing:** pytest with FastAPI TestClient

---

## 🚀 Quick Setup & Run Guide

### 1. Prerequisites
Ensure Python 3.11+ is installed.

### 2. Setup Virtual Environment
```powershell
cd C:\Users\URVASHI\.gemini\antigravity\scratch\opsdesk
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Seed the Database
Populates 3 travel agencies, 6 demo accounts, and 20 realistic tickets (safe to re-run anytime):
```powershell
python seed.py
```

### 5. Launch the Server
```powershell
uvicorn app.main:app --reload --port 8000
```
Open your browser and navigate to: **`http://localhost:8000`**

### 6. Run the Test Suite
```powershell
pytest -v
```

---

## 👥 Demo User Accounts

All demo accounts share the default password: **`password123`**.  
The `/login` screen includes a **1-Click Quick Login** switcher for instant testing.

| Username | Role | Agency Scope | Permissions |
| :--- | :--- | :--- | :--- |
| `requester_skyline` | **Requester** | Skyline Travels | Sees **only** Skyline Travels tickets. Blocked (403) from other agencies. |
| `requester_global` | **Requester** | Global Gateways | Sees **only** Global Gateways tickets. |
| `requester_wander` | **Requester** | Wanderlust Co. | Sees **only** Wanderlust Co. tickets. |
| `agent_alice` | **Agent** | *Global (Internal)* | Sees and manages tickets across all partner agencies. |
| `manager_bob` | **Escalation Manager** | *Global (Internal)* | Full visibility, handles escalations. |
| `lead_charlie` | **Lead** | *Global (Internal)* | Full administrative visibility across operations. |

---

## 📌 Core Domain Assumptions

1. **Demo Login / Authentication:**  
   Uses standard HTTP-only session cookies signed with HMAC-SHA256 (`SECRET_KEY`). This avoids OAuth/JWT configuration overhead for hackathon judging while guaranteeing production-grade tamper protection and password hashing with `bcrypt`.
2. **TBOH = Booking Reference:**  
   TBOH is the travel company's primary booking reference code (e.g. `TBOH-7701-DXB`). Tickets with identical TBOH refer to the same flight, hotel, or itinerary.
3. **LCD = Last Cancellation Date:**  
   The critical cutoff date and time after which airline/hotel cancellation penalties or non-refundable policies kick in.
4. **Rule-Based Engine (Rules, Not ML):**  
   All intent classification rules are kept in a single file ([app/rules.py](file:///C:/Users/URVASHI/.gemini/antigravity/scratch/opsdesk/app/rules.py)). Rather than an unexplainable, slow machine learning black box, rule-based matching is instantaneous, deterministic, and 100% explainable by highlighting the exact matched trigger words. The user always maintains manual override authority via the dropdown.

---

## 💡 MVP-1 Features Implemented

### 1. Context-Rich Tickets
- Fields: Title, Description, Agency, TBOH (Booking Ref), Priority (Low, Medium, High, Urgent), Intent, Check-in Date, LCD (Last Cancellation Date), Status (New, Open, Pending, Escalated, Resolved, Closed).
- Pre-loaded with ~20 tickets across 3 agencies.

### 2. Explainable Intent Auto-Suggest & User Override
- Fixed Categories: `Refund`, `Date Change`, `Cancellation`, `Visa/Documents`, `Payment Issue`, `Supplier Issue`, `Other`.
- As the user types the title and description, the frontend queries `/api/suggest-intent` with debouncing.
- Displays the matched words badge: `💡 Suggested Intent: Refund (Matched: refund, duplicate charge)`.
- User can accept the suggestion or manually pick any category from the dropdown.

### 3. Context Linking (Related Older Tickets)
- **Strong Link:** Tickets sharing the same TBOH (e.g., 3 refund tickets for `TBOH-7701-DXB`). Reason shown: `Same booking reference ({tboh})`.
- **Weak Link:** Tickets with the same agency and same intent category (with different TBOH). Reason shown: `Same agency ({agency}) and same intent ({intent})`.
- Strong matches take precedence and are never duplicated as weak matches.
- Requesters can only see linked tickets within their own agency.

### 4. Activity Audit Timeline
- Every ticket tracks lifecycle events in an append-only `activity_logs` table:
  - `🆕 Ticket Created` (with priority and intent details)
  - `🔄 Status Changed` (tracks who changed it and the transition, e.g. `Open` &rarr; `Resolved`)
  - `🔗 Related Tickets Linked` (tracks when strong/weak matches are detected by the context engine)

### 5. Backend Role Enforcement & Security
- Strict URL tampering prevention: if `requester_skyline` tries to access `http://localhost:8000/tickets/9` (belonging to Global Gateways), the backend returns **HTTP 403 Forbidden** with an informative error screen.

### 6. Robust States & Data Persistence
- **Server-Side Validation:** Powered by Pydantic; rejects invalid lengths or illegal enum values with descriptive alerts while preserving form input.
- **Empty States:** Friendly empty states for ticket lists and related ticket cards.
- **Loading States:** Form submission button transitions to `⏳ Creating...` and disables to prevent duplicate submissions.
- **Persistence:** All data is persisted to SQLite on disk and survives server restarts.

---

## 🧪 Automated Test Suite

Run all tests via pytest:
```powershell
.\.venv\Scripts\pytest.exe -v
```

Tests include:
- `test_intent.py`: 7 tests verifying keyword matching across all categories and fallback behavior.
- `test_linking.py`: 4 tests validating Strong TBOH matching, Weak agency+intent matching, exclusivity, and requester isolation.
- `test_security.py`: 2 tests verifying cross-agency URL tampering is blocked (403) and agent access is permitted.
