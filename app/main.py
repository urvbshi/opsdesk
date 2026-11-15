import os
from pathlib import Path
from datetime import date, datetime
from typing import Optional
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Agency, Ticket, ActivityLog, PRIORITIES, INTENTS, STATUSES
from app.schemas import TicketCreateSchema
from app.rules import detect_intent
from app.linking import find_related_tickets
from app.auth import (
    verify_password,
    sign_user_id,
    COOKIE_NAME,
    get_current_user_optional,
    get_current_user_required,
    enforce_agency_access,
)

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="OpsDesk MVP-1", description="B2B Travel Operations Ticketing Platform")

# Mount static files using absolute path
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Templates using absolute path
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Render friendly HTML error page for HTTPExceptions like 403 and 404."""
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    db = next(get_db())
    try:
        user = get_current_user_optional(request, db)
    finally:
        db.close()

    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "user": user,
            "status_code": exc.status_code,
            "detail": exc.detail,
        },
        status_code=exc.status_code,
    )


@app.get("/", response_class=HTMLResponse)
def index(request: Request, current_user: Optional[User] = Depends(get_current_user_optional)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/tickets", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, current_user: Optional[User] = Depends(get_current_user_optional)):
    if current_user:
        return RedirectResponse(url="/tickets", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"user": None},
    )


@app.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username.strip()).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "user": None,
                "error": "Invalid username or password. Check credentials or use demo quick-login.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    response = RedirectResponse(url="/tickets", status_code=status.HTTP_303_SEE_OTHER)
    signed_token = sign_user_id(user.id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=signed_token,
        httponly=True,
        samesite="lax",
    )
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(COOKIE_NAME)
    return response


class IntentSuggestRequest(BaseModel):
    text: str


@app.post("/api/suggest-intent")
def api_suggest_intent(payload: IntentSuggestRequest):
    """
    Auto-suggest endpoint that evaluates text against rules in app/rules.py
    and returns the detected intent along with the matched trigger words.
    """
    intent, matched = detect_intent(payload.text)
    return {
        "intent": intent,
        "matched_words": matched,
    }


@app.get("/tickets", response_class=HTMLResponse)
def list_tickets(
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """
    Shows ticket list scoped by role:
    - Requesters see ONLY tickets from their own travel agency.
    - Agents, Escalation Managers, and Leads see tickets from ALL agencies.
    """
    query = db.query(Ticket)
    if current_user.role == "Requester":
        query = query.filter(Ticket.agency_id == current_user.agency_id)

    tickets = query.order_by(Ticket.created_at.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="tickets_list.html",
        context={
            "user": current_user,
            "tickets": tickets,
        },
    )


@app.get("/tickets/new", response_class=HTMLResponse)
def create_ticket_page(
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    agencies = db.query(Agency).order_by(Agency.name).all()
    return templates.TemplateResponse(
        request=request,
        name="ticket_create.html",
        context={
            "user": current_user,
            "agencies": agencies,
            "form_data": None,
            "form_error": None,
        },
    )


@app.post("/tickets/new")
def create_ticket_submit(
    request: Request,
    title: str = Form(""),
    description: str = Form(""),
    agency_id: Optional[int] = Form(None),
    tboh: str = Form(""),
    priority: str = Form("Medium"),
    intent: str = Form("Other"),
    matched_keywords: Optional[str] = Form(None),
    check_in_date: Optional[str] = Form(None),
    lcd: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    # Enforce agency ownership: Requesters can only submit tickets for their own agency
    if current_user.role == "Requester":
        target_agency_id = current_user.agency_id
    else:
        target_agency_id = agency_id or 1

    # Date parsing helper
    parsed_check_in = None
    if check_in_date and check_in_date.strip():
        try:
            parsed_check_in = date.fromisoformat(check_in_date.strip())
        except ValueError:
            pass

    parsed_lcd = None
    if lcd and lcd.strip():
        try:
            parsed_lcd = date.fromisoformat(lcd.strip())
        except ValueError:
            pass

    raw_payload = {
        "title": title,
        "description": description,
        "agency_id": target_agency_id,
        "tboh": tboh,
        "priority": priority,
        "intent": intent,
        "matched_keywords": matched_keywords,
        "check_in_date": parsed_check_in,
        "lcd": parsed_lcd,
    }

    # Server-side validation via Pydantic
    try:
        validated_data = TicketCreateSchema(**raw_payload)
    except ValidationError as err:
        error_msg = "; ".join([f"{e['loc'][0]}: {e['msg']}" for e in err.errors()])
        agencies = db.query(Agency).order_by(Agency.name).all()
        return templates.TemplateResponse(
            request=request,
            name="ticket_create.html",
            context={
                "user": current_user,
                "agencies": agencies,
                "form_data": raw_payload,
                "form_error": error_msg,
            },
            status_code=422,
        )

    # Persist ticket in database
    new_ticket = Ticket(
        title=validated_data.title,
        description=validated_data.description,
        agency_id=validated_data.agency_id,
        tboh=validated_data.tboh,
        priority=validated_data.priority,
        intent=validated_data.intent,
        matched_keywords=validated_data.matched_keywords,
        check_in_date=validated_data.check_in_date,
        lcd=validated_data.lcd,
        status="New",
        created_by_user_id=current_user.id,
    )
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)

    # Log initial creation activity
    activity = ActivityLog(
        ticket_id=new_ticket.id,
        user_id=current_user.id,
        action_type="CREATED",
        details=f"Ticket #{new_ticket.id} created with priority '{new_ticket.priority}' and intent '{new_ticket.intent}'. Booking: {new_ticket.tboh}.",
    )
    db.add(activity)

    # Check for immediate context links and log them in timeline
    related = find_related_tickets(new_ticket, db, viewer=current_user)
    num_strong = len(related["strong"])
    num_weak = len(related["weak"])
    if num_strong > 0 or num_weak > 0:
        activity_links = ActivityLog(
            ticket_id=new_ticket.id,
            user_id=None,
            action_type="LINKS_DETECTED",
            details=f"Context engine discovered {num_strong} strong link(s) (same TBOH) and {num_weak} weak link(s) (same agency & intent).",
        )
        db.add(activity_links)

    db.commit()

    return RedirectResponse(
        url=f"/tickets/{new_ticket.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def get_ticket_detail(
    ticket_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket #{ticket_id} does not exist.",
        )

    # Cross-agency security check
    enforce_agency_access(current_user, ticket)

    # Context linking: find strong (same TBOH) & weak (same agency + intent) matches
    related_tickets = find_related_tickets(ticket, db, viewer=current_user)

    return templates.TemplateResponse(
        request=request,
        name="ticket_detail.html",
        context={
            "user": current_user,
            "ticket": ticket,
            "related_tickets": related_tickets,
        },
    )


@app.post("/tickets/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    new_status: str = Form(...),
    current_user: User = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket #{ticket_id} does not exist.",
        )

    enforce_agency_access(current_user, ticket)

    if new_status not in STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{new_status}'. Allowed: {', '.join(STATUSES)}",
        )

    old_status = ticket.status
    if old_status != new_status:
        ticket.status = new_status
        status_log = ActivityLog(
            ticket_id=ticket.id,
            user_id=current_user.id,
            action_type="STATUS_CHANGE",
            details=f"Status transitioned from '{old_status}' to '{new_status}'.",
        )
        db.add(status_log)
        db.commit()

    return RedirectResponse(
        url=f"/tickets/{ticket.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
