<template>
  <div class="backtest-container">
    <div class="back-section">
      <button class="back-btn" @click="goBack">
        <span class="back-arrow">←</span>
        <span class="back-text">返回首页</span>
      </button>
    </div>

    <div class="header-section">
      <div class="header-glow"></div>
      <div class="header-content">
        <h1>📊 通用回测框架</h1>
        <p class="subtitle">
          {{ backtestData?.strategy?.name || '支持多股票、多周期、多策略的统一回测入口' }}
        </p>
      </div>
    </div>

    <div class="config-card">
      <div class="card-header">
        <h3>⚙️ 回测配置</h3>
      </div>
      <div class="config-grid">
        <div class="config-item stock-selector">
          <label>股票</label>
          <div class="stock-search-wrapper">
            <input
              v-model="stockKeyword"
              type="text"
              class="tech-input"
              placeholder="输入股票代码或名称搜索"
              @input="handleStockSearch"
              @focus="handleStockSearch"
            />
            <div class="stock-dropdown" v-if="stockOptions.length > 0">
              <button
                v-for="stock in stockOptions"
                :key="stock.stock_code"
                class="stock-option"
                @click="selectStock(stock)"
              >
                <span>{{ stock.stock_name }}</span>
                <span>{{ stock.stock_code }}</span>
              </button>
            </div>
          </div>
          <div class="selected-value" v-if="selectedStock">
            已选：{{ selectedStock.stock_name }} / {{ selectedStock.stock_code }}
          </div>
        </div>

        <div class="config-item">
          <label>周期</label>
          <select v-model="selectedPeriod" class="tech-select">
            <option v-for="period in periodOptions" :key="period.id" :value="period.id">
              {{ period.label }}
            </option>
          </select>
        </div>

        <div class="config-item">
          <label>策略</label>
          <select v-model="selectedStrategyId" class="tech-select">
            <option v-for="strategy in strategies" :key="strategy.id" :value="strategy.id">
              {{ strategy.name }}
            </option>
          </select>
        </div>

        <div class="config-item">
          <label>初始资金</label>
          <input v-model.number="initialCapital" type="number" min="10000" step="1000" class="tech-input" />
        </div>
      </div>

      <div class="param-section" v-if="currentStrategy">
        <div class="param-header">策略参数</div>
        <div class="param-grid">
          <div class="config-item" v-for="field in currentStrategy.param_schema" :key="field.key">
            <label>{{ field.label }}</label>
            <input
              v-if="field.type === 'number'"
              v-model.number="strategyParams[field.key]"
              type="number"
              :min="field.min"
              :max="field.max"
              :step="field.step || 1"
              class="tech-input"
            />
            <label v-else-if="field.type === 'boolean'" class="checkbox-label">
              <input v-model="strategyParams[field.key]" type="checkbox" />
              <span>{{ strategyParams[field.key] ? '开启' : '关闭' }}</span>
            </label>
          </div>
        </div>
      </div>

      <div class="action-row">
        <button class="run-btn" @click="runBacktest" :disabled="loading || !selectedStock || !selectedStrategyId">
          {{ loading ? '回测中...' : '开始回测' }}
        </button>
      </div>
    </div>

    <div class="loading-wrapper" v-if="loading">
      <div class="loader">
        <div class="loader-ring"></div>
        <div class="loader-ring"></div>
        <div class="loader-ring"></div>
      </div>
      <p class="loading-text">回测计算中...</p>
    </div>

    <div v-else-if="backtestData">
      <div class="summary-bar">
        <span>标的：{{ backtestData.stock.stock_name }} / {{ backtestData.stock.stock_code }}</span>
        <span>区间：{{ backtestData.start_date }} ~ {{ backtestData.end_date }}</span>
        <span>周期：{{ currentPeriodLabel }}</span>
      </div>

      <div class="metrics-section">
        <div class="metric-card metric-primary">
          <div class="metric-icon">💰</div>
          <div class="metric-content">
            <div class="metric-label">总收益率</div>
            <div class="metric-value" :class="valueClass(backtestData.metrics.return_pct)">
              {{ backtestData.metrics.return_pct.toFixed(2) }}%
            </div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">📈</div>
          <div class="metric-content">
            <div class="metric-label">最终资金</div>
            <div class="metric-value">¥{{ formatNumber(backtestData.metrics.final_capital) }}</div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">🔁</div>
          <div class="metric-content">
            <div class="metric-label">完整交易次数</div>
            <div class="metric-value">{{ backtestData.metrics.total_trades }}</div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">✅</div>
          <div class="metric-content">
            <div class="metric-label">胜率</div>
            <div class="metric-value">{{ backtestData.metrics.win_rate.toFixed(2) }}%</div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">🛒</div>
          <div class="metric-content">
            <div class="metric-label">买入次数</div>
            <div class="metric-value">{{ backtestData.metrics.buy_count }}</div>
          </div>
        </div>
        <div class="metric-card metric-danger">
          <div class="metric-icon">📉</div>
          <div class="metric-content">
            <div class="metric-label">最大回撤</div>
            <div class="metric-value">{{ backtestData.metrics.max_drawdown_pct.toFixed(2) }}%</div>
          </div>
        </div>
      </div>

      <div class="info-card">
        <div class="card-header">
          <h3>📋 策略说明</h3>
        </div>
        <p class="strategy-description" v-if="backtestData.strategy.description">
          {{ backtestData.strategy.description }}
        </p>
        <div class="strategy-info">
          <div class="strategy-point" v-for="(rule, index) in backtestData.strategy.rules || []" :key="index">
            <span class="strategy-label">规则 {{ index + 1 }}：</span>
            <span class="strategy-value">{{ rule }}</span>
          </div>
        </div>
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <h3>📊 K线图 & 策略信号</h3>
        </div>
        <div ref="priceChart" class="chart-container"></div>
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <h3>📈 资金曲线</h3>
        </div>
        <div ref="equityChart" class="chart-container"></div>
      </div>

      <div class="chart-card" v-if="backtestData.trades.length > 0">
        <div class="chart-header">
          <h3>📋 交易记录</h3>
        </div>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>类型</th>
                <th>原因</th>
                <th>价格</th>
                <th>股数</th>
                <th>收益</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(trade, index) in backtestData.trades" :key="index">
                <td class="date-cell">{{ trade.date }}</td>
                <td>
                  <span class="trade-type" :class="{ buy: trade.type === 'BUY', sell: trade.type === 'SELL' }">
                    {{ trade.type === 'BUY' ? '买入' : '卖出' }}
                  </span>
                </td>
                <td>{{ trade.reason || '-' }}</td>
                <td>¥{{ trade.price.toFixed(2) }}</td>
                <td>{{ trade.shares.toLocaleString() }}</td>
                <td v-if="trade.profit !== undefined" :class="valueClass(trade.profit)">
                  ¥{{ formatNumber(trade.profit) }}
                </td>
                <td v-else>-</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <div class="empty-icon">📭</div>
      <p class="empty-text">请选择股票和策略后运行回测</p>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { apiFetch } from '../api'

const router = useRouter()

const loading = ref(false)
const strategies = ref([])
const periodOptions = ref([])
const selectedStrategyId = ref('')
const selectedPeriod = ref('1y')
const initialCapital = ref(100000)
const strategyParams = ref({})
const stockKeyword = ref('招商银行')
const stockOptions = ref([])
const selectedStock = ref({ stock_code: '600036.SH', stock_name: '招商银行' })
const backtestData = ref(null)
const priceChart = ref(null)
const equityChart = ref(null)
let priceChartInstance = null
let equityChartInstance = null

const currentStrategy = computed(() => strategies.value.find(item => item.id === selectedStrategyId.value) || null)
const currentPeriodLabel = computed(() => {
  return periodOptions.value.find(item => item.id === selectedPeriod.value)?.label || selectedPeriod.value
})

function goBack() {
  router.push({ name: 'Home' })
}

function valueClass(value) {
  return value >= 0 ? 'positive' : 'negative'
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function applyStrategyDefaults(strategyId) {
  const strategy = strategies.value.find(item => item.id === strategyId)
  if (!strategy) return
  strategyParams.value = { ...strategy.defaults }
}

async function fetchStrategies() {
  const response = await apiFetch('/backtest/strategies')
  const result = await response.json()
  strategies.value = result.strategies || []
  periodOptions.value = result.period_options || []
  selectedStrategyId.value = result.default_strategy_id || strategies.value[0]?.id || ''
  if (!selectedPeriod.value && periodOptions.value.length > 0) {
    selectedPeriod.value = periodOptions.value[0].id
  }
  applyStrategyDefaults(selectedStrategyId.value)
}

async function handleStockSearch() {
  const keyword = stockKeyword.value.trim()
  if (!keyword) {
    stockOptions.value = []
    return
  }
  const response = await apiFetch(`/stocks?search=${encodeURIComponent(keyword)}`)
  const result = await response.json()
  stockOptions.value = (result || []).slice(0, 8)
}

function selectStock(stock) {
  selectedStock.value = {
    stock_code: stock.stock_code,
    stock_name: stock.stock_name,
  }
  stockKeyword.value = `${stock.stock_name} ${stock.stock_code}`
  stockOptions.value = []
}

async function runBacktest() {
  if (!selectedStock.value || !selectedStrategyId.value) return
  loading.value = true
  try {
    const response = await apiFetch('/backtest/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        stock_code: selectedStock.value.stock_code,
        strategy_id: selectedStrategyId.value,
        period: selectedPeriod.value,
        initial_capital: initialCapital.value,
        strategy_params: strategyParams.value,
      }),
    })
    const result = await response.json()
    if (!response.ok || result.detail) {
      throw new Error(result.detail || '回测失败')
    }
    backtestData.value = result
  } catch (error) {
    console.error('Failed to run backtest:', error)
  } finally {
    loading.value = false
  }
}

function renderPriceChart() {
  if (!priceChart.value || !backtestData.value?.price_data) return
  if (priceChartInstance) {
    priceChartInstance.dispose()
  }
  priceChartInstance = echarts.init(priceChart.value)

  const data = backtestData.value.price_data
  const dates = data.map(item => item.date)
  const klineData = data.map(item => [item.open, item.close, item.low, item.high])
  const overlays = backtestData.value.strategy?.chart_overlays || []
  const buyPoints = []
  const sellPoints = []

  backtestData.value.trades.forEach(trade => {
    const index = dates.findIndex(item => item === trade.date)
    if (index === -1) return
    if (trade.type === 'BUY') {
      buyPoints.push([index, trade.price])
    } else {
      sellPoints.push([index, trade.price])
    }
  })

  const series = [
    {
      name: 'K线',
      type: 'candlestick',
      data: klineData,
      itemStyle: {
        color: '#ff6b6b',
        color0: '#00ff88',
        borderColor: '#ff6b6b',
        borderColor0: '#00ff88',
      },
    },
    ...overlays.map(overlay => ({
      name: overlay.label,
      type: 'line',
      data: data.map(item => item[overlay.key]),
      smooth: true,
      lineStyle: {
        width: 1.5,
        color: overlay.color,
        type: overlay.lineStyle || 'solid',
      },
      showSymbol: false,
    })),
    {
      name: '买入',
      type: 'scatter',
      data: buyPoints,
      symbol: 'triangle',
      symbolSize: 15,
      itemStyle: { color: '#00ff88', borderWidth: 2, borderColor: '#fff' },
    },
    {
      name: '卖出',
      type: 'scatter',
      data: sellPoints,
      symbol: 'triangle',
      symbolRotate: 180,
      symbolSize: 15,
      itemStyle: { color: '#ff6b6b', borderWidth: 2, borderColor: '#fff' },
    },
  ]

  priceChartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(15,23,42,0.95)',
      borderColor: 'rgba(0,212,255,0.3)',
      textStyle: { color: '#fff' },
      borderWidth: 1,
    },
    legend: {
      data: ['K线', ...overlays.map(item => item.label), '买入', '卖出'],
      textStyle: { color: '#98a2b3' },
      top: 10,
    },
    grid: { left: '10%', right: '10%', top: 60, bottom: '10%' },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#667085' },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#667085' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
    },
    dataZoom: [{ type: 'inside', start: 0, end: 100 }],
    series,
  })
}

function renderEquityCurve() {
  if (!equityChart.value || !backtestData.value?.equity_curve) return
  if (equityChartInstance) {
    equityChartInstance.dispose()
  }
  equityChartInstance = echarts.init(equityChart.value)

  const data = backtestData.value.equity_curve
  const dates = data.map(item => item.date)
  const equity = data.map(item => item.equity)

  equityChartInstance.setOption({
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(15,23,42,0.95)',
      borderColor: 'rgba(0,212,255,0.3)',
      textStyle: { color: '#fff' },
      borderWidth: 1,
      formatter: params => {
        const value = params[0].value
        return `${params[0].axisValue}<br/>资金: ¥${formatNumber(value)}`
      },
    },
    legend: { data: ['资金曲线'], textStyle: { color: '#98a2b3' }, top: 10 },
    grid: { left: '10%', right: '10%', top: 60, bottom: '10%' },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#667085' },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#667085' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
    },
    dataZoom: [{ type: 'inside', start: 0, end: 100 }],
    series: [
      {
        name: '资金曲线',
        type: 'line',
        data: equity,
        smooth: true,
        lineStyle: { width: 2, color: '#00d4ff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0,212,255,0.3)' },
            { offset: 1, color: 'rgba(0,212,255,0.05)' },
          ]),
        },
        showSymbol: false,
      },
    ],
  })
}

function renderCharts() {
  renderPriceChart()
  renderEquityCurve()
}

function handleResize() {
  priceChartInstance?.resize()
  equityChartInstance?.resize()
}

watch(selectedStrategyId, value => {
  if (value) {
    applyStrategyDefaults(value)
  }
})

watch(
  () => [loading.value, backtestData.value],
  async ([isLoading, data]) => {
    if (isLoading || !data) return
    await nextTick()
    renderCharts()
  },
  { flush: 'post' },
)

onMounted(async () => {
  await fetchStrategies()
  await runBacktest()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  priceChartInstance?.dispose()
  equityChartInstance?.dispose()
})
</script>

<style scoped>
.backtest-container {
  max-width: 1600px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
}

.back-section {
  margin-bottom: 2rem;
}

.back-btn,
.run-btn,
.stock-option {
  cursor: pointer;
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1.5rem;
  background: rgba(15, 23, 42, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: #98a2b3;
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 1px;
  transition: all 0.3s ease;
}

.back-btn:hover {
  border-color: rgba(0, 212, 255, 0.4);
  color: #00d4ff;
  transform: translateX(-4px);
}

.back-arrow {
  font-size: 1.25rem;
}

.header-section {
  position: relative;
  text-align: center;
  margin-bottom: 2rem;
  padding: 2rem 0;
}

.header-glow {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 300px;
  height: 150px;
  background: radial-gradient(circle, rgba(0, 212, 255, 0.15) 0%, transparent 70%);
  filter: blur(40px);
  pointer-events: none;
}

.header-content {
  position: relative;
  z-index: 1;
}

.header-content h1 {
  font-size: 2.5rem;
  font-weight: 700;
  letter-spacing: 4px;
  background: linear-gradient(90deg, #00d4ff, #00ff88, #00d4ff);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: gradientMove 3s ease infinite;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #667085;
  font-size: 0.875rem;
  letter-spacing: 2px;
}

@keyframes gradientMove {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.config-card,
.info-card,
.chart-card {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(15, 23, 42, 0.7) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.card-header {
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  margin-bottom: 1rem;
}

.card-header h3,
.chart-header h3 {
  margin: 0;
  color: #fff;
  font-size: 1.1rem;
}

.config-grid,
.param-grid,
.metrics-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.config-item label,
.param-header,
.selected-value,
.summary-bar,
.strategy-description,
.strategy-value,
.data-table td {
  color: #98a2b3;
}

.tech-input,
.tech-select {
  width: 100%;
  box-sizing: border-box;
  padding: 0.85rem 1rem;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(2, 6, 23, 0.65);
  color: #fff;
  outline: none;
}

.tech-input:focus,
.tech-select:focus {
  border-color: rgba(0, 212, 255, 0.45);
  box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.12);
}

.stock-search-wrapper {
  position: relative;
}

.stock-dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  left: 0;
  right: 0;
  z-index: 10;
  background: rgba(2, 6, 23, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
}

.stock-option {
  width: 100%;
  display: flex;
  justify-content: space-between;
  padding: 0.85rem 1rem;
  color: #e2e8f0;
  background: transparent;
  border: 0;
}

.stock-option:hover {
  background: rgba(0, 212, 255, 0.08);
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.param-section {
  margin-top: 1.5rem;
}

.action-row {
  margin-top: 1.5rem;
  display: flex;
  justify-content: flex-end;
}

.run-btn {
  padding: 0.9rem 1.6rem;
  border-radius: 10px;
  border: 1px solid rgba(0, 212, 255, 0.35);
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.24) 0%, rgba(0, 255, 136, 0.12) 100%);
  color: #fff;
  font-weight: 600;
}

.run-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.summary-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1rem;
}

.metrics-section {
  margin-bottom: 2rem;
}

.metric-card {
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(15, 23, 42, 0.6) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 1.25rem;
  display: flex;
  gap: 1rem;
  align-items: center;
}

.metric-primary {
  border-color: rgba(0, 212, 255, 0.3);
}

.metric-danger {
  border-color: rgba(255, 107, 107, 0.25);
}

.metric-icon {
  font-size: 2rem;
}

.metric-label {
  color: #667085;
  font-size: 0.75rem;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 0.4rem;
}

.metric-value {
  color: #fff;
  font-size: 1.5rem;
  font-weight: 700;
}

.positive {
  color: #00ff88;
}

.negative {
  color: #ff6b6b;
}

.strategy-info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.strategy-point {
  display: flex;
  gap: 0.5rem;
}

.strategy-label {
  color: #00d4ff;
  font-weight: 600;
}

.chart-header {
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  margin-bottom: 1rem;
}

.chart-container {
  width: 100%;
  height: 460px;
}

.table-container {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.data-table th {
  padding: 1rem;
  text-align: left;
  color: #667085;
  font-size: 0.75rem;
  text-transform: uppercase;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.data-table td {
  padding: 0.875rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.date-cell {
  font-family: 'SF Mono', monospace;
}

.trade-type {
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.trade-type.buy {
  color: #00ff88;
  background: rgba(0, 255, 136, 0.15);
}

.trade-type.sell {
  color: #ff6b6b;
  background: rgba(255, 107, 107, 0.15);
}

.loading-wrapper,
.empty-state {
  text-align: center;
  padding: 4rem;
}

.loader {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto 1.5rem;
}

.loader-ring {
  position: absolute;
  inset: 0;
  border: 3px solid transparent;
  border-top-color: #00d4ff;
  border-radius: 50%;
  animation: spin 1.5s linear infinite;
}

.loader-ring:nth-child(2) {
  inset: 8px;
  border-top-color: #00ff88;
  animation-duration: 1.2s;
  animation-direction: reverse;
}

.loader-ring:nth-child(3) {
  inset: 16px;
  border-top-color: #ff6b6b;
  animation-duration: 0.9s;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text,
.empty-text {
  color: #667085;
}
</style>
