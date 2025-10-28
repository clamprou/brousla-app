import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import Base, get_db
from app.models import Plan

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Seed plans
    plans = [
        Plan(
            name="FREE",
            stripe_price_id=None,
            limits_json={"max_renders_per_day": 10, "max_seats": 1}
        ),
        Plan(
            name="PRO",
            stripe_price_id="price_pro",
            limits_json={"max_renders_per_day": 100, "max_seats": 1}
        ),
        Plan(
            name="TEAM",
            stripe_price_id="price_team",
            limits_json={"max_renders_per_day": 500, "max_seats": 5}
        )
    ]
    db.add_all(plans)
    db.commit()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
