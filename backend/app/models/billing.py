"""Pydantic-схемы для /api/billing/* и вспомогательных ручек."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PlanOut(BaseModel):
    plan_key: str
    name: str
    tier: str
    duration_days: int | None = None
    price_stars: int = 0
    price_usd_cents: int | None = None
    limits: dict[str, Any] = Field(default_factory=dict)
    features: list[str] = Field(default_factory=list)


class UsageItem(BaseModel):
    key: str
    limit: int
    period: str           # d | m | static
    used: int
    allowed: bool
    reset_at: datetime | None = None


class MeOut(BaseModel):
    tier: str
    plan_key: str
    plan_name: str
    status: str
    source: str | None = None
    end_at: datetime | None = None
    features: list[str] = Field(default_factory=list)
    usage: list[UsageItem] = Field(default_factory=list)
    auto_renew: bool = False


class InvoiceCreate(BaseModel):
    plan_key: str


class InvoiceOut(BaseModel):
    plan_key: str
    plan_name: str
    stars_amount: int
    invoice_url: str
    invoice_payload: str
    bot_username: str | None = None


class PaymentOut(BaseModel):
    id: int
    plan_key: str
    stars_amount: int
    status: str
    created_at: datetime
    paid_at: datetime | None = None
    refunded_at: datetime | None = None


class HistoryOut(BaseModel):
    payments: list[PaymentOut] = Field(default_factory=list)
