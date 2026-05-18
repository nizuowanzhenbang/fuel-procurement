"""订单 schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.order import OrderStatus


class OrderCreate(BaseModel):
    contract_id: int
    planned_quantity: float
    unit_price: Optional[float] = None  # 不传则使用合同单价
    planned_delivery_date: datetime
    transport_mode: Optional[str] = None
    departure_port: Optional[str] = None
    arrival_plant: Optional[str] = None
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    planned_quantity: Optional[float] = None
    planned_delivery_date: Optional[datetime] = None
    transport_mode: Optional[str] = None
    notes: Optional[str] = None


class OrderReceive(BaseModel):
    """到货登记"""
    delivered_quantity: float
    actual_delivery_date: Optional[datetime] = None
    notes: Optional[str] = None


class OrderSettle(BaseModel):
    """结算"""
    settled_by: str
    delivered_amount: Optional[float] = None  # 不传则用已收量×单价
    notes: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    order_no: str
    contract_id: int
    contract_no: Optional[str] = None
    supplier_name: Optional[str] = None
    coal_type: Optional[str] = None
    planned_quantity: float
    unit_price: float
    planned_amount: float
    delivered_quantity: float
    delivered_amount: float
    planned_delivery_date: datetime
    actual_delivery_date: Optional[datetime]
    transport_mode: Optional[str]
    departure_port: Optional[str]
    arrival_plant: Optional[str]
    status: OrderStatus
    settled_by: Optional[str]
    settled_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
