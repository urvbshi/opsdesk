from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from app.database import Base

ROLES = ("Requester", "Agent", "Escalation Manager", "Lead")
PRIORITIES = ("Low", "Medium", "High", "Urgent")
INTENTS = (
    "Refund",
    "Date Change",
    "Cancellation",
    "Visa/Documents",
    "Payment Issue",
    "Supplier Issue",
    "Other",
)
STATUSES = ("New", "Open", "Pending", "Escalated", "Resolved", "Closed")


class Agency(Base):
    __tablename__ = "agencies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="agency")
    tickets = relationship("Ticket", back_populates="agency")

    def __repr__(self):
        return f"<Agency(id={self.id}, name='{self.name}')>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Eagerly join agency so it is always accessible in templates without DetachedInstanceError
    agency = relationship("Agency", back_populates="users", lazy="joined")
    tickets_created = relationship("Ticket", back_populates="creator")
    activity_logs = relationship("ActivityLog", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False, index=True)
    tboh = Column(String(50), nullable=False, index=True)
    priority = Column(String(20), nullable=False, default="Medium")
    intent = Column(String(50), nullable=False, default="Other")
    matched_keywords = Column(String(255), nullable=True)
    check_in_date = Column(Date, nullable=True)
    lcd = Column(Date, nullable=True)
    status = Column(String(30), nullable=False, default="New")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Eagerly join agency and creator
    agency = relationship("Agency", back_populates="tickets", lazy="joined")
    creator = relationship("User", back_populates="tickets_created", lazy="joined")
    activity_logs = relationship(
        "ActivityLog",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="ActivityLog.created_at.desc()",
        lazy="joined",
    )

    def __repr__(self):
        return f"<Ticket(id={self.id}, tboh='{self.tboh}', intent='{self.intent}', status='{self.status}')>"


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_type = Column(String(50), nullable=False)
    details = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    ticket = relationship("Ticket", back_populates="activity_logs")
    user = relationship("User", back_populates="activity_logs", lazy="joined")

    def __repr__(self):
        return f"<ActivityLog(id={self.id}, action='{self.action_type}')>"
