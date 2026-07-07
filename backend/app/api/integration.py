"""上下游集成接口：暴露给煤场库存系统（coal-yard-management）调用。

- GET /api/integration/order-info?order_no=  → 拉订单到货信息
- POST /api/integration/yard-stocked         → 接收"已入煤场"通知，自动登记到货

鉴权：header X-Integration-Token，与 settings.INTEGRATION_SECRET 比对。
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db
from app.config import settings
from app.models.contract import FuelContract, ContractStatus
from app.models.order import PurchaseOrder, OrderStatus
from app.utils.helpers import api_response

router = APIRouter(prefix="/api/integration", tags=["闭环集成"])


def _verify_token(x_integration_token: Optional[str] = Header(None, alias="X-Integration-Token")):
    if not x_integration_token or x_integration_token != settings.INTEGRATION_SECRET:
        raise HTTPException(status_code=401, detail="集成 token 校验失败")


@router.get("/order-info", dependencies=[Depends(_verify_token)])
def get_order_info(order_no: str, db: Session = Depends(get_db)):
    """按订单号返回履约信息，供煤场入场时拉取核对。"""
    order = (
        db.query(PurchaseOrder)
        .options(joinedload(PurchaseOrder.contract).joinedload(FuelContract.supplier))
        .filter(PurchaseOrder.order_no == order_no)
        .first()
    )
    if not order:
        raise HTTPException(404, f"订单不存在：{order_no}")

    contract = order.contract
    supplier = contract.supplier if contract else None
    data = {
        "order_no": order.order_no,
        "status": order.status.value if order.status else None,
        "planned_quantity": order.planned_quantity,
        "delivered_quantity": order.delivered_quantity or 0,
        "unit_price": order.unit_price,
        "planned_delivery_date": order.planned_delivery_date.isoformat() if order.planned_delivery_date else None,
        "actual_delivery_date": order.actual_delivery_date.isoformat() if order.actual_delivery_date else None,
        "transport_mode": order.transport_mode,
        "departure_port": order.departure_port,
        "arrival_plant": order.arrival_plant,
        "contract_no": contract.contract_no if contract else None,
        "coal_type": contract.coal_type if contract else None,
        "coal_origin": contract.coal_origin if contract else None,
        "supplier_name": supplier.name if supplier else None,
        "supplier_code": supplier.code if supplier else None,
        # 合同煤质基准，便于煤场入场时与化验值比对
        "spec_calorific_value": contract.spec_calorific_value if contract else None,
        "spec_ash_max": contract.spec_ash_max if contract else None,
        "spec_sulfur_max": contract.spec_sulfur_max if contract else None,
        "spec_moisture_max": contract.spec_moisture_max if contract else None,
    }
    return api_response(data=data)


class YardStockedPayload(BaseModel):
    order_no: str = Field(..., description="订单编号")
    yard_code: str = Field(..., description="入煤场堆区编码")
    quantity: float = Field(..., gt=0, description="本次入场量（吨）")
    stocked_at: Optional[datetime] = Field(None, description="实际入场时间，缺省取服务端 utcnow")
    notes: Optional[str] = Field(None, description="备注")


@router.post("/yard-stocked", dependencies=[Depends(_verify_token)])
def receive_yard_stocked(payload: YardStockedPayload, db: Session = Depends(get_db)):
    """煤场入场后回传到货信息，自动累计到订单 delivered_quantity 并推进状态机。

    与 /api/orders/{id}/receive 共享履约逻辑，但走集成密钥免登录。
    """
    order = (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.order_no == payload.order_no)
        .first()
    )
    if not order:
        raise HTTPException(404, f"订单不存在：{payload.order_no}")
    if order.status in (OrderStatus.SETTLED, OrderStatus.CANCELLED):
        raise HTTPException(400, "已结算/已取消订单不可登记入场")

    order.delivered_quantity = round((order.delivered_quantity or 0) + payload.quantity, 2)
    order.actual_delivery_date = payload.stocked_at or datetime.utcnow()

    if order.delivered_quantity >= order.planned_quantity * 0.99:
        order.status = OrderStatus.RECEIVED
    else:
        order.status = OrderStatus.PARTIAL_RECEIVED

    note_line = f"[煤场入库] 堆区 {payload.yard_code} 入 {payload.quantity:.2f} 吨"
    if payload.notes:
        note_line += f"，{payload.notes}"
    order.notes = (order.notes + "\n" if order.notes else "") + note_line

    # 同步累计到合同
    contract = db.query(FuelContract).filter(FuelContract.id == order.contract_id).first()
    if contract:
        delivered_sum = (
            db.query(func.sum(PurchaseOrder.delivered_quantity))
            .filter(PurchaseOrder.contract_id == contract.id)
            .scalar() or 0
        )
        contract.delivered_quantity = round(delivered_sum, 2)
        if (
            contract.status == ContractStatus.ACTIVE
            and contract.delivered_quantity >= contract.contract_quantity * 0.99
        ):
            contract.status = ContractStatus.COMPLETED

    db.commit()
    db.refresh(order)

    return api_response(
        message="已记录入场",
        data={
            "order_no": order.order_no,
            "status": order.status.value if order.status else None,
            "delivered_quantity": order.delivered_quantity,
            "planned_quantity": order.planned_quantity,
        },
    )
