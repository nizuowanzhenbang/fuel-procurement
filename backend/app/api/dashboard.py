"""仪表盘 API"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_current_user
from app.models.contract import FuelContract, ContractStatus, ContractType
from app.models.order import PurchaseOrder, OrderStatus
from app.models.supplier import Supplier, SupplierStatus
from app.models.supplier_quality_score import SupplierQualityScore
from app.models.user import User
from app.utils.helpers import api_response

router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_suppliers = db.query(func.count(Supplier.id)).filter(
        Supplier.status == SupplierStatus.ACTIVE
    ).scalar() or 0

    pending_review = db.query(func.count(Supplier.id)).filter(
        Supplier.status == SupplierStatus.PENDING_REVIEW
    ).scalar() or 0

    active_contracts = db.query(func.count(FuelContract.id)).filter(
        FuelContract.status == ContractStatus.ACTIVE
    ).scalar() or 0

    pending_approval = db.query(func.count(FuelContract.id)).filter(
        FuelContract.status == ContractStatus.PENDING_APPROVAL
    ).scalar() or 0

    # 本月采购量与金额
    month_qty = db.query(func.coalesce(func.sum(PurchaseOrder.delivered_quantity), 0)).filter(
        PurchaseOrder.actual_delivery_date >= month_start
    ).scalar() or 0
    month_amount = db.query(func.coalesce(func.sum(PurchaseOrder.delivered_amount), 0)).filter(
        PurchaseOrder.settled_at >= month_start
    ).scalar() or 0

    # 在途订单
    in_transit = db.query(func.count(PurchaseOrder.id)).filter(
        PurchaseOrder.status.in_([OrderStatus.DISPATCHED, OrderStatus.PARTIAL_RECEIVED])
    ).scalar() or 0

    # 平均到厂单价（本月已结算）
    avg_price = db.query(func.avg(PurchaseOrder.unit_price)).filter(
        PurchaseOrder.settled_at >= month_start
    ).scalar()

    return api_response(data={
        "active_suppliers": total_suppliers,
        "pending_review": pending_review,
        "active_contracts": active_contracts,
        "pending_approval": pending_approval,
        "month_delivered_tons": round(float(month_qty), 1),
        "month_settled_amount": round(float(month_amount), 2),
        "in_transit_orders": in_transit,
        "avg_unit_price": round(float(avg_price), 2) if avg_price else None,
    })


@router.get("/monthly-quantity")
def monthly_quantity(months: int = Query(6, ge=3, le=24), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """近 N 月采购量趋势"""
    now = datetime.utcnow()
    start = (now.replace(day=1) - timedelta(days=months * 31)).replace(day=1)

    orders = db.query(PurchaseOrder).filter(
        PurchaseOrder.actual_delivery_date.isnot(None),
        PurchaseOrder.actual_delivery_date >= start,
    ).all()

    monthly: dict = {}
    for o in orders:
        key = o.actual_delivery_date.strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = {"month": key, "quantity": 0.0, "amount": 0.0}
        monthly[key]["quantity"] += o.delivered_quantity or 0
        monthly[key]["amount"] += o.delivered_amount or 0
    return api_response(data=sorted([
        {"month": v["month"], "quantity": round(v["quantity"], 1), "amount": round(v["amount"], 2)}
        for v in monthly.values()
    ], key=lambda x: x["month"]))


@router.get("/supplier-share")
def supplier_share(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """供应商采购量占比（按近 90 天到货量）"""
    start = datetime.utcnow() - timedelta(days=90)
    rows = (
        db.query(Supplier.name, func.coalesce(func.sum(PurchaseOrder.delivered_quantity), 0).label("qty"))
        .join(FuelContract, FuelContract.supplier_id == Supplier.id)
        .join(PurchaseOrder, PurchaseOrder.contract_id == FuelContract.id)
        .filter(PurchaseOrder.actual_delivery_date >= start)
        .group_by(Supplier.name)
        .order_by(func.sum(PurchaseOrder.delivered_quantity).desc())
        .all()
    )
    return api_response(data=[
        {"supplier_name": r[0], "quantity": round(float(r[1]), 1)}
        for r in rows
    ])


@router.get("/price-trend")
def price_trend(days: int = Query(90, ge=30, le=365), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """单价趋势（按结算日）"""
    start = datetime.utcnow() - timedelta(days=days)
    orders = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.contract)
    ).filter(
        PurchaseOrder.settled_at.isnot(None),
        PurchaseOrder.settled_at >= start,
    ).all()

    daily: dict = {}
    for o in orders:
        key = o.settled_at.strftime("%Y-%m-%d")
        if key not in daily:
            daily[key] = {"date": key, "prices": []}
        daily[key]["prices"].append(o.unit_price)
    return api_response(data=sorted([
        {"date": v["date"], "avg_price": round(sum(v["prices"]) / len(v["prices"]), 2)}
        for v in daily.values()
    ], key=lambda x: x["date"]))


@router.get("/supplier-quality-ranking")
def supplier_quality_ranking(
    limit: int = Query(10, ge=3, le=30),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """供应商质量综合评分排名（取每个供应商最新一条评分）"""
    # 子查询：每个供应商最新评分时间
    sub = (
        db.query(
            SupplierQualityScore.supplier_name,
            func.max(SupplierQualityScore.evaluated_at).label("latest"),
        )
        .group_by(SupplierQualityScore.supplier_name)
        .subquery()
    )
    rows = (
        db.query(SupplierQualityScore)
        .join(
            sub,
            (SupplierQualityScore.supplier_name == sub.c.supplier_name)
            & (SupplierQualityScore.evaluated_at == sub.c.latest),
        )
        .order_by(SupplierQualityScore.score.desc())
        .limit(limit)
        .all()
    )
    # 关联供应商（取等级 / 信用分）
    name_to_supplier = {
        s.name: s for s in db.query(Supplier).filter(
            Supplier.name.in_([r.supplier_name for r in rows])
        ).all()
    }
    data = []
    for idx, r in enumerate(rows, 1):
        s = name_to_supplier.get(r.supplier_name)
        data.append({
            "rank": idx,
            "supplier_name": r.supplier_name,
            "score": round(r.score, 1),
            "sample_count": r.sample_count,
            "pass_rate": round(r.pass_rate, 1) if r.pass_rate is not None else None,
            "evaluated_at": r.evaluated_at.isoformat(),
            "tier": s.tier.value if s and s.tier else None,
            "credit_score": s.credit_score if s else None,
        })
    return api_response(data=data)


@router.get("/expiring-contracts")
def expiring_contracts(
    days: int = Query(30, ge=7, le=180),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """长协合同到期前 N 天提醒（默认 30 天）"""
    now = datetime.utcnow()
    deadline = now + timedelta(days=days)
    rows = (
        db.query(FuelContract)
        .options(joinedload(FuelContract.supplier))
        .filter(
            FuelContract.status == ContractStatus.ACTIVE,
            FuelContract.contract_type == ContractType.LONG_TERM,
            FuelContract.expiry_date <= deadline,
            FuelContract.expiry_date >= now,
        )
        .order_by(FuelContract.expiry_date)
        .all()
    )
    data = []
    for c in rows:
        days_left = (c.expiry_date - now).days
        remaining = (c.contract_quantity or 0) - (c.delivered_quantity or 0)
        completion = (c.delivered_quantity or 0) / c.contract_quantity * 100 if c.contract_quantity else 0
        data.append({
            "id": c.id,
            "contract_no": c.contract_no,
            "supplier_name": c.supplier.name if c.supplier else None,
            "coal_type": c.coal_type,
            "expiry_date": c.expiry_date.isoformat(),
            "days_left": days_left,
            "contract_quantity": c.contract_quantity,
            "delivered_quantity": c.delivered_quantity or 0,
            "remaining_quantity": round(remaining, 1),
            "completion_rate": round(completion, 1),
            "unit_price": c.unit_price,
        })
    return api_response(data=data)


@router.get("/coal-type-share")
def coal_type_share(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """煤种采购量占比"""
    start = datetime.utcnow() - timedelta(days=90)
    rows = (
        db.query(FuelContract.coal_type, func.coalesce(func.sum(PurchaseOrder.delivered_quantity), 0).label("qty"))
        .join(PurchaseOrder, PurchaseOrder.contract_id == FuelContract.id)
        .filter(PurchaseOrder.actual_delivery_date >= start)
        .group_by(FuelContract.coal_type)
        .all()
    )
    return api_response(data=[
        {"coal_type": r[0], "quantity": round(float(r[1]), 1)}
        for r in rows
    ])
