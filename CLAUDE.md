# Claude Code 项目规则

## 项目定位

发电厂燃料采购管理系统。v1.0 聚焦"供应商→合同→订单"三层闭环。独立部署，未来可与 coal-quality-monitor 集成（供应商打分双向同步）。

## 技术栈约束

- 后端：FastAPI + SQLAlchemy + Pydantic v2，沿用 plant-safety / coal-quality-monitor 的同款分层结构
- 前端：React 18 + TypeScript + Ant Design 5 + ECharts + Zustand + Vite
- 数据库：SQLite（开发）/ PostgreSQL（生产）
- 认证：JWT (OAuth2PasswordBearer)

## 业务规则

### 供应商状态机
- `PENDING_REVIEW`（新登记） → 审核 → `ACTIVE` 或 `ARCHIVED`
- `ACTIVE` → 暂停 → `SUSPENDED` → 恢复 → `ACTIVE`
- `ACTIVE` / `SUSPENDED` → 拉黑 → `BLACKLISTED`（v2 加）
- 仅 `ACTIVE` 状态的供应商可签订合同

### 合同状态机
- `DRAFT` → 提交 → `PENDING_APPROVAL` → 审批 → `ACTIVE`（通过）或 `DRAFT`（退回）
- `ACTIVE` → 解除 → `TERMINATED`
- `ACTIVE` → 累计交付达 99% → 自动 `COMPLETED`
- 仅 `DRAFT` / `PENDING_APPROVAL` 状态可修改

### 订单状态机
- `PLANNED` → 发运 → `DISPATCHED` → 部分到货 → `PARTIAL_RECEIVED` → 满载到货 → `RECEIVED` → 结算 → `SETTLED`
- 到货量达计划 99% 视为完整到货
- `PLANNED` / `DISPATCHED` 可取消，已结算/已取消不可改

### 编号规则
- 供应商：`GYS-NNNN`（顺序）
- 合同：`HT-YYYYMM-NNNN`（月度顺序）
- 订单：`PO-YYYYMMDD-NNNN`（日期顺序）

## 与已有系统的关系

- 共享"供应商名称"作为关联键（与 coal-quality-monitor 一致）
- 合同的煤质基准（spec_calorific_value/ash_max/sulfur_max/moisture_max）字段名与 coal-quality-monitor 的 contract_calorific_value 等字段对应

未来集成：
- 配置 `QUALITY_SYSTEM_URL` 后，供应商详情可显示煤质系统的信用分
- 煤质系统的供应商打分变化可 webhook 推送过来，影响采购优先级（v3 加）

## 代码风格

- API 响应统一 `{code, message, data}`，使用 `utils.helpers.api_response`
- 分页用 `paginate_response`
- 中文 docstring 和字段注释
- 前端中文 locale + 中文 label

## 已知简化

- 合同审批仅单级（v2 加多级审批）
- 招标比价、发票管理未实现
- 没有角色权限拦截（仅校验登录）
- 没有 WebSocket（采购场景无强实时需求）
- 单价历史变更未追踪（仅记录当前价）
