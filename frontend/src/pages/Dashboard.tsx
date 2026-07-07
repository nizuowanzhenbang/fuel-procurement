import { useEffect, useState, useCallback } from 'react'
import { Row, Col, Card, Statistic, Table, Tag, Progress, Empty, Tooltip } from 'antd'
import {
  TeamOutlined, FileTextOutlined, ShoppingCartOutlined,
  DollarOutlined, RiseOutlined, TrophyOutlined, ClockCircleOutlined,
} from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { dashboardApi } from '../api'
import type {
  OverviewData, MonthlyQuantityItem, SupplierShareItem,
  PriceTrendItem, CoalTypeShareItem,
  SupplierQualityRank, ExpiringContract,
} from '../types'

export default function Dashboard() {
  const [overview, setOverview] = useState<OverviewData | null>(null)
  const [monthly, setMonthly] = useState<MonthlyQuantityItem[]>([])
  const [supplierShare, setSupplierShare] = useState<SupplierShareItem[]>([])
  const [priceTrend, setPriceTrend] = useState<PriceTrendItem[]>([])
  const [coalShare, setCoalShare] = useState<CoalTypeShareItem[]>([])
  const [qualityRank, setQualityRank] = useState<SupplierQualityRank[]>([])
  const [expiring, setExpiring] = useState<ExpiringContract[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const [ov, mq, ss, pt, cs, qr, ec] = await Promise.all([
        dashboardApi.overview(),
        dashboardApi.monthlyQuantity(6),
        dashboardApi.supplierShare(),
        dashboardApi.priceTrend(90),
        dashboardApi.coalTypeShare(),
        dashboardApi.supplierQualityRanking(10),
        dashboardApi.expiringContracts(30),
      ])
      setOverview(ov.data)
      setMonthly(mq.data)
      setSupplierShare(ss.data)
      setPriceTrend(pt.data)
      setCoalShare(cs.data)
      setQualityRank(qr.data)
      setExpiring(ec.data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const t = setInterval(load, 60000)
    return () => clearInterval(t)
  }, [load])

  const monthlyOption: EChartsOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['采购量（吨）', '金额（万元）'], bottom: 0 },
    grid: { left: 60, right: 60, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: monthly.map((m) => m.month) },
    yAxis: [
      { type: 'value', name: '吨', position: 'left' },
      { type: 'value', name: '万元', position: 'right' },
    ],
    series: [
      { name: '采购量（吨）', type: 'bar', data: monthly.map((m) => m.quantity), itemStyle: { color: '#1677ff' } },
      { name: '金额（万元）', type: 'line', yAxisIndex: 1, data: monthly.map((m) => m.amount), itemStyle: { color: '#52c41a' } },
    ],
  }

  const supplierOption: EChartsOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} 吨 ({d}%)' },
    legend: { type: 'scroll', orient: 'vertical', right: 0, top: 20, textStyle: { fontSize: 11 } },
    series: [{
      type: 'pie', radius: ['40%', '70%'], center: ['40%', '50%'],
      data: supplierShare.map((s) => ({ name: s.supplier_name, value: s.quantity })),
      label: { show: false },
    }],
  }

  const priceOption: EChartsOption = {
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: priceTrend.map((p) => p.date.slice(5)) },
    yAxis: { type: 'value', name: '元/吨', scale: true },
    series: [{
      type: 'line', smooth: true, data: priceTrend.map((p) => p.avg_price),
      itemStyle: { color: '#fa8c16' }, areaStyle: { color: 'rgba(250,140,22,0.1)' },
    }],
  }

  const coalOption: EChartsOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} 吨 ({d}%)' },
    legend: { orient: 'horizontal', bottom: 0 },
    series: [{
      type: 'pie', radius: ['40%', '70%'], center: ['50%', '45%'],
      data: coalShare.map((c) => ({ name: c.coal_type, value: c.quantity })),
    }],
  }

  const rankColumns: ColumnsType<SupplierQualityRank> = [
    {
      title: '排名', dataIndex: 'rank', width: 60, align: 'center',
      render: (v: number) => {
        const colors = ['#f59f00', '#adb5bd', '#cd7f32']
        return v <= 3
          ? <Tag color={colors[v - 1]} style={{ fontWeight: 600 }}>NO.{v}</Tag>
          : v
      },
    },
    { title: '供应商', dataIndex: 'supplier_name', ellipsis: true },
    {
      title: '质量评分', dataIndex: 'score', width: 130,
      render: (v: number) => (
        <Progress
          percent={v} size="small"
          strokeColor={v >= 90 ? '#52c41a' : v >= 80 ? '#1677ff' : '#faad14'}
          format={(p) => `${p?.toFixed?.(1) ?? p}`}
        />
      ),
    },
    {
      title: '合格率', dataIndex: 'pass_rate', width: 80,
      render: (v: number | null) => v != null ? `${v}%` : '-',
    },
    { title: '样本', dataIndex: 'sample_count', width: 60 },
    {
      title: '评估时间', dataIndex: 'evaluated_at', width: 100,
      render: (v: string) => dayjs(v).format('MM-DD'),
    },
  ]

  const expiringColumns: ColumnsType<ExpiringContract> = [
    { title: '合同号', dataIndex: 'contract_no', width: 150 },
    { title: '供应商', dataIndex: 'supplier_name', ellipsis: true },
    { title: '煤种', dataIndex: 'coal_type', width: 80 },
    {
      title: '到期', dataIndex: 'expiry_date', width: 100,
      render: (v: string) => dayjs(v).format('YYYY-MM-DD'),
    },
    {
      title: '剩余', dataIndex: 'days_left', width: 80, align: 'center',
      render: (v: number) => (
        <Tag color={v <= 7 ? 'red' : v <= 15 ? 'orange' : 'gold'}>{v} 天</Tag>
      ),
    },
    {
      title: '履约进度', dataIndex: 'completion_rate', width: 130,
      render: (v: number) => <Progress percent={v} size="small" />,
    },
    {
      title: '剩余量', dataIndex: 'remaining_quantity', width: 90,
      render: (v: number) => `${v.toLocaleString()} 吨`,
    },
  ]

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="合作供应商"
              value={overview?.active_suppliers ?? 0}
              prefix={<TeamOutlined style={{ color: '#1677ff' }} />}
              suffix={
                (overview?.pending_review ?? 0) > 0
                  ? <span style={{ fontSize: 13, color: '#faad14' }}>待审 {overview?.pending_review}</span>
                  : null
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="生效合同"
              value={overview?.active_contracts ?? 0}
              prefix={<FileTextOutlined style={{ color: '#722ed1' }} />}
              suffix={
                (overview?.pending_approval ?? 0) > 0
                  ? <span style={{ fontSize: 13, color: '#faad14' }}>待批 {overview?.pending_approval}</span>
                  : null
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="在途订单"
              value={overview?.in_transit_orders ?? 0}
              prefix={<ShoppingCartOutlined style={{ color: '#fa8c16' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="本月结算（万元）"
              value={overview?.month_settled_amount ?? 0}
              precision={2}
              prefix={<DollarOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} lg={14}>
          <Card title="近6月采购量与金额" loading={loading}>
            <ReactECharts option={monthlyOption} style={{ height: 280 }} notMerge />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="供应商占比（近90天）" loading={loading}>
            <ReactECharts option={supplierOption} style={{ height: 280 }} notMerge />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={24} lg={14}>
          <Card
            title="单价趋势（近90天）"
            loading={loading}
            extra={
              overview?.avg_unit_price ? (
                <span style={{ fontSize: 13, color: '#666' }}>
                  本月均价 <b style={{ color: '#fa8c16' }}>{overview.avg_unit_price}</b> 元/吨
                  <RiseOutlined style={{ color: '#fa8c16', marginLeft: 4 }} />
                </span>
              ) : null
            }
          >
            <ReactECharts option={priceOption} style={{ height: 280 }} notMerge />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="煤种采购占比" loading={loading}>
            <ReactECharts option={coalOption} style={{ height: 280 }} notMerge />
          </Card>
        </Col>
      </Row>

      {/* v2: 集成与预警 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card
            title={
              <span>
                <TrophyOutlined style={{ color: '#fa8c16', marginRight: 8 }} />
                供应商质量综合评分排名
                <Tooltip title="数据来源：煤质化验系统（coal-quality-monitor）webhook 推送">
                  <Tag color="purple" style={{ marginLeft: 8, fontWeight: 'normal' }}>集成</Tag>
                </Tooltip>
              </span>
            }
            loading={loading}
          >
            {qualityRank.length > 0 ? (
              <Table<SupplierQualityRank>
                dataSource={qualityRank} columns={rankColumns} rowKey="rank"
                pagination={false} size="small"
              />
            ) : (
              <Empty description="尚未接收质量评分（等待煤质系统推送）" />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card
            title={
              <span>
                <ClockCircleOutlined style={{ color: '#fa541c', marginRight: 8 }} />
                长协合同到期提醒（30天内）
                <Tag color={expiring.length > 0 ? 'red' : 'green'} style={{ marginLeft: 8 }}>
                  {expiring.length} 份
                </Tag>
              </span>
            }
            loading={loading}
          >
            {expiring.length > 0 ? (
              <Table<ExpiringContract>
                dataSource={expiring} columns={expiringColumns} rowKey="id"
                pagination={false} size="small"
                scroll={{ x: 700 }}
              />
            ) : (
              <Empty description="30 天内无长协合同到期" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
