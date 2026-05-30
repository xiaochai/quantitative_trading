<template>
  <div class="backtest-container">
    <!-- 返回按钮 -->
    <div class="back-section">
      <button class="back-btn" @click="goBack">
        <span class="back-arrow">←</span>
        <span class="back-text">返回首页</span>
      </button>
    </div>

    <!-- 头部区域 -->
    <div class="header-section">
      <div class="header-glow"></div>
      <div class="header-content">
        <h1>📊 增强布林带策略回测</h1>
        <p class="subtitle">
          {{ backtestData?.strategy?.name || '招商银行增强布林带分批策略' }}
        </p>
      </div>
    </div>

    <!-- 加载状态 -->
    <div class="loading-wrapper" v-if="loading">
      <div class="loader">
        <div class="loader-ring"></div>
        <div class="loader-ring"></div>
        <div class="loader-ring"></div>
      </div>
      <p class="loading-text">回测计算中...</p>
    </div>

    <div v-else-if="backtestData">
      <!-- 回测指标卡片 -->
      <div class="metrics-section">
        <div class="metric-card metric-primary">
          <div class="metric-icon">💰</div>
          <div class="metric-content">
            <div class="metric-label">总收益率</div>
            <div class="metric-value" :class="{'positive': backtestData.metrics.return_pct >= 0, 'negative': backtestData.metrics.return_pct < 0}">
              {{ backtestData.metrics.return_pct.toFixed(2) }}%
            </div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">📈</div>
          <div class="metric-content">
            <div class="metric-label">最终资金</div>
            <div class="metric-value">
              ¥{{ backtestData.metrics.final_capital.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}
            </div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">🎯</div>
          <div class="metric-content">
            <div class="metric-label">交易次数</div>
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
        <div class="metric-card metric-danger">
          <div class="metric-icon">📉</div>
          <div class="metric-content">
            <div class="metric-label">最大回撤</div>
            <div class="metric-value">{{ backtestData.metrics.max_drawdown_pct.toFixed(2) }}%</div>
          </div>
        </div>
      </div>

      <!-- 策略说明 -->
      <div class="info-card">
        <div class="card-header">
          <h3>📋 策略说明</h3>
        </div>
        <div class="strategy-info">
          <div
            class="strategy-point"
            v-for="(rule, index) in backtestData.strategy?.rules || []"
            :key="index"
          >
            <span class="strategy-label">规则 {{ index + 1 }}：</span>
            <span class="strategy-value">{{ rule }}</span>
          </div>
        </div>
      </div>

      <!-- 布林带K线图 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>📊 布林带K线图 & 买卖点</h3>
        </div>
        <div ref="bollingerChart" class="chart-container" style="width: 100%; height: 450px;"></div>
      </div>

      <!-- 资金曲线图 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>📈 资金曲线</h3>
        </div>
        <div ref="equityChart" class="chart-container" style="width: 100%; height: 450px;"></div>
      </div>

      <!-- 交易记录表格 -->
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
                  <span class="trade-type" :class="{'buy': trade.type === 'BUY', 'sell': trade.type === 'SELL'}">
                    {{ trade.type === 'BUY' ? '买入' : '卖出' }}
                  </span>
                </td>
                <td>{{ trade.reason || '-' }}</td>
                <td>¥{{ trade.price.toFixed(2) }}</td>
                <td>{{ trade.shares.toLocaleString() }}</td>
                <td v-if="trade.profit !== undefined" :class="{'positive': trade.profit >= 0, 'negative': trade.profit < 0}">
                  ¥{{ trade.profit.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}
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
      <p class="empty-text">暂无回测数据</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'

const router = useRouter()

const loading = ref(false)
const backtestData = ref(null)
const bollingerChart = ref(null)
const equityChart = ref(null)
let bollingerChartInstance = null
let equityChartInstance = null

function goBack() {
  router.push({ name: 'Home' })
}

async function loadBacktestData() {
  loading.value = true
  try {
    const response = await fetch('/api/backtest/bollinger?stock_code=600036.SH')
    const result = await response.json()
    
    if (result.error) {
      throw new Error(result.error)
    }
    
    backtestData.value = result
  } catch (error) {
    console.error('Failed to load backtest data:', error)
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  renderBollingerChart()
  renderEquityCurve()
}

function renderBollingerChart() {
  if (!bollingerChart.value) {
    return
  }
  
  if (!backtestData.value || !backtestData.value.bollinger_data) {
    return
  }
  
  if (bollingerChartInstance) {
    bollingerChartInstance.dispose()
  }
  
  bollingerChartInstance = echarts.init(bollingerChart.value)
  
  const data = backtestData.value.bollinger_data
  const dates = data.map(d => d.date)
  const sma = data.map(d => d.sma)
  const upper = data.map(d => d.upper)
  const lower = data.map(d => d.lower)
  const klineData = data.map(d => [d.open, d.close, d.low, d.high])
  
  // 找到买卖点
  const buyPoints = []
  const sellPoints = []
  
  backtestData.value.trades.forEach(trade => {
    const idx = dates.findIndex(d => d === trade.date)
    if (idx !== -1) {
      if (trade.type === 'BUY') {
        buyPoints.push([idx, trade.price])
      } else {
        sellPoints.push([idx, trade.price])
      }
    }
  })
  
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(15,23,42,0.95)',
      borderColor: 'rgba(0,212,255,0.3)',
      textStyle: { color: '#fff' },
      borderWidth: 1
    },
    legend: {
      data: ['K线', '中轨(SMA20)', '上轨', '下轨', '买入', '卖出'],
      textStyle: { color: '#98a2b3' },
      top: 10
    },
    grid: {
      left: '10%',
      right: '10%',
      top: 60,
      bottom: '10%'
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#667085' },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#667085' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 }
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: klineData,
        itemStyle: {
          color: '#ff6b6b',
          color0: '#00ff88',
          borderColor: '#ff6b6b',
          borderColor0: '#00ff88'
        }
      },
      {
        name: '中轨(SMA20)',
        type: 'line',
        data: sma,
        smooth: true,
        lineStyle: { width: 1.5, color: '#ffd93d' },
        showSymbol: false
      },
      {
        name: '上轨',
        type: 'line',
        data: upper,
        smooth: true,
        lineStyle: { width: 1, color: '#ff6b6b', type: 'dashed' },
        showSymbol: false
      },
      {
        name: '下轨',
        type: 'line',
        data: lower,
        smooth: true,
        lineStyle: { width: 1, color: '#00ff88', type: 'dashed' },
        showSymbol: false
      },
      {
        name: '买入',
        type: 'scatter',
        data: buyPoints,
        symbol: 'triangle',
        symbolSize: 15,
        itemStyle: {
          color: '#00ff88',
          borderWidth: 2,
          borderColor: '#fff'
        }
      },
      {
        name: '卖出',
        type: 'scatter',
        data: sellPoints,
        symbol: 'triangle',
        symbolRotate: 180,
        symbolSize: 15,
        itemStyle: {
          color: '#ff6b6b',
          borderWidth: 2,
          borderColor: '#fff'
        }
      }
    ]
  }
  
  bollingerChartInstance.setOption(option)
}

function renderEquityCurve() {
  if (!equityChart.value) {
    return
  }
  
  if (!backtestData.value || !backtestData.value.equity_curve) {
    return
  }
  
  if (equityChartInstance) {
    equityChartInstance.dispose()
  }
  
  equityChartInstance = echarts.init(equityChart.value)
  
  const data = backtestData.value.equity_curve
  const dates = data.map(d => d.date)
  const equity = data.map(d => d.equity)
  
  const option = {
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
        return `${params[0].axisValue}<br/>资金: ¥${value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}`
      }
    },
    legend: {
      data: ['资金曲线'],
      textStyle: { color: '#98a2b3' },
      top: 10
    },
    grid: {
      left: '10%',
      right: '10%',
      top: 60,
      bottom: '10%'
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#667085' },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#667085' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 }
    ],
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
            { offset: 1, color: 'rgba(0,212,255,0.05)' }
          ])
        },
        showSymbol: false
      }
    ]
  }
  
  equityChartInstance.setOption(option)
}

function handleResize() {
  bollingerChartInstance?.resize()
  equityChartInstance?.resize()
}

onMounted(() => {
  loadBacktestData()
  window.addEventListener('resize', handleResize)
})

watch(
  () => [loading.value, backtestData.value],
  async ([isLoading, data]) => {
    if (isLoading || !data) {
      return
    }

    await nextTick()
    renderCharts()
  },
  { flush: 'post' }
)

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  bollingerChartInstance?.dispose()
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

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1.5rem;
  background: rgba(15,23,42,0.8);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  color: #98a2b3;
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-btn:hover {
  border-color: rgba(0,212,255,0.4);
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
  background: radial-gradient(circle, rgba(0,212,255,0.15) 0%, transparent 70%);
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

@keyframes gradientMove {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.subtitle {
  color: #667085;
  font-size: 0.875rem;
  letter-spacing: 3px;
  text-transform: uppercase;
}

.loading-wrapper {
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

.loading-text {
  color: #667085;
  letter-spacing: 4px;
  font-size: 0.875rem;
}

.empty-state {
  text-align: center;
  padding: 4rem;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-text {
  color: #667085;
  font-size: 1.25rem;
  margin-bottom: 0.5rem;
  letter-spacing: 2px;
}

.metrics-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.metric-card {
  position: relative;
  background: linear-gradient(135deg, rgba(15,23,42,0.8) 0%, rgba(15,23,42,0.7) 100%);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: all 0.3s ease;
  overflow: hidden;
}

.metric-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0,212,255,0.3);
}

.metric-primary {
  background: linear-gradient(135deg, rgba(0,212,255,0.2) 0%, rgba(0,255,136,0.1) 100%);
  border-color: rgba(0,212,255,0.3);
}

.metric-danger {
  background: linear-gradient(135deg, rgba(255,107,107,0.2) 0%, rgba(15,23,42,0.1) 100%);
}

.metric-icon {
  font-size: 2.5rem;
  filter: drop-shadow(0 0 10px rgba(0,212,255,0.3));
}

.metric-content {
  flex: 1;
}

.metric-label {
  color: #667085;
  font-size: 0.75rem;
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-bottom: 0.5rem;
}

.metric-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #fff;
}

.metric-value.positive {
  color: #00ff88;
}

.metric-value.negative {
  color: #ff6b6b;
}

.info-card {
  background: linear-gradient(135deg, rgba(15,23,42,0.9) 0%, rgba(15,23,42,0.7) 100%);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  transition: all 0.3s ease;
}

.info-card:hover {
  border-color: rgba(0,212,255,0.3);
}

.card-header {
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  margin-bottom: 1rem;
}

.card-header h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #fff;
  letter-spacing: 1px;
  margin: 0;
}

.strategy-info {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.strategy-point {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.strategy-label {
  color: #00d4ff;
  font-weight: 600;
}

.strategy-value {
  color: #98a2b3;
}

.chart-card {
  position: relative;
  background: linear-gradient(135deg, rgba(15,23,42,0.9) 0%, rgba(15,23,42,0.7) 100%);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  margin-bottom: 2rem;
  overflow: hidden;
  transition: all 0.3s ease;
}

.chart-card:hover {
  border-color: rgba(0,212,255,0.3);
}

.chart-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem 1.5rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  padding-bottom: 1rem;
  margin-bottom: 1rem;
}

.chart-header h3 {
  font-size: 1rem;
  font-weight: 600;
  color: #fff;
  letter-spacing: 1px;
  margin: 0;
}

.chart-container {
  width: 100%;
  height: 450px;
  min-height: 450px;
  padding: 0 1.5rem 1.5rem;
  box-sizing: border-box;
}

.table-container {
  padding: 0 1.5rem 1.5rem;
  max-height: 500px;
  overflow-y: auto;
}

.table-container::-webkit-scrollbar {
  width: 6px;
}

.table-container::-webkit-scrollbar-track {
  background: rgba(255,255,255,0.05);
  border-radius: 3px;
}

.table-container::-webkit-scrollbar-thumb {
  background: rgba(0,212,255,0.3);
  border-radius: 3px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.data-table thead {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(15,23,42,0.95);
}

.data-table th {
  padding: 1rem;
  text-align: left;
  color: #667085;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  white-space: nowrap;
}

.data-table td {
  padding: 0.875rem 1rem;
  color: #98a2b3;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  white-space: nowrap;
}

.data-table tbody tr:hover {
  background: rgba(0,212,255,0.05);
}

.date-cell {
  font-family: 'SF Mono', monospace;
}

.trade-type {
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.75rem;
}

.trade-type.buy {
  background: rgba(0,255,136,0.2);
  color: #00ff88;
  border: 1px solid rgba(0,255,136,0.3);
}

.trade-type.sell {
  background: rgba(255,107,107,0.2);
  color: #ff6b6b;
  border: 1px solid rgba(255,107,107,0.3);
}

.positive {
  color: #00ff88;
  font-weight: 600;
}

.negative {
  color: #ff6b6b;
  font-weight: 600;
}
</style>
