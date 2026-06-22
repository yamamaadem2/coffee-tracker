"""Pydantic schemas for request/response validation."""
from datetime import date
from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, examples=["Layla"])
    drink: str = Field(..., min_length=1, examples=["Spanish Latte"])
    order_date: date | None = None  # defaults to today if not provided


class OrderOut(BaseModel):
    id: int
    customer_name: str
    drink: str
    order_date: date

    class Config:
        from_attributes = True


class StreakOut(BaseModel):
    customer_name: str
    current_streak: int
    longest_streak: int
    total_orders: int


class CustomerSummaryOut(BaseModel):
    name: str
    order_count: int
    current_streak: int
    longest_streak: int


class PopularDrinkOut(BaseModel):
    drink: str
    order_count: int
