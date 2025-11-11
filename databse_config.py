from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLAlchemy_local_DB_URL = 'postgresql://postgres:Password@localhost/ShopeeProject'
engine = create_engine(SQLAlchemy_local_DB_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()  
    try:
        yield db
    finally:
        db.close()
