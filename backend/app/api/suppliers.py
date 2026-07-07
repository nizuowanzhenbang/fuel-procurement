"""供应商 API"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_write, require_approver
from app.models.supplier import Supplier, SupplierStatus, SupplierTier
from app.models.supplier_quality_score import SupplierQualityScore
from app.models.user import User
from app.schemas.supplier import (
    SupplierCreate, SupplierUpdate, SupplierReview, SupplierResponse,
)
from app.utils.helpers import api_response, paginate_response, generate_supplier_code
from app.utils.csv_export import stream_csv, fmt_dt
from app.utils.quality_client import fetch_supplier_credit

router = APIRouter(prefix="/api/suppliers", tags=["供应商"])


def _latest_quality_score(db: Session, supplier_name: str) -> Optional[SupplierQualityScore]:
    return (
        db.query(SupplierQualityScore)
        .filter(SupplierQualityScore.supplier_name == supplier_name)
        .order_by(SupplierQualityScore.evaluated_at.desc())
        .first()
    )


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


@router.get("/export")
def export_suppliers(
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
    rows = q.order_by(Supplier.created_at.desc()).all()

    headers = [
        "编码", "名称", "等级", "状态", "信用分", "联系人", "电话",
        "可供煤种", "产地", "年供应能力(吨)", "审核人", "审核时间",
    ]
    data = [
        [
            r.code, r.name, r.tier.value if r.tier else "",
            r.status.value if r.status else "", r.credit_score,
            r.contact_person or "", r.contact_phone or "",
            r.coal_types or "", r.coal_origin or "", r.annual_capacity or 0,
            r.reviewed_by or "", fmt_dt(r.reviewed_at),
        ]
        for r in rows
    ]
    return stream_csv("供应商列表", headers, data)


@router.post("")
def create_supplier(
    payload: SupplierCreate, db: Session = Depends(get_db),
    _: User = Depends(require_write),
):
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

    result = SupplierResponse.model_validate(s).model_dump()

    # 本地最新质量评分（webhook 同步）
    local_score = _latest_quality_score(db, s.name)
    if local_score:
        result["quality_score"] = {
            "score": local_score.score,
            "sample_count": local_score.sample_count,
            "pass_rate": local_score.pass_rate,
            "evaluated_at": local_score.evaluated_at.isoformat(),
            "source": "synced",
        }
    else:
        # 尝试实时拉取煤质系统（失败降级为 None）
        remote = fetch_supplier_credit(s.name)
        if remote:
            result["quality_score"] = {**remote, "source": "live"}
        else:
            result["quality_score"] = None

    return api_response(data=result)


@router.put("/{supplier_id}")
def update_supplier(
    supplier_id: int, payload: SupplierUpdate,
    db: Session = Depends(get_db), _: User = Depends(require_write),
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
    db: Session = Depends(get_db), current: User = Depends(require_approver),
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
    supplier_id: int, db: Session = Depends(get_db),
    _: User = Depends(require_approver),
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
    supplier_id: int, db: Session = Depends(get_db),
    _: User = Depends(require_approver),
):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(404, "供应商不存在")
    if s.status != SupplierStatus.SUSPENDED:
        raise HTTPException(400, "仅暂停供应商可恢复")
    s.status = SupplierStatus.ACTIVE
    db.commit()
    return api_response(message="已恢复合作")
