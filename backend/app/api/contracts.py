"""合同 API"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_current_user
from app.models.contract import FuelContract, ContractStatus
from app.models.supplier import Supplier, SupplierStatus
from app.models.user import User
from app.schemas.contract import (
    ContractCreate, ContractUpdate, ContractApprove, ContractResponse,
)
from app.utils.helpers import api_response, paginate_response, generate_contract_no

router = APIRouter(prefix="/api/contracts", tags=["采购合同"])


@router.get("")
def list_contracts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[ContractStatus] = None,
    supplier_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(FuelContract).options(joinedload(FuelContract.supplier))
    if status:
        q = q.filter(FuelContract.status == status)
    if supplier_id:
        q = q.filter(FuelContract.supplier_id == supplier_id)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter((FuelContract.contract_no.like(like)) | (FuelContract.coal_type.like(like)))

    total = q.count()
    rows = (
        q.order_by(FuelContract.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for r in rows:
        item = ContractResponse.model_validate(r).model_dump()
        item["supplier_name"] = r.supplier.name if r.supplier else None
        items.append(item)
    return api_response(data=paginate_response(items, total, page, page_size))


@router.post("")
def create_contract(payload: ContractCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
    if not supplier:
        raise HTTPException(404, "供应商不存在")
    if supplier.status != SupplierStatus.ACTIVE:
        raise HTTPException(400, f"供应商当前状态 {supplier.status.value}，不可签订合同")

    next_seq = (db.query(func.count(FuelContract.id)).scalar() or 0) + 1
    total_amount = round(payload.contract_quantity * payload.unit_price / 10000, 2)

    contract = FuelContract(
        contract_no=generate_contract_no(next_seq),
        total_amount=total_amount,
        status=ContractStatus.DRAFT,
        **payload.model_dump(),
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    result = ContractResponse.model_validate(contract).model_dump()
    result["supplier_name"] = supplier.name
    return api_response(message="合同已创建", data=result)


@router.get("/{contract_id}")
def get_contract(contract_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    c = (
        db.query(FuelContract)
        .options(joinedload(FuelContract.supplier))
        .filter(FuelContract.id == contract_id)
        .first()
    )
    if not c:
        raise HTTPException(404, "合同不存在")
    result = ContractResponse.model_validate(c).model_dump()
    result["supplier_name"] = c.supplier.name if c.supplier else None
    return api_response(data=result)


@router.put("/{contract_id}")
def update_contract(
    contract_id: int, payload: ContractUpdate,
    db: Session = Depends(get_db), _: User = Depends(get_current_user),
):
    c = db.query(FuelContract).filter(FuelContract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "合同不存在")
    if c.status not in (ContractStatus.DRAFT, ContractStatus.PENDING_APPROVAL):
        raise HTTPException(400, "仅草稿/待审批合同可修改")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    if c.contract_quantity and c.unit_price:
        c.total_amount = round(c.contract_quantity * c.unit_price / 10000, 2)
    db.commit()
    db.refresh(c)
    return api_response(message="已更新", data=ContractResponse.model_validate(c).model_dump())


@router.post("/{contract_id}/submit")
def submit_contract(contract_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """提交审批"""
    c = db.query(FuelContract).filter(FuelContract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "合同不存在")
    if c.status != ContractStatus.DRAFT:
        raise HTTPException(400, "仅草稿可提交")
    c.status = ContractStatus.PENDING_APPROVAL
    db.commit()
    return api_response(message="已提交审批")


@router.post("/{contract_id}/approve")
def approve_contract(
    contract_id: int, payload: ContractApprove,
    db: Session = Depends(get_db), _: User = Depends(get_current_user),
):
    c = db.query(FuelContract).filter(FuelContract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "合同不存在")
    if c.status != ContractStatus.PENDING_APPROVAL:
        raise HTTPException(400, "仅待审批合同可审批")
    c.approved_by = payload.approver
    c.approved_at = datetime.utcnow()
    c.status = ContractStatus.ACTIVE if payload.approved else ContractStatus.DRAFT
    if payload.notes:
        c.notes = (c.notes or "") + f"\n[审批] {payload.notes}"
    db.commit()
    db.refresh(c)
    return api_response(
        message="审批通过，合同生效" if payload.approved else "审批未通过，已退回草稿",
        data=ContractResponse.model_validate(c).model_dump(),
    )


@router.post("/{contract_id}/terminate")
def terminate_contract(
    contract_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user),
):
    c = db.query(FuelContract).filter(FuelContract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "合同不存在")
    if c.status != ContractStatus.ACTIVE:
        raise HTTPException(400, "仅生效合同可解除")
    c.status = ContractStatus.TERMINATED
    db.commit()
    return api_response(message="合同已解除")
