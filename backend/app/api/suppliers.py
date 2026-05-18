"""供应商 API"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.supplier import Supplier, SupplierStatus, SupplierTier
from app.models.user import User
from app.schemas.supplier import (
    SupplierCreate, SupplierUpdate, SupplierReview, SupplierResponse,
)
from app.utils.helpers import api_response, paginate_response, generate_supplier_code

router = APIRouter(prefix="/api/suppliers", tags=["供应商"])


@router.get("")
def list_suppliers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[SupplierStatus] = None,
    tier: Optional[SupplierTier] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Supplier)
    if status:
        q = q.filter(Supplier.status == status)
    if tier:
        q = q.filter(Supplier.tier == tier)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter((Supplier.name.like(like)) | (Supplier.short_name.like(like)) | (Supplier.code.like(like)))

    total = q.count()
    rows = (
        q.order_by(Supplier.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [SupplierResponse.model_validate(r).model_dump() for r in rows]
    return api_response(data=paginate_response(items, total, page, page_size))


@router.post("")
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    if db.query(Supplier).filter(Supplier.name == payload.name).first():
        raise HTTPException(400, "供应商名称已存在")

    next_seq = (db.query(func.count(Supplier.id)).scalar() or 0) + 1
    supplier = Supplier(
        code=generate_supplier_code(next_seq),
        status=SupplierStatus.PENDING_REVIEW,
        tier=SupplierTier.PROBATION,
        **payload.model_dump(),
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return api_response(message="供应商已登记，待审核", data=SupplierResponse.model_validate(supplier).model_dump())


@router.get("/{supplier_id}")
def get_supplier(supplier_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "供应商不存在")
    return api_response(data=SupplierResponse.model_validate(s).model_dump())


@router.put("/{supplier_id}")
def update_supplier(
    supplier_id: int, payload: SupplierUpdate,
    db: Session = Depends(get_db), _: User = Depends(get_current_user),
):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "供应商不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return api_response(message="已更新", data=SupplierResponse.model_validate(s).model_dump())


@router.post("/{supplier_id}/review")
def review_supplier(
    supplier_id: int, payload: SupplierReview,
    db: Session = Depends(get_db), current: User = Depends(get_current_user),
):
    """准入审核：通过→ACTIVE，未通过→ARCHIVED"""
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "供应商不存在")
    if s.status != SupplierStatus.PENDING_REVIEW:
        raise HTTPException(400, "仅待审核供应商可审核")
    s.status = SupplierStatus.ACTIVE if payload.approved else SupplierStatus.ARCHIVED
    s.tier = payload.tier or SupplierTier.PROBATION
    s.reviewed_by = current.username
    s.reviewed_at = datetime.utcnow()
    s.review_notes = payload.review_notes
    db.commit()
    db.refresh(s)
    return api_response(
        message="审核通过，已准入合作" if payload.approved else "审核未通过，已归档",
        data=SupplierResponse.model_validate(s).model_dump(),
    )


@router.post("/{supplier_id}/suspend")
def suspend_supplier(
    supplier_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user),
):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "供应商不存在")
    if s.status != SupplierStatus.ACTIVE:
        raise HTTPException(400, "仅活动供应商可暂停")
    s.status = SupplierStatus.SUSPENDED
    db.commit()
    return api_response(message="已暂停合作")


@router.post("/{supplier_id}/resume")
def resume_supplier(
    supplier_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user),
):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "供应商不存在")
    if s.status != SupplierStatus.SUSPENDED:
        raise HTTPException(400, "仅暂停供应商可恢复")
    s.status = SupplierStatus.ACTIVE
    db.commit()
    return api_response(message="已恢复合作")
