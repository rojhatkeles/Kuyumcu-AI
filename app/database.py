from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

# Geliştirme kolaylığı için SQLite kullanalım. 
# Eğer .env içinde başka bir URL tanımlıysa o kullanılır (Örn: PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

# SQLite için check_same_thread=False gereklidir
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()