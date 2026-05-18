import { useState, useEffect, useCallback } from 'react'
import {
  Card, Table, Tag, Button, Space, Modal, Form, Input, Select,
  DatePicker, message, Descriptions, Row, Col, InputNumber, Progress,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, ReloadOutlined, EyeOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { contractApi, supplierApi } from '../api'
import type { Contract, ContractStatus, ContractType, PricingMode, Supplier } from '../types'

const STATUS_LABEL: Record<ContractStatus, { label: string; color: string }> = {
  DRAFT: { label: '草稿', color: 'default' },
  PENDING_APPROVAL: { label: '待审批', color: 'warning' },
  ACTIVE: { label: '生效中', color: 'success' },
  COMPLETED: { label: '已完成', color: 'blue' },
  EXPIRED: { label: '已到期', color: 'error' },
  TERMINATED: { label: '已解除', color: 'red' },
}

const TYPE_LABEL: Record<ContractType, string> = {
  LONG_TERM: '长协', SPOT: '现货', FRAMEWORK: '框架',
}

const PRICING_LABEL: Record<PricingMode, string> = {
  DELIVERED: '到厂价', EX_MINE: '坑口价', FOB: '车板价', CIF: '到港价',
}

export default function ContractList() {
  const [data, setData] = useState<Contract[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState<{ status?: ContractStatus; keyword?: string }>({})
  const [createOpen, setCreateOpen] = useState(false)
  const [detail, setDetail] = useState<Contract | null>(null)
  const [approveOpen, setApproveOpen] = useState(false)
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [form] = Form.useForm()
  const [approveForm] = Form.useForm()

  const load = useCallback(async (p = page, ps = pageSize, f = filters) => {
    setLoading(true)
    try {
      const res = await contractApi.list({ page: p, page_size: ps, ...f })
      setData(res.data.items)
      setTotal(res.data.total)
    } catch {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, filters])

  useEffect(() => {
    load(1, 20, {})
    supplierApi.list({ page: 1, page_size: 100, status: 'ACTIVE' }).then((r) => setSuppliers(r.data.items))
  }, [])

  const handleCreate = async (values: {
    effective_date: dayjs.Dayjs; expiry_date: dayjs.Dayjs;
  } & Partial<Contract>) => {
    try {
      const payload = {
        ...values,
        effective_date: values.effective_date.toISOString(),
        expiry_date: values.expiry_date.toISOString(),
      }
      await contractApi.create(payload as Partial<Contract>)
      message.success('合同已创建')
      setCreateOpen(false)
      form.resetFields()
      load()
    } catch (e: unknown) {
      message.error((e as { detail?: string })?.detail || '创建失败')
    }
  }

  const handleApprove = async (values: { approver: string; approved: boolean; notes?: string }) => {
    if (!detail) return
    try {
      await contractApi.approve(detail.id, values.approver, values.approved, values.notes)
      message.success(values.approved ? '审批通过' : '已退回草稿')
      setApproveOpen(false); approveForm.resetFields(); setDetail(null); load()
    } catch (e: unknown) {
      message.error((e as { detail?: string })?.detail || '操作失败')
    }
  }

  const columns: ColumnsType<Contract> = [
    { title: '合同编号', dataIndex: 'contract_no', width: 150 },
    { title: '供应商', dataIndex: 'supplier_name', ellipsis: true, width: 180 },
    { title: '煤种', dataIndex: 'coal_type', width: 90 },
    { title: '类型', dataIndex: 'contract_type', width: 80, render: (v: ContractType) => TYPE_LABEL[v] },
    {
      title: '合同量(吨)', dataIndex: 'contract_quantity', width: 100,
      render: (v: number) => v.toLocaleString(),
    },
    {
      title: '单价(元/吨)', dataIndex: 'unit_price', width: 100,
      render: (v: number) => v.toFixed(2),
    },
    {
      title: '总金额(万元)', dataIndex: 'total_amount', width: 110,
      render: (v: number) => v.toFixed(2),
    },
    {
      title: '执行进度', width: 130,
      render: (_, r) => {
        const pct = Math.min(100, Math.round((r.delivered_quantity || 0) / r.contract_quantity * 100))
        return <Progress percent={pct} size="small" />
      },
    },
    {
      title: '状态', dataIndex: 'status', width: 100,
      render: (v: ContractStatus) => <Tag color={STATUS_LABEL[v].color}>{STATUS_LABEL[v].label}</Tag>,
    },
    {
      title: '操作', width: 70,
      render: (_, r) => <Button type="link" icon={<EyeOutlined />} onClick={() => setDetail(r)} />,
    },
  ]

  return (
    <div>
      <Card>
        <Row gutter={12} style={{ marginBottom: 16 }}>
          <Col>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
              新建合同
            </Button>
          </Col>
          <Col flex="auto">
            <Space wrap>
              <Input
                placeholder="合同号/煤种" style={{ width: 180 }} allowClear
                onChange={(e) => setFilters((f) => ({ ...f, keyword: e.target.value || undefined }))}
                onPressEnter={() => { setPage(1); load(1, pageSize) }}
              />
              <Select
                placeholder="状态" allowClear style={{ width: 120 }}
                options={Object.entries(STATUS_LABEL).map(([v, { label }]) => ({ value: v, label }))}
                onChange={(v) => { const next = { ...filters, status: v }; setFilters(next); setPage(1); load(1, pageSize, next) }}
              />
              <Button icon={<ReloadOutlined />} onClick={() => { setFilters({}); setPage(1); load(1, pageSize, {}) }}>
                重置
              </Button>
            </Space>
          </Col>
        </Row>

        <Table<Contract>
          dataSource={data} columns={columns} rowKey="id" loading={loading}
          scroll={{ x: 1300 }}
          pagination={{
            current: page, pageSize, total, showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); load(p, ps) },
          }}
        />
      </Card>

      {/* 创建 */}
      <Modal title="新建采购合同" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={() => form.submit()} width={760}>
        <Form form={form} layout="vertical" onFinish={handleCreate}
          initialValues={{ contract_type: 'SPOT', pricing_mode: 'DELIVERED' }}>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="supplier_id" label="供应商" rules={[{ required: true }]}>
                <Select
                  showSearch optionFilterProp="label"
                  options={suppliers.map((s) => ({ value: s.id, label: s.name }))}
                />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="contract_type" label="合同类型" rules={[{ required: true }]}>
                <Select options={Object.entries(TYPE_LABEL).map(([v, l]) => ({ value: v, label: l }))} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="pricing_mode" label="计价方式" rules={[{ required: true }]}>
                <Select options={Object.entries(PRICING_LABEL).map(([v, l]) => ({ value: v, label: l }))} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="coal_type" label="煤种" rules={[{ required: true }]}>
                <Input placeholder="如：动力煤" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="coal_origin" label="产地">
                <Input />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="contract_quantity" label="合同总量（吨）" rules={[{ required: true }]}>
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="unit_price" label="合同单价（元/吨）" rules={[{ required: true }]}>
                <InputNumber min={0} precision={2} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="effective_date" label="生效日期" rules={[{ required: true }]}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="expiry_date" label="到期日期" rules={[{ required: true }]}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <div style={{ marginBottom: 8, color: '#666', fontSize: 13 }}>煤质基准（验收依据）：</div>
          <Row gutter={12}>
            <Col span={6}>
              <Form.Item name="spec_calorific_value" label="基准热值 kcal/kg">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="spec_ash_max" label="灰分上限 %">
                <InputNumber min={0} precision={2} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="spec_sulfur_max" label="硫分上限 %">
                <InputNumber min={0} precision={3} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="spec_moisture_max" label="水分上限 %">
                <InputNumber min={0} precision={2} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 详情 */}
      <Modal
        title={detail ? `合同详情 - ${detail.contract_no}` : ''}
        open={!!detail}
        onCancel={() => setDetail(null)}
        width={820}
        footer={detail ? (
          <Space>
            {detail.status === 'DRAFT' && (
              <Button type="primary" onClick={async () => {
                await contractApi.submit(detail.id)
                message.success('已提交审批')
                setDetail(null); load()
              }}>提交审批</Button>
            )}
            {detail.status === 'PENDING_APPROVAL' && (
              <Button type="primary" onClick={() => setApproveOpen(true)}>审批</Button>
            )}
            {detail.status === 'ACTIVE' && (
              <Button danger onClick={async () => {
                Modal.confirm({
                  title: '确认解除合同？',
                  onOk: async () => {
                    await contractApi.terminate(detail.id)
                    message.success('已解除')
                    setDetail(null); load()
                  },
                })
              }}>解除合同</Button>
            )}
            <Button onClick={() => setDetail(null)}>关闭</Button>
          </Space>
        ) : null}
      >
        {detail && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="合同编号">{detail.contract_no}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={STATUS_LABEL[detail.status].color}>{STATUS_LABEL[detail.status].label}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="供应商" span={2}>{detail.supplier_name}</Descriptions.Item>
            <Descriptions.Item label="类型">{TYPE_LABEL[detail.contract_type]}</Descriptions.Item>
            <Descriptions.Item label="计价方式">{PRICING_LABEL[detail.pricing_mode]}</Descriptions.Item>
            <Descriptions.Item label="煤种">{detail.coal_type}</Descriptions.Item>
            <Descriptions.Item label="产地">{detail.coal_origin || '-'}</Descriptions.Item>
            <Descriptions.Item label="合同量">{detail.contract_quantity.toLocaleString()} 吨</Descriptions.Item>
            <Descriptions.Item label="累计交付">{detail.delivered_quantity.toLocaleString()} 吨</Descriptions.Item>
            <Descriptions.Item label="单价">{detail.unit_price} 元/吨</Descriptions.Item>
            <Descriptions.Item label="总金额">{detail.total_amount} 万元</Descriptions.Item>
            <Descriptions.Item label="生效日期">{dayjs(detail.effective_date).format('YYYY-MM-DD')}</Descriptions.Item>
            <Descriptions.Item label="到期日期">{dayjs(detail.expiry_date).format('YYYY-MM-DD')}</Descriptions.Item>
            <Descriptions.Item label="基准热值">{detail.spec_calorific_value || '-'} kcal/kg</Descriptions.Item>
            <Descriptions.Item label="灰分上限">{detail.spec_ash_max != null ? `${detail.spec_ash_max}%` : '-'}</Descriptions.Item>
            <Descriptions.Item label="硫分上限">{detail.spec_sulfur_max != null ? `${detail.spec_sulfur_max}%` : '-'}</Descriptions.Item>
            <Descriptions.Item label="水分上限">{detail.spec_moisture_max != null ? `${detail.spec_moisture_max}%` : '-'}</Descriptions.Item>
            {detail.approved_by && (
              <Descriptions.Item label="审批" span={2}>
                {detail.approved_by} 于 {dayjs(detail.approved_at).format('YYYY-MM-DD HH:mm')}
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>

      {/* 审批 */}
      <Modal title="合同审批" open={approveOpen} onCancel={() => setApproveOpen(false)} onOk={() => approveForm.submit()}>
        <Form form={approveForm} layout="vertical" onFinish={handleApprove} initialValues={{ approved: true }}>
          <Form.Item name="approver" label="审批人" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="approved" label="结果" rules={[{ required: true }]}>
            <Select options={[
              { value: true, label: '通过 - 合同生效' },
              { value: false, label: '退回草稿' },
            ]} />
          </Form.Item>
          <Form.Item name="notes" label="意见">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
