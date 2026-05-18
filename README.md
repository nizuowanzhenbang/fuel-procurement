# 发电厂燃料采购管理系统 (Fuel Procurement)

> 供应商准入 → 合同执行 → 订单履约 全流程闭环管理

## 业务范围

发电厂燃料部最常用的采购管理三大模块：

1. **供应商管理** — 准入审核、信用评级、煤种/产地档案、状态流转
2. **采购合同** — 长协/现货/框架协议、煤质基准、审批流、累计履约统计
3. **采购订单** — 关联合同、计划/实际到货、分批到货、运输方式、结算

## 核心特征

- **发电厂燃料业务特色**：
  - 煤种：动力煤 / 长焰煤 / 弱粘煤 / 1/3焦煤 / 褐煤 / 混煤
  - 计价方式：到厂价 / 坑口价 / 车板价 / 到港价
  - 合同类型：长协 / 现货 / 框架
  - 煤质验收基准（合同里写明热值/灰分/硫分/水分上限）
- **状态机**：
  - 供应商：待审核 → 已准入 → 暂停/黑名单/归档
  - 合同：草稿 → 待审批 → 生效 → 完成/到期/解除
  - 订单：计划中 → 已发运 → 部分到货 → 已到货 → 已结算
- **自动累计**：订单到货量自动汇总到合同的 `delivered_quantity`，达 99% 自动完成

## 技术栈

- **后端**：FastAPI + SQLAlchemy + Pydantic v2 + JWT
- **前端**：React 18 + TypeScript + Ant Design 5 + ECharts + Zustand + Vite

## 快速开始

### 后端

```bash
cd backend
pip install -r requirements.txt
python seed_data.py     # 生成演示数据（8 供应商 + 15 合同 + ~40 订单）
uvicorn app.main:app --reload --port 8000
```

API 文档：http://localhost:8000/docs

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问：http://localhost:5173

**默认账户**：`admin` / `admin123`

## 数据流程

```
供应商登记 → 准入审核（PENDING_REVIEW → ACTIVE）
       ↓
新建合同（DRAFT → 提交审批 → 审批 → ACTIVE）
       ↓
基于合同下订单（PLANNED）
       ↓
确认发运 → 登记到货（可分批）→ RECEIVED
       ↓
结算 → SETTLED
       ↓
合同累计履约量自动汇总，达 99% → COMPLETED
```

## 与已有系统的联动

`fuel-procurement` 与 `coal-quality-monitor` 共享"供应商"实体（按名称匹配）：
- 煤质系统的供应商信用分（基于实际到货质量+运输异常）可作为本系统采购决策依据
- 本系统的合同煤质基准（热值/灰分/硫分/水分上限）应与煤质验收阈值一致

未来 v2.0 计划加入：
- 通过 `QUALITY_SYSTEM_URL` 调用煤质系统 API，在供应商列表展示其在煤质系统中的信用分
- 招标比价模块（多供应商报价对比）
- 长协合同自动续签提醒

## 项目结构

```
fuel-procurement/
├── backend/
│   ├── app/
│   │   ├── api/          # auth/suppliers/contracts/orders/dashboard
│   │   ├── models/       # User/Supplier/FuelContract/PurchaseOrder
│   │   ├── schemas/
│   │   ├── utils/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   └── seed_data.py
└── frontend/
    └── src/
        ├── pages/        # Dashboard/SupplierList/ContractList/OrderList/LoginPage
        ├── components/   # Layout
        ├── api/
        ├── stores/
        └── types/
```

## 路线图

- **v1.0**（当前）：供应商 + 合同 + 订单 + Dashboard
- v2.0：与 coal-quality-monitor 集成（供应商信用分双向同步）
- v3.0：招标比价模块（多供应商报价对比）
- v4.0：发票管理 + 应付账款 + 与财务系统对接
