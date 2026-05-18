"""合同 schemas"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator

from app.models.contract import ContractType, PricingMode, ContractStatus


class ContractCreate(BaseModel):
    supplier_id: int
    contract_type: ContractType = ContractType.SPOT
    coal_type: str
    coal_origin: Optional[str] = None
    contract_quantity: float
    unit_price: float
    pricing_mode: PricingMode = PricingMode.DELIVERED
    spec_calorific_value: Optional[float] = None
    spec_ash_max: Optional[float] = None
    spec_sulfur_max: Optional[float] = None
    spec_moisture_max: Optional[float] = None
    effective_date: datetime
    expiry_date: datetime
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "ContractCreate":
        if self.expiry_date <= self.effective_date:
            raise ValueError("到期日期必须晚于生效日期")
        if self.contract_quantity <= 0:
            raise ValueError("合同总量必须大于 0")
        if self.unit_price <= 0:
            raise ValueError("合同单价必须大于 0")
        return self


class ContractUpdate(BaseModel):
    unit_price: Optional[float] = None
    contract_quantity: Optional[float] = None
    expiry_date: Optional[datetime] = None
    spec_calorific_value: Optional[float] = None
    spec_ash_max: Optional[float] = None
    spec_sulfur_max: Optional[float] = None
    spec_moisture_max: Optional[float] = None
    notes: Optional[str] = None


class ContractApprove(BaseModel):
    approver: str
    approved: bool
    notes: Optional[str] = None


class ContractResponse(BaseModel):
    id: int
    contract_no: str
    supplier_id: int
    supplier_name: Optional[str] = None
    contract_type: ContractType
    coal_type: str
    coal_origin: Optional[str]
    contract_quantity: float
    unit_price: float
    pricing_mode: PricingMode
    total_amount: float
    spec_calorific_value: Optional[float]
    spec_ash_max: Optional[float]
    spec_sulfur_max: Optional[float]
    spec_moisture_max: Optional[float]
    effective_date: datetime
    expiry_date: datetime
    delivered_quantity: float
    status: ContractStatus
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
