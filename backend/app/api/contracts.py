"""合同 API"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, get_current_user, require_write, require_approver
from app.models.contract import FuelContract, ContractStatus
from app.models.contract_approval import ContractApproval, ApprovalLevelStatus
from app.models.contract_price_history import ContractPriceHistory
from app.models.supplier import Supplier, SupplierStatus
from app.models.user import User
from app.schemas.contract import (
    ContractCreate, ContractUpdate, ContractApprove, ContractResponse,
)
from app.schemas.contract_approval import (
    ApprovalLevelResponse, ApprovalLevelAction,
    PriceHistoryResponse, PriceUpdatePayload,
)
from app.utils.helpers import api_response, paginate_response, generate_contract_no
from app.utils.csv_export import stream_csv, fmt_dt, fmt_date

router = APIRouter(prefix="/api/contracts", tags=["采购合同"])


# ===== 多级审批配置 =====
# 阈值单位：万元
LEVEL_RULES = [
    (1, "采购主管"),
    (2, "燃料部主任"),
    (3, "总经理"),
]


def _required_levels(total_amount: float) -> List[tuple]:
    """金额→需要的审批级别。<100 万 1 级，100-500 万 2 级，>500 万 3 级。"""
    if total_amount < 100:
        return LEVEL_RULES[:1]
    if total_amount <= 500:
        return LEVEL_RULES[:2]
    return LEVEL_RULES[:3]


def _create_approval_chain(db: Session, contract: FuelContract) -> None:
    """为合同创建审批链（删除旧的、按当前金额重新生成）"""
    db.query(ContractApproval).filter(ContractApproval.contract_id == contract.id).delete()
    for level, name in _required_levels(contract.total_amount):
        db.add(ContractApproval(
            contract_id=contract.id,
            level=level,
            level_name=name,
            status=ApprovalLevelStatus.PENDING,
        ))


def _current_pending_level(db: Session, contract_id: int) -> Optional[ContractApproval]:
    """合同当前待审批的最低级别记录"""
    return (
        db.query(ContractApproval)
        .filter(
            ContractApproval.contract_id == contract_id,
            ContractApproval.status == ApprovalLevelStatus.PENDING,
        )
        .order_by(ContractApproval.level)
        .first()
    )


# ===== CRUD =====

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


@router.get("/export")
def export_contracts(
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
    rows = q.order_by(FuelContract.created_at.desc()).all()

    headers = [
        "合同编号", "供应商", "类型", "煤种", "产地", "数量(吨)", "单价(元/吨)",
        "总金额(万元)", "已交付(吨)", "状态", "生效", "到期", "审批人", "审批时间",
    ]
    data = []
    for r in rows:
        type_map = {"LONG_TERM": "长协", "SPOT": "现货", "FRAMEWORK": "框架"}
        data.append([
            r.contract_no, r.supplier.name if r.supplier else "",
            type_map.get(r.contract_type.value, ""),
            r.coal_type, r.coal_origin or "",
            r.contract_quantity, r.unit_price, r.total_amount,
            r.delivered_quantity or 0, r.status.value if r.status else "",
            fmt_date(r.effective_date), fmt_date(r.expiry_date),
            r.approved_by or "", fmt_dt(r.approved_at),
        ])
    return stream_csv("合同列表", headers, data)


@router.post("")
def create_contract(
    payload: ContractCreate, db: Session = Depends(get_db),
    _: User = Depends(require_write),
):
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
        .options(
            joinedload(FuelContract.supplier),
            joinedload(FuelContract.approvals),
            joinedload(FuelContract.price_history),
        )
        .filter(FuelContract.id == contract_id)
        .first()
    )
    if not c:
        raise HTTPException(404, "合同不存在")
    result = ContractResponse.model_validate(c).model_dump()
    result["supplier_name"] = c.supplier.name if c.supplier else None
    result["approvals"] = [
        ApprovalLevelResponse.model_validate(a).model_dump() for a in c.approvals
    ]
    result["price_history"] = [
        PriceHistoryResponse.model_validate(p).model_dump() for p in c.price_history
    ]
    return api_response(data=result)


@router.put("/{contract_id}")
def update_contract(
    contract_id: int, payload: ContractUpdate,
    db: Session = Depends(get_db), current: User = Depends(require_write),
):
    c = db.query(FuelContract).filter(FuelContract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "合同不存在")
    if c.status not in (ContractStatus.DRAFT, ContractStatus.PENDING_APPROVAL):
        raise HTTPException(400, "仅草稿/待审批合同可修改，已生效合同请使用价格调整接口")

    data = payload.model_dump(exclude_unset=True)
    old_price = c.unit_price
    for field, value in data.items():
        setattr(c, field, value)
    if c.contract_quantity and c.unit_price:
        c.total_amount = round(c.contract_quantity * c.unit_price / 10000, 2)
    # 草稿阶段的单价变更也写入历史（追溯创建期的调价）
    if "unit_price" in data and data["unit_price"] != old_price:
        db.add(ContractPriceHistory(
            contract_id=c.id,
            old_price=old_price,
            new_price=c.unit_price,
            changed_by=current.username,
            reason="草稿期调整",
        ))
    db.commit()
    db.refresh(c)
    return api_response(message="已更新", data=ContractResponse.model_validate(c).model_dump())


@router.post("/{contract_id}/submit")
def submit_contract(
    contract_id: int, db: Session = Depends(get_db),
    _: User = Depends(require_write),
):
    """提交审批：按金额生成多级审批链"""
    c = db.query(FuelContract).filter(FuelContract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "合同不存在")
    if c.status != ContractStatus.DRAFT:
        raise HTTPException(400, "仅草稿可提交")

    _create_approval_chain(db, c)
    c.status = ContractStatus.PENDING_APPROVAL
    db.commit()
    levels = _required_levels(c.total_amount)
    return api_response(
        message=f"已提交审批（共 {len(levels)} 级：{' → '.join(n for _, n in levels)}）",
    )


@router.post("/{contract_id}/approve")
def approve_contract(
    contract_id: int, payload: ContractApprove,
    db: Session = Depends(get_db), current: User = Depends(require_approver),
):
    """审批合同：自动定位当前待审级别。
    通过 → 推进到下一级；最后一级通过 → 合同 ACTIVE。
    拒绝 → 整条审批链作废，合同退回 DRAFT。
    """
    c = db.query(FuelContract).filter(FuelContract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "合同不存在")
    if c.status != ContractStatus.PENDING_APPROVAL:
        raise HTTPException(400, "仅待审批合同可审批")

    pending = _current_pending_level(db, c.id)
    if not pending:
        raise HTTPException(400, "审批链异常：无待审记录")

    approver_name = payload.approver or current.username

    if payload.approved:
        pending.status = ApprovalLevelStatus.APPROVED
        pending.approver = approver_name
        pending.approved_at = datetime.utcnow()
        pending.notes = payload.notes

        next_pending = (
            db.query(ContractApproval)
            .filter(
                ContractApproval.contract_id == c.id,
                ContractApproval.status == ApprovalLevelStatus.PENDING,
                ContractApproval.level > pending.level,
            )
            .order_by(ContractApproval.level)
            .first()
        )
        if not next_pending:
            c.status = ContractStatus.ACTIVE
            c.approved_by = approver_name
            c.approved_at = datetime.utcnow()
            msg = f"第 {pending.level} 级通过，合同最终生效"
        else:
            msg = f"第 {pending.level} 级通过，待 {next_pending.level_name} 审批"
    else:
        pending.status = ApprovalLevelStatus.REJECTED
        pending.approver = approver_name
        pending.approved_at = datetime.utcnow()
        pending.notes = payload.notes
        c.status = ContractStatus.DRAFT
        if payload.notes:
            c.notes = (c.notes or "") + f"\n[{pending.level_name}驳回] {payload.notes}"
        msg = f"{pending.level_name} 驳回，合同退回草稿"

    db.commit()
    db.refresh(c)
    return api_response(message=msg, data=ContractResponse.model_validate(c).model_dump())


@router.post("/{contract_id}/terminate")
def terminate_contract(
    contract_id: int, db: Session = Depends(get_db),
    _: User = Depends(require_approver),
):
    c = db.query(FuelContract).filter(FuelContract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "合同不存在")
    if c.status != ContractStatus.ACTIVE:
        raise HTTPException(400, "仅生效合同可解除")
    c.status = ContractStatus.TERMINATED
    db.commit()
    return api_response(message="合同已解除")


# ===== 价格调整（生效合同的单价审计） =====

@router.post("/{contract_id}/adjust-price")
def adjust_price(
    contract_id: int, payload: PriceUpdatePayload,
    db: Session = Depends(get_db), current: User = Depends(require_approver),
):
    """已生效合同的单价调整（审计入历史，重新计算总金额）"""
    c = db.query(FuelContract).filter(FuelContract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "合同不存在")
    if c.status not in (ContractStatus.ACTIVE, ContractStatus.PENDING_APPROVAL):
        raise HTTPException(400, "仅生效/待审批合同可调价")
    if payload.new_price <= 0:
        raise HTTPException(400, "调整后单价必须大于 0")
    if abs(payload.new_price - c.unit_price) < 0.01:
        raise HTTPException(400, "调整后价格与当前价格相同")

    db.add(ContractPriceHistory(
        contract_id=c.id,
        old_price=c.unit_price,
        new_price=payload.new_price,
        changed_by=current.username,
        reason=payload.reason or "价格调整",
    ))
    c.unit_price = payload.new_price
    c.total_amount = round(c.contract_quantity * payload.new_price / 10000, 2)
    db.commit()
    db.refresh(c)
    return api_response(
        message="价格已调整，已写入审计历史",
        data=ContractResponse.model_validate(c).model_dump(),
    )


@router.get("/{contract_id}/price-history")
def get_price_history(
    contract_id: int, db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    c = db.query(FuelContract).filter(FuelContract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "合同不存在")
    rows = (
        db.query(ContractPriceHistory)
        .filter(ContractPriceHistory.contract_id == contract_id)
        .order_by(ContractPriceHistory.created_at.desc())
        .all()
    )
    return api_response(data=[PriceHistoryResponse.model_validate(r).model_dump() for r in rows])


@router.get("/{contract_id}/approvals")
def get_approvals(
    contract_id: int, db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = (
        db.query(ContractApproval)
        .filter(ContractApproval.contract_id == contract_id)
        .order_by(ContractApproval.level)
        .all()
    )
    return api_response(data=[ApprovalLevelResponse.model_validate(r).model_dump() for r in rows])
