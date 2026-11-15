import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Vercel serverless environment only permits writing to /tmp
if os.getenv("VERCEL"):
    DATABASE_URL = "sqlite:////tmp/opsdesk.db"
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./opsdesk.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# expire_on_commit=False prevents attributes from detaching unnecessarily after transactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
