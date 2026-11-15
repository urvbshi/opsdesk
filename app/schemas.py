from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.models import PRIORITIES, INTENTS, STATUSES


class TicketCreateSchema(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="Ticket title")
    description: str = Field(..., min_length=5, description="Detailed problem description")
    agency_id: int = Field(..., gt=0, description="Target travel agency ID")
    tboh: str = Field(..., min_length=3, max_length=50, description="Booking reference (TBOH)")
    priority: str = Field(default="Medium", description="Ticket priority")
    intent: str = Field(default="Other", description="Operational category")
    matched_keywords: Optional[str] = Field(default=None, description="Matched keyword tokens")
    check_in_date: Optional[date] = Field(default=None, description="Traveler check-in date")
    lcd: Optional[date] = Field(default=None, description="Last Cancellation Date")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 3:
            raise ValueError("Title must be at least 3 characters long.")
        return s

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        s = v.strip()
        if len(s) < 5:
            raise ValueError("Description must be at least 5 characters long.")
        return s

    @field_validator("tboh")
    @classmethod
    def validate_tboh(cls, v: str) -> str:
        s = v.strip().upper()
        if len(s) < 3:
            raise ValueError("Booking reference (TBOH) cannot be blank.")
        return s

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in PRIORITIES:
            raise ValueError(f"Priority must be one of: {', '.join(PRIORITIES)}")
        return v

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, v: str) -> str:
        if v not in INTENTS:
            raise ValueError(f"Intent must be one of: {', '.join(INTENTS)}")
        return v
