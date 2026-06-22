"""Coffee Order Tracker API.

Tracks customer coffee orders, computes order streaks per customer,
and reports the most popular drinks.
"""
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import models, schemas
from .database import engine, get_db
from .logic import calculate_streaks, most_popular_drinks

models.Base.metadata.create_all(bind=engine)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="Coffee Order Tracker",
    description="Track coffee orders, customer streaks, and popular drinks.",
    version="1.1.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request, exc: RequestValidationError):
    """Return readable validation errors instead of raw Pydantic output."""
    messages = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"] if part != "body")
        messages.append(f"{field}: {error['msg']}" if field else error["msg"])
    return JSONResponse(status_code=422, content={"detail": "; ".join(messages)})


def get_customer_or_404(db: Session, customer_name: str) -> models.Customer:
    customer = (
        db.query(models.Customer)
        .filter(models.Customer.name == customer_name)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


def customer_summary(customer: models.Customer) -> schemas.CustomerSummaryOut:
    order_dates = [order.order_date for order in customer.orders]
    current, longest = calculate_streaks(order_dates)
    return schemas.CustomerSummaryOut(
        name=customer.name,
        order_count=len(order_dates),
        current_streak=current,
        longest_streak=longest,
    )


@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")


@app.post("/orders", response_model=schemas.OrderOut, status_code=201)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    """Log a new order. Creates the customer if they don't exist yet."""
    customer = (
        db.query(models.Customer)
        .filter(models.Customer.name == order.customer_name)
        .first()
    )
    if not customer:
        customer = models.Customer(name=order.customer_name)
        db.add(customer)
        db.commit()
        db.refresh(customer)

    new_order = models.Order(
        customer_id=customer.id,
        drink=order.drink,
        order_date=order.order_date or date.today(),
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    return schemas.OrderOut(
        id=new_order.id,
        customer_name=customer.name,
        drink=new_order.drink,
        order_date=new_order.order_date,
    )


@app.get("/orders", response_model=list[schemas.OrderOut])
def list_orders(
    limit: int = Query(50, ge=1, le=100, description="Max orders to return"),
    offset: int = Query(0, ge=0, description="Number of orders to skip"),
    db: Session = Depends(get_db),
):
    """List logged orders, most recent first."""
    orders = (
        db.query(models.Order, models.Customer.name)
        .join(models.Customer)
        .order_by(models.Order.order_date.desc(), models.Order.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        schemas.OrderOut(
            id=o.Order.id,
            customer_name=o.name,
            drink=o.Order.drink,
            order_date=o.Order.order_date,
        )
        for o in orders
    ]


@app.get("/customers", response_model=list[schemas.CustomerSummaryOut])
def list_customers(db: Session = Depends(get_db)):
    """List all customers with order counts and streak stats."""
    customers = db.query(models.Customer).order_by(models.Customer.name).all()
    return [customer_summary(customer) for customer in customers]


@app.get("/customers/{customer_name}/streak", response_model=schemas.StreakOut)
def get_customer_streak(customer_name: str, db: Session = Depends(get_db)):
    """Get a customer's current and longest order streak."""
    customer = get_customer_or_404(db, customer_name)
    order_dates = [o.order_date for o in customer.orders]
    current, longest = calculate_streaks(order_dates)

    return schemas.StreakOut(
        customer_name=customer.name,
        current_streak=current,
        longest_streak=longest,
        total_orders=len(order_dates),
    )


@app.get("/drinks/popular", response_model=list[schemas.PopularDrinkOut])
def get_popular_drinks(
    top: int = Query(5, ge=1, le=20, description="Number of drinks to return"),
    db: Session = Depends(get_db),
):
    """Get the most popular drinks across all customers."""
    drinks = [o.drink for o in db.query(models.Order).all()]
    top_drinks = most_popular_drinks(drinks, top_n=top)

    return [
        schemas.PopularDrinkOut(drink=drink, order_count=count)
        for drink, count in top_drinks
    ]
