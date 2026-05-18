"""供应商 schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.supplier import SupplierStatus, SupplierTier


class SupplierCreate(BaseModel):
    name: str
    short_name: Optional[str] = None
    legal_representative: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    business_license: Optional[str] = None
    registered_capital: Optional[float] = None
    coal_types: Optional[str] = None
    coal_origin: Optional[str] = None
    annual_capacity: Optional[float] = None
    transport_modes: Optional[str] = None
    notes: Optional[str] = None


class SupplierUpdate(BaseModel):
    short_name: Optional[str] = None
    contact_person: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    coal_types: Optional[str] = None
    coal_origin: Optional[str] = None
    annual_capacity: Optional[float] = None
    transport_modes: Optional[str] = None
    tier: Optional[SupplierTier] = None
    notes: Optional[str] = None


class SupplierReview(BaseModel):
    """准入审核"""
    approved: bool
    review_notes: str
    tier: Optional[SupplierTier] = SupplierTier.PROBATION


class SupplierResponse(BaseModel):
    id: int
    code: str
    name: str
    short_name: Optional[str]
    legal_representative: Optional[str]
    contact_person: Optional[str]
    contact_phone: Optional[str]
    address: Optional[str]
    business_license: Optional[str]
    registered_capital: Optional[float]
    coal_types: Optional[str]
    coal_origin: Optional[str]
    annual_capacity: Optional[float]
    transport_modes: Optional[str]
    tier: SupplierTier
    credit_score: float
    status: SupplierStatus
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
