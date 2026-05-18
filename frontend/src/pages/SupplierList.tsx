import { useState, useEffect, useCallback } from 'react'
import {
  Card, Table, Tag, Button, Space, Modal, Form, Input, Select,
  message, Descriptions, Row, Col, InputNumber, Progress,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, ReloadOutlined, EyeOutlined } from '@ant-design/icons'
import { supplierApi } from '../api'
import type { Supplier, SupplierStatus, SupplierTier } from '../types'

const STATUS_LABEL: Record<SupplierStatus, { label: string; color: string }> = {
  PENDING_REVIEW: { label: '待审核', color: 'warning' },
  ACTIVE: { label: '合作中', color: 'success' },
  SUSPENDED: { label: '已暂停', color: 'default' },
  BLACKLISTED: { label: '黑名单', color: 'error' },
  ARCHIVED: { label: '已归档', color: 'default' },
}

const TIER_LABEL: Record<SupplierTier, { label: string; color: string }> = {
  STRATEGIC: { label: '战略合作', color: 'gold' },
  PREFERRED: { label: '优先采购', color: 'blue' },
  QUALIFIED: { label: '合格', color: 'green' },
  PROBATION: { label: '试用期', color: 'default' },
}

export default function SupplierList() {
  const [data, setData] = useState<Supplier[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState<{ status?: SupplierStatus; tier?: SupplierTier; keyword?: string }>({})
  const [createOpen, setCreateOpen] = useState(false)
  const [detail, setDetail] = useState<Supplier | null>(null)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [form] = Form.useForm()
  const [reviewForm] = Form.useForm()

  const load = useCallback(async (p = page, ps = pageSize, f = filters) => {
    setLoading(true)
    try {
      const res = await supplierApi.list({ page: p, page_size: ps, ...f })
      setData(res.data.items)
      setTotal(res.data.total)
    } catch {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, filters])

  useEffect(() => { load(1, 20, {}) }, [])

  const handleCreate = async (values: Partial<Supplier>) => {
    try {
      await supplierApi.create(values)
      message.success('已登记，等待审核')
      setCreateOpen(false)
      form.resetFields()
      load()
    } catch (e: unknown) {
      message.error((e as { detail?: string })?.detail || '创建失败')
    }
  }

  const handleReview = async (values: { approved: boolean; review_notes: string; tier: SupplierTier }) => {
    if (!detail) return
    try {
      await supplierApi.review(detail.id, values.approved, values.review_notes, values.tier)
      message.success(values.approved ? '审核通过' : '审核未通过')
      setReviewOpen(false)
      reviewForm.resetFields()
      setDetail(null)
      load()
    } catch (e: unknown) {
      message.error((e as { detail?: string })?.detail || '操作失败')
    }
  }

  const columns: ColumnsType<Supplier> = [
    { title: '编码', dataIndex: 'code', width: 100 },
    { title: '供应商名称', dataIndex: 'name', ellipsis: true },
    { title: '产地', dataIndex: 'coal_origin', width: 130 },
    { title: '煤种', dataIndex: 'coal_types', width: 130, ellipsis: true },
    {
      title: '等级', dataIndex: 'tier', width: 100,
      render: (v: SupplierTier) => <Tag color={TIER_LABEL[v].color}>{TIER_LABEL[v].label}</Tag>,
    },
    {
      title: '信用分', dataIndex: 'credit_score', width: 130,
      render: (v: number) => (
        <Progress
          percent={v} size="small"
          strokeColor={v >= 80 ? '#52c41a' : v >= 60 ? '#faad14' : '#ff4d4f'}
          format={(p) => `${p}`}
        />
      ),
    },
    {
      title: '状态', dataIndex: 'status', width: 100,
      render: (v: SupplierStatus) => <Tag color={STATUS_LABEL[v].color}>{STATUS_LABEL[v].label}</Tag>,
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
              登记供应商
            </Button>
          </Col>
          <Col flex="auto">
            <Space wrap>
              <Input
                placeholder="名称/编码关键字" style={{ width: 200 }} allowClear
                onChange={(e) => setFilters((f) => ({ ...f, keyword: e.target.value || undefined }))}
                onPressEnter={() => { setPage(1); load(1, pageSize) }}
              />
              <Select
                placeholder="状态" allowClear style={{ width: 110 }}
                options={Object.entries(STATUS_LABEL).map(([v, { label }]) => ({ value: v, label }))}
                onChange={(v) => { const next = { ...filters, status: v }; setFilters(next); setPage(1); load(1, pageSize, next) }}
              />
              <Select
                placeholder="等级" allowClear style={{ width: 110 }}
                options={Object.entries(TIER_LABEL).map(([v, { label }]) => ({ value: v, label }))}
                onChange={(v) => { const next = { ...filters, tier: v }; setFilters(next); setPage(1); load(1, pageSize, next) }}
              />
              <Button icon={<ReloadOutlined />} onClick={() => { setFilters({}); setPage(1); load(1, pageSize, {}) }}>
                重置
              </Button>
            </Space>
          </Col>
        </Row>

        <Table<Supplier>
          dataSource={data} columns={columns} rowKey="id" loading={loading}
          scroll={{ x: 1100 }}
          pagination={{
            current: page, pageSize, total, showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); load(p, ps) },
          }}
        />
      </Card>

      <Modal title="登记新供应商" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={() => form.submit()} width={760}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="name" label="供应商名称" rules={[{ required: true }]}>
                <Input placeholder="如：神华神东煤炭集团" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="short_name" label="简称">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="legal_representative" label="法定代表人">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="business_license" label="营业执照号">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="contact_person" label="联系人">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="contact_phone" label="联系电话">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="address" label="地址">
            <Input />
          </Form.Item>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="coal_origin" label="产地">
                <Input placeholder="陕西神木" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="coal_types" label="可供煤种">
                <Input placeholder="动力煤,长焰煤" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="annual_capacity" label="年供应能力（吨）">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="registered_capital" label="注册资本（万元）">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="transport_modes" label="运输方式">
                <Input placeholder="铁路,汽运" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={detail ? `供应商详情 - ${detail.code}` : ''}
        open={!!detail}
        onCancel={() => setDetail(null)}
        width={760}
        footer={detail ? (
          <Space>
            {detail.status === 'PENDING_REVIEW' && (
              <Button type="primary" onClick={() => setReviewOpen(true)}>准入审核</Button>
            )}
            {detail.status === 'ACTIVE' && (
              <Button danger onClick={async () => {
                await supplierApi.suspend(detail.id)
                message.success('已暂停')
                setDetail(null); load()
              }}>暂停合作</Button>
            )}
            {detail.status === 'SUSPENDED' && (
              <Button type="primary" onClick={async () => {
                await supplierApi.resume(detail.id)
                message.success('已恢复')
                setDetail(null); load()
              }}>恢复合作</Button>
            )}
            <Button onClick={() => setDetail(null)}>关闭</Button>
          </Space>
        ) : null}
      >
        {detail && (
          <Descriptions column={2} bordered size="small">
            <Descriptions.Item label="编码">{detail.code}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={STATUS_LABEL[detail.status].color}>{STATUS_LABEL[detail.status].label}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="名称" span={2}>{detail.name}</Descriptions.Item>
            <Descriptions.Item label="法定代表人">{detail.legal_representative || '-'}</Descriptions.Item>
            <Descriptions.Item label="营业执照">{detail.business_license || '-'}</Descriptions.Item>
            <Descriptions.Item label="联系人">{detail.contact_person || '-'}</Descriptions.Item>
            <Descriptions.Item label="联系电话">{detail.contact_phone || '-'}</Descriptions.Item>
            <Descriptions.Item label="地址" span={2}>{detail.address || '-'}</Descriptions.Item>
            <Descriptions.Item label="产地">{detail.coal_origin || '-'}</Descriptions.Item>
            <Descriptions.Item label="煤种">{detail.coal_types || '-'}</Descriptions.Item>
            <Descriptions.Item label="年供能力">{detail.annual_capacity ? `${detail.annual_capacity} 吨` : '-'}</Descriptions.Item>
            <Descriptions.Item label="注册资本">{detail.registered_capital ? `${detail.registered_capital} 万元` : '-'}</Descriptions.Item>
            <Descriptions.Item label="等级">
              <Tag color={TIER_LABEL[detail.tier].color}>{TIER_LABEL[detail.tier].label}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="信用分">{detail.credit_score}</Descriptions.Item>
            {detail.review_notes && (
              <Descriptions.Item label="审核意见" span={2}>
                {detail.reviewed_by}: {detail.review_notes}
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>

      <Modal title="准入审核" open={reviewOpen} onCancel={() => setReviewOpen(false)} onOk={() => reviewForm.submit()}>
        <Form form={reviewForm} layout="vertical" onFinish={handleReview} initialValues={{ approved: true, tier: 'PROBATION' }}>
          <Form.Item name="approved" label="审核结果" rules={[{ required: true }]}>
            <Select options={[
              { value: true, label: '通过 - 准入合作' },
              { value: false, label: '未通过 - 归档' },
            ]} />
          </Form.Item>
          <Form.Item name="tier" label="供应商等级">
            <Select options={Object.entries(TIER_LABEL).map(([v, { label }]) => ({ value: v, label }))} />
          </Form.Item>
          <Form.Item name="review_notes" label="审核意见" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
