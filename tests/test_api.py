"""Integration tests for the API endpoints, using an isolated in-memory
SQLite DB so tests never touch the real coffee_tracker.db file."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # keeps the same in-memory DB across connections
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_and_teardown():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200


def test_create_order_creates_new_customer():
    response = client.post(
        "/orders", json={"customer_name": "Layla", "drink": "Spanish Latte"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["customer_name"] == "Layla"
    assert data["drink"] == "Spanish Latte"


def test_create_order_reuses_existing_customer():
    client.post("/orders", json={"customer_name": "Omar", "drink": "Espresso"})
    response = client.post(
        "/orders", json={"customer_name": "Omar", "drink": "Mocha"}
    )
    assert response.status_code == 201

    list_response = client.get("/orders")
    omar_orders = [o for o in list_response.json() if o["customer_name"] == "Omar"]
    assert len(omar_orders) == 2


def test_streak_for_unknown_customer_returns_404():
    response = client.get("/customers/NobodyHome/streak")
    assert response.status_code == 404


def test_streak_for_existing_customer():
    client.post("/orders", json={"customer_name": "Sara", "drink": "Latte"})
    response = client.get("/customers/Sara/streak")
    assert response.status_code == 200
    data = response.json()
    assert data["current_streak"] == 1
    assert data["total_orders"] == 1


def test_popular_drinks_endpoint():
    client.post("/orders", json={"customer_name": "A", "drink": "Latte"})
    client.post("/orders", json={"customer_name": "B", "drink": "Latte"})
    client.post("/orders", json={"customer_name": "C", "drink": "Espresso"})

    response = client.get("/drinks/popular")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["drink"] == "Latte"
    assert data[0]["order_count"] == 2


def test_popular_drinks_empty():
    response = client.get("/drinks/popular")
    assert response.status_code == 200
    assert response.json() == []


def test_popular_drinks_rejects_invalid_top():
    response = client.get("/drinks/popular?top=0")
    assert response.status_code == 422
    assert "top" in response.json()["detail"]


def test_list_customers_returns_summaries():
    client.post("/orders", json={"customer_name": "Layla", "drink": "Latte"})
    client.post("/orders", json={"customer_name": "Omar", "drink": "Espresso"})

    response = client.get("/customers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    layla = next(customer for customer in data if customer["name"] == "Layla")
    assert layla["order_count"] == 1
    assert layla["current_streak"] == 1


def test_list_customers_empty():
    response = client.get("/customers")
    assert response.status_code == 200
    assert response.json() == []


def test_create_order_rejects_empty_fields():
    response = client.post(
        "/orders", json={"customer_name": "", "drink": "Latte"}
    )
    assert response.status_code == 422
    assert "customer_name" in response.json()["detail"]


def test_orders_support_pagination():
    for index in range(3):
        client.post(
            "/orders",
            json={"customer_name": f"Customer{index}", "drink": "Latte"},
        )

    response = client.get("/orders?limit=2&offset=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_streak_with_historical_dates():
    client.post(
        "/orders",
        json={
            "customer_name": "History",
            "drink": "Latte",
            "order_date": "2024-01-01",
        },
    )
    response = client.get("/customers/History/streak")
    assert response.status_code == 200
    data = response.json()
    assert data["current_streak"] == 0
    assert data["longest_streak"] == 1
