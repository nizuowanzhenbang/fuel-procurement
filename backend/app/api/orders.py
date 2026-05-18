"""采购订单 API"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_current_user
from app.models.contract import FuelContract, ContractStatus
from app.models.order import PurchaseOrder, OrderStatus
from app.models.user import User
from app.schemas.order import (
    OrderCreate, OrderUpdate, OrderReceive, OrderSettle, OrderResponse,
)
from app.utils.helpers import api_response, paginate_response, generate_order_no

router = APIRouter(prefix="/api/orders", tags=["采购订单"])


def _enrich(o: PurchaseOrder) -> dict:
    result = OrderResponse.model_validate(o).model_dump()
    if o.contract:
        result["contract_no"] = o.contract.contract_no
        result["coal_type"] = o.contract.coal_type
        if o.contract.supplier:
            result["supplier_name"] = o.contract.supplier.name
    return result


@router.get("")
def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatus] = None,
    contract_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.contract).joinedload(FuelContract.supplier)
    )
    if status:
        q = q.filter(PurchaseOrder.status == status)
    if contract_id:
        q = q.filter(PurchaseOrder.contract_id == contract_id)

    total = q.count()
    rows = (
        q.order_by(PurchaseOrder.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [_enrich(r) for r in rows]
    return api_response(data=paginate_response(items, total, page, page_size))


@router.post("")
def create_order(payload: OrderCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    contract = db.query(FuelContract).filter(FuelContract.id == payload.contract_id).first()
    if not contract:
        raise HTTPException(404, "合同不存在")
    if contract.status != ContractStatus.ACTIVE:
        raise HTTPException(400, "仅生效合同可下订单")

    remaining = contract.contract_quantity - (contract.delivered_quantity or 0)
    if payload.planned_quantity > remaining:
        raise HTTPException(400, f"超出合同剩余量（剩余 {remaining:.0f} 吨）")

    unit_price = payload.unit_price or contract.unit_price
    planned_amount = round(payload.planned_quantity * unit_price / 10000, 2)

    next_seq = (db.query(func.count(PurchaseOrder.id)).scalar() or 0) + 1
    order = PurchaseOrder(
        order_no=generate_order_no(next_seq),
        contract_id=contract.id,
        planned_quantity=payload.planned_quantity,
        unit_price=unit_price,
        planned_amount=planned_amount,
        planned_delivery_date=payload.planned_delivery_date,
        transport_mode=payload.transport_mode,
        departure_port=payload.departure_port,
        arrival_plant=payload.arrival_plant,
        notes=payload.notes,
        status=OrderStatus.PLANNED,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return api_response(message="订单已创建", data=_enrich(order))


@router.get("/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    o = (
        db.query(PurchaseOrder)
        .options(joinedload(PurchaseOrder.contract).joinedload(FuelContract.supplier))
        .filter(PurchaseOrder.id == order_id)
        .first()
    )
    if not o:
        raise HTTPException(404, "订单不存在")
    return api_response(data=_enrich(o))


@router.put("/{order_id}")
def update_order(
    order_id: int, payload: OrderUpdate,
    db: Session = Depends(get_db), _: User = Depends(get_current_user),
):
    o = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    if o.status in (OrderStatus.SETTLED, OrderStatus.CANCELLED):
        raise HTTPException(400, "已结算/已取消订单不可修改")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(o, field, value)
    if o.planned_quantity and o.unit_price:
        o.planned_amount = round(o.planned_quantity * o.unit_price / 10000, 2)
    db.commit()
    db.refresh(o)
    return api_response(message="已更新", data=_enrich(o))


@router.post("/{order_id}/dispatch")
def dispatch_order(order_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    o = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    if o.status != OrderStatus.PLANNED:
        raise HTTPException(400, "仅计划中订单可发运")
    o.status = OrderStatus.DISPATCHED
    db.commit()
    return api_response(message="已发运")


@router.post("/{order_id}/receive")
def receive_order(
    order_id: int, payload: OrderReceive,
    db: Session = Depends(get_db), _: User = Depends(get_current_user),
):
    """到货登记，支持部分到货"""
    o = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    if o.status in (OrderStatus.SETTLED, OrderStatus.CANCELLED):
        raise HTTPException(400, "已结算/已取消订单不可登记")

    o.delivered_quantity = (o.delivered_quantity or 0) + payload.delivered_quantity
    if payload.actual_delivery_date:
        o.actual_delivery_date = payload.actual_delivery_date

    if o.delivered_quantity >= o.planned_quantity * 0.99:
        o.status = OrderStatus.RECEIVED
        if not o.actual_delivery_date:
            o.actual_delivery_date = datetime.utcnow()
    else:
        o.status = OrderStatus.PARTIAL_RECEIVED

    # 同步更新合同累计交付量
    contract = db.query(FuelContract).filter(FuelContract.id == o.contract_id).first()
    if contract:
        delivered_sum = (
            db.query(func.sum(PurchaseOrder.delivered_quantity))
            .filter(PurchaseOrder.contract_id == contract.id)
            .scalar() or 0
        )
        contract.delivered_quantity = round(delivered_sum, 2)
        if contract.delivered_quantity >= contract.contract_quantity * 0.99:
            contract.status = ContractStatus.COMPLETED

    db.commit()
    db.refresh(o)
    return api_response(message="到货已登记", data=_enrich(o))


@router.post("/{order_id}/settle")
def settle_order(
    order_id: int, payload: OrderSettle,
    db: Session = Depends(get_db), _: User = Depends(get_current_user),
):
    """结算订单"""
    o = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    if o.status != OrderStatus.RECEIVED:
        raise HTTPException(400, "仅已到货订单可结算")

    o.delivered_amount = payload.delivered_amount or round(
        (o.delivered_quantity or 0) * o.unit_price / 10000, 2
    )
    o.settled_by = payload.settled_by
    o.settled_at = datetime.utcnow()
    o.status = OrderStatus.SETTLED
    if payload.notes:
        o.notes = (o.notes or "") + f"\n[结算] {payload.notes}"
    db.commit()
    db.refresh(o)
    return api_response(message="已结算", data=_enrich(o))


@router.post("/{order_id}/cancel")
def cancel_order(order_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    o = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    if o.status in (OrderStatus.SETTLED, OrderStatus.CANCELLED):
        raise HTTPException(400, "已结算/已取消订单不可取消")
    o.status = OrderStatus.CANCELLED
    db.commit()
    return api_response(message="已取消")
