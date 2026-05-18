import { useState, useEffect, useCallback } from 'react'
import {
  Card, Table, Tag, Button, Space, Modal, Form, Input, Select,
  DatePicker, message, Descriptions, Row, Col, InputNumber, Progress,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, ReloadOutlined, EyeOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { orderApi, contractApi } from '../api'
import type { Order, OrderStatus, Contract } from '../types'

const STATUS_LABEL: Record<OrderStatus, { label: string; color: string }> = {
  PLANNED: { label: '计划中', color: 'default' },
  DISPATCHED: { label: '已发运', color: 'processing' },
  PARTIAL_RECEIVED: { label: '部分到货', color: 'warning' },
  RECEIVED: { label: '已到货', color: 'cyan' },
  SETTLED: { label: '已结算', color: 'success' },
  CANCELLED: { label: '已取消', color: 'default' },
}

export default function OrderList() {
  const [data, setData] = useState<Order[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState<{ status?: OrderStatus }>({})
  const [createOpen, setCreateOpen] = useState(false)
  const [detail, setDetail] = useState<Order | null>(null)
  const [receiveOpen, setReceiveOpen] = useState(false)
  const [settleOpen, setSettleOpen] = useState(false)
  const [contracts, setContracts] = useState<Contract[]>([])
  const [form] = Form.useForm()
  const [receiveForm] = Form.useForm()
  const [settleForm] = Form.useForm()

  const load = useCallback(async (p = page, ps = pageSize, f = filters) => {
    setLoading(true)
    try {
      const res = await orderApi.list({ page: p, page_size: ps, ...f })
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
    contractApi.list({ page: 1, page_size: 200, status: 'ACTIVE' }).then((r) => setContracts(r.data.items))
  }, [])

  const handleCreate = async (values: { planned_delivery_date: dayjs.Dayjs } & Partial<Order>) => {
    try {
      const payload = {
        ...values,
        planned_delivery_date: values.planned_delivery_date.toISOString(),
      }
      await orderApi.create(payload as Partial<Order>)
      message.success('订单已创建')
      setCreateOpen(false); form.resetFields(); load()
    } catch (e: unknown) {
      message.error((e as { detail?: string })?.detail || '创建失败')
    }
  }

  const handleReceive = async (values: { delivered_quantity: number; actual_delivery_date?: dayjs.Dayjs }) => {
    if (!detail) return
    try {
      await orderApi.receive(
        detail.id,
        values.delivered_quantity,
        values.actual_delivery_date?.toISOString(),
      )
      message.success('到货已登记')
      setReceiveOpen(false); receiveForm.resetFields(); setDetail(null); load()
    } catch (e: unknown) {
      message.error((e as { detail?: string })?.detail || '操作失败')
    }
  }

  const handleSettle = async (values: { settled_by: string; delivered_amount?: number }) => {
    if (!detail) return
    try {
      await orderApi.settle(detail.id, values.settled_by, values.delivered_amount)
      message.success('已结算')
      setSettleOpen(false); settleForm.resetFields(); setDetail(null); load()
    } catch (e: unknown) {
      message.error((e as { detail?: string })?.detail || '操作失败')
    }
  }

  const columns: ColumnsType<Order> = [
    { title: '订单号', dataIndex: 'order_no', width: 160 },
    { title: '合同号', dataIndex: 'contract_no', width: 150 },
    { title: '供应商', dataIndex: 'supplier_name', ellipsis: true, width: 180 },
    { title: '煤种', dataIndex: 'coal_type', width: 90 },
    {
      title: '计划/实际(吨)', width: 130,
      render: (_, r) => `${r.planned_quantity.toLocaleString()} / ${r.delivered_quantity.toLocaleString()}`,
    },
    {
      title: '到货进度', width: 110,
      render: (_, r) => {
        const pct = Math.min(100, Math.round((r.delivered_quantity || 0) / r.planned_quantity * 100))
        return <Progress percent={pct} size="small" />
      },
    },
    {
      title: '单价', dataIndex: 'unit_price', width: 80,
      render: (v: number) => v.toFixed(2),
    },
    {
      title: '计划到货', dataIndex: 'planned_delivery_date', width: 110,
      render: (v: string) => dayjs(v).format('YYYY-MM-DD'),
    },
    {
      title: '状态', dataIndex: 'status', width: 110,
      render: (v: OrderStatus) => <Tag color={STATUS_LABEL[v].color}>{STATUS_LABEL[v].label}</Tag>,
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
              新建订单
            </Button>
          </Col>
          <Col flex="auto">
            <Space wrap>
              <Select
                placeholder="状态" allowClear style={{ width: 130 }}
                options={Object.entries(STATUS_LABEL).map(([v, { label }]) => ({ value: v, label }))}
                onChange={(v) => { const next = { ...filters, status: v }; setFilters(next); setPage(1); load(1, pageSize, next) }}
              />
              <Button icon={<ReloadOutlined />} onClick={() => { setFilters({}); setPage(1); load(1, pageSize, {}) }}>
                重置
              </Button>
            </Space>
          </Col>
        </Row>

        <Table<Order>
          dataSource={data} columns={columns} rowKey="id" loading={loading}
          scroll={{ x: 1300 }}
          pagination={{
            current: page, pageSize, total, showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); load(p, ps) },
          }}
        />
      </Card>

      <Modal title="新建采购订单" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={() => form.submit()} width={680}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="contract_id" label="关联合同" rules={[{ required: true }]}>
            <Select
              showSearch optionFilterProp="label"
              options={contracts.map((c) => ({
                value: c.id,
                label: `${c.contract_no} - ${c.supplier_name} - ${c.coal_type}（剩余 ${(c.contract_quantity - c.delivered_quantity).toLocaleString()} 吨）`,
              }))}
            />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="planned_quantity" label="计划数量（吨）" rules={[{ required: true }]}>
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="unit_price" label="本次单价（元/吨，留空用合同价）">
                <InputNumber min={0} precision={2} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="planned_delivery_date" label="计划到货日期" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="transport_mode" label="运输方式">
                <Select options={[{ value: '铁路', label: '铁路' }, { value: '汽运', label: '汽运' }, { value: '水运', label: '水运' }]} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="departure_port" label="发货港/矿">
                <Input />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="arrival_plant" label="到厂">
                <Input placeholder="本厂" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={detail ? `订单详情 - ${detail.order_no}` : ''}
        open={!!detail}
        onCancel={() => setDetail(null)}
        width={760}
        footer={detail ? (
          <Space>
            {detail.status === 'PLANNED' && (
              <Button type="primary" onClick={async () => {
                await orderApi.dispatch(detail.id)
                message.success('已发运')
                setDetail(null); load()
              }}>确认发运</Button>
            )}
            {['DISPATCHED', 'PARTIAL_RECEIVED'].includes(detail.status) && (
              <Button type="primary" onClick={() => setReceiveOpen(true)}>登记到货</Button>
            )}
            {detail.status === 'RECEIVED' && (
              <Button type="primary" onClick={() => setSettleOpen(true)}>结算</Button>
            )}
            {['PLANNED', 'DISPATCHED'].includes(detail.status) && (
              <Button danger onClick={async () => {
                Modal.confirm({
                  title: '确认取消？',
                  onOk: async () => {
                    await orderApi.cancel(detail.id)
                    message.success('已取消')
                    setDetail(null); load()
                  },
                })
              }}>取消订单</Button>
            )}
            <Button onClick={() => setDetail(null)}>关闭</Button>
          </Space>
        ) : null}
      >
        {detail && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="订单号">{detail.order_no}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={STATUS_LABEL[detail.status].color}>{STATUS_LABEL[detail.status].label}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="合同号">{detail.contract_no}</Descriptions.Item>
            <Descriptions.Item label="供应商">{detail.supplier_name}</Descriptions.Item>
            <Descriptions.Item label="煤种">{detail.coal_type}</Descriptions.Item>
            <Descriptions.Item label="单价">{detail.unit_price} 元/吨</Descriptions.Item>
            <Descriptions.Item label="计划数量">{detail.planned_quantity.toLocaleString()} 吨</Descriptions.Item>
            <Descriptions.Item label="到货数量">{detail.delivered_quantity.toLocaleString()} 吨</Descriptions.Item>
            <Descriptions.Item label="计划金额">{detail.planned_amount} 万元</Descriptions.Item>
            <Descriptions.Item label="结算金额">{detail.delivered_amount} 万元</Descriptions.Item>
            <Descriptions.Item label="计划到货">{dayjs(detail.planned_delivery_date).format('YYYY-MM-DD')}</Descriptions.Item>
            <Descriptions.Item label="实际到货">
              {detail.actual_delivery_date ? dayjs(detail.actual_delivery_date).format('YYYY-MM-DD') : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="运输">{detail.transport_mode || '-'}</Descriptions.Item>
            <Descriptions.Item label="发→到">{detail.departure_port || '-'} → {detail.arrival_plant || '-'}</Descriptions.Item>
            {detail.settled_by && (
              <Descriptions.Item label="结算" span={2}>
                {detail.settled_by} 于 {dayjs(detail.settled_at).format('YYYY-MM-DD HH:mm')}
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>

      <Modal title="登记到货" open={receiveOpen} onCancel={() => setReceiveOpen(false)} onOk={() => receiveForm.submit()}>
        <Form form={receiveForm} layout="vertical" onFinish={handleReceive}>
          <Form.Item name="delivered_quantity" label="本次到货量（吨）" rules={[{ required: true }]}>
            <InputNumber min={0} style={{ width: '100%' }} placeholder="支持分批到货，多次登记累加" />
          </Form.Item>
          <Form.Item name="actual_delivery_date" label="到货日期（不填则为今日）">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="订单结算" open={settleOpen} onCancel={() => setSettleOpen(false)} onOk={() => settleForm.submit()}>
        <Form form={settleForm} layout="vertical" onFinish={handleSettle}>
          <Form.Item name="settled_by" label="结算人" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="delivered_amount" label="结算金额（万元，留空按单价×到货量自动计算）">
            <InputNumber min={0} precision={2} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
