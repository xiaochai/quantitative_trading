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
        <h1>📊 组合轮动策略</h1>
        <p class="subtitle">收盘后选股，下一交易日开盘前生成执行计划</p>
      </div>
    </div>

    <div class="config-card">
      <div class="card-header">
        <h3>⚙️ 回测配置</h3>
      </div>
      <div class="config-grid">
        <div class="config-item">
          <label>股票池</label>
          <select v-model="selectedUniverseId" class="tech-select">
            <option v-for="item in universeOptions" :key="item.id" :value="item.id">{{ item.label }}</option>
          </select>
        </div>
        <div class="config-item">
          <label>策略</label>
          <select v-model="selectedStrategyId" class="tech-select">
            <option v-for="item in strategies" :key="item.id" :value="item.id">{{ item.name }}</option>
          </select>
        </div>
        <div class="config-item">
          <label>回测周期</label>
          <select v-model="selectedPeriod" class="tech-select">
            <option v-for="item in periodOptions" :key="item.id" :value="item.id">{{ item.label }}</option>
          </select>
        </div>
        <div class="config-item">
          <label>开始日期</label>
          <input v-model="startDate" type="date" class="tech-input" />
        </div>
        <div class="config-item">
          <label>结束日期</label>
          <input v-model="endDate" type="date" class="tech-input" />
        </div>
        <div class="config-item">
          <label>初始资金</label>
          <input v-model.number="initialCapital" type="number" min="10000" step="1000" class="tech-input" />
        </div>
        <div class="config-item">
          <label>最大持仓数</label>
          <input v-model.number="maxPositions" type="number" min="1" max="10" step="1" class="tech-input" />
        </div>
        <div class="config-item">
          <label>现金保留比例</label>
          <input v-model.number="cashReserveRatio" type="number" min="0" max="0.5" step="0.01" class="tech-input" />
        </div>
      </div>

      <div class="param-section" v-if="currentStrategy">
        <div class="param-header">策略参数</div>
        <div class="param-grid">
          <div class="config-item" v-for="field in currentStrategy.param_schema" :key="field.key">
            <label>{{ field.label }}</label>
            <input
              v-if="field.type === 'boolean'"
              v-model="strategyParams[field.key]"
              type="checkbox"
              :true-value="true"
              :false-value="false"
            />
            <input
              v-else
              v-model.number="strategyParams[field.key]"
              type="number"
              :min="field.min"
              :max="field.max"
              :step="field.step || 1"
              class="tech-input"
            />
          </div>
        </div>
      </div>

      <div class="action-row">
        <button class="run-btn" @click="runBacktest" :disabled="loading">{{ loading ? '回测中...' : '开始组合回测' }}</button>
      </div>
    </div>

    <div class="loading-wrapper" v-if="loading">
      <div class="loader">
        <div class="loader-ring"></div>
        <div class="loader-ring"></div>
        <div class="loader-ring"></div>
      </div>
      <p class="loading-text">组合回测计算中...</p>
    </div>

    <div v-else-if="portfolioData">
      <div class="summary-bar">
        <span>股票池：{{ portfolioData.universe.label }}</span>
        <span>策略：{{ portfolioData.strategy.name }}</span>
        <span>区间：{{ portfolioData.start_date }} ~ {{ portfolioData.end_date }}</span>
      </div>

      <div class="metrics-section">
        <div class="metric-card metric-primary">
          <div class="metric-icon">💰</div>
          <div class="metric-content">
            <div class="metric-label">总收益率</div>
            <div class="metric-value" :class="valueClass(portfolioData.metrics.return_pct)">{{ portfolioData.metrics.return_pct.toFixed(2) }}%</div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">📈</div>
          <div class="metric-content">
            <div class="metric-label">年化收益</div>
            <div class="metric-value" :class="valueClass(portfolioData.metrics.annualized_return_pct)">{{ portfolioData.metrics.annualized_return_pct.toFixed(2) }}%</div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">🏦</div>
          <div class="metric-content">
            <div class="metric-label">最终资金</div>
            <div class="metric-value">¥{{ formatNumber(portfolioData.metrics.final_capital) }}</div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">📉</div>
          <div class="metric-content">
            <div class="metric-label">最大回撤</div>
            <div class="metric-value">{{ portfolioData.metrics.max_drawdown_pct.toFixed(2) }}%</div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">🔁</div>
          <div class="metric-content">
            <div class="metric-label">调仓日数量</div>
            <div class="metric-value">{{ portfolioData.metrics.rebalance_count }}</div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-icon">✅</div>
          <div class="metric-content">
            <div class="metric-label">胜率</div>
            <div class="metric-value">{{ portfolioData.metrics.win_rate.toFixed(2) }}%</div>
          </div>
        </div>
      </div>

      <div class="info-card">
        <div class="card-header">
          <h3>📋 策略分析</h3>
        </div>
        <div class="strategy-info">
          <div class="strategy-point" v-for="(line, index) in portfolioData.analysis || []" :key="index">
            <span class="strategy-label">分析 {{ index + 1 }}：</span>
            <span class="strategy-value">{{ line }}</span>
          </div>
        </div>
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <h3>📈 资金曲线与调仓节点</h3>
        </div>
        <div ref="equityChartRef" class="chart-container"></div>
      </div>

      <div class="two-column-grid">
        <div class="info-card">
          <div class="card-header">
            <h3>🏆 最新候选排名</h3>
          </div>
          <div class="table-container slim-table">
            <table class="data-table">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>股票</th>
                  <th>得分</th>
                  <th>原因</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in portfolioData.latest_candidates" :key="item.stock_code">
                  <td>{{ item.rank }}</td>
                  <td>{{ item.stock_name }} / {{ item.stock_code }}</td>
                  <td>{{ item.score.toFixed(2) }}</td>
                  <td>{{ item.reason }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="info-card">
          <div class="card-header">
            <h3>📦 回测结束持仓</h3>
          </div>
          <div class="table-container slim-table">
            <table class="data-table">
              <thead>
                <tr>
                  <th>股票</th>
                  <th>股数</th>
                  <th>成本</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in portfolioData.final_holdings" :key="item.stock_code">
                  <td>{{ item.stock_name }} / {{ item.stock_code }}</td>
                  <td>{{ item.shares.toLocaleString() }}</td>
                  <td>¥{{ item.cost_price.toFixed(2) }}</td>
                </tr>
                <tr v-if="!portfolioData.final_holdings.length">
                  <td colspan="3">回测结束无持仓</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <h3>🔄 调仓节点</h3>
        </div>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>信号日</th>
                <th>执行日</th>
                <th>买入</th>
                <th>卖出</th>
                <th>目标组合</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in portfolioData.rebalance_events" :key="`${item.signal_date}-${index}`">
                <td>{{ item.signal_date }}</td>
                <td>{{ item.execute_date }}</td>
                <td>{{ item.buy_stocks.join('、') || '-' }}</td>
                <td>{{ item.sell_stocks.join('、') || '-' }}</td>
                <td>{{ item.top_candidates.join('、') || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <h3>🧾 交易明细</h3>
        </div>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>动作</th>
                <th>信号日</th>
                <th>执行日</th>
                <th>股票</th>
                <th>股数</th>
                <th>价格</th>
                <th>金额</th>
                <th>收益</th>
                <th>原因</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in portfolioData.trade_records" :key="`${item.stock_code}-${item.execute_date}-${index}`">
                <td>
                  <span class="trade-type" :class="{ buy: item.action === 'BUY', sell: item.action === 'SELL' }">{{ item.action }}</span>
                </td>
                <td>{{ item.signal_date }}</td>
                <td>{{ item.execute_date }}</td>
                <td>{{ item.stock_name }} / {{ item.stock_code }}</td>
                <td>{{ item.shares.toLocaleString() }}</td>
                <td>¥{{ item.price.toFixed(2) }}</td>
                <td>¥{{ formatNumber(item.amount) }}</td>
                <td>
                  <span v-if="item.profit !== undefined" :class="valueClass(item.profit)">¥{{ formatNumber(item.profit) }}</span>
                  <span v-else>-</span>
                </td>
                <td>{{ item.reason }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="config-card plan-card">
      <div class="card-header">
        <h3>🗓️ 下一个交易日计划</h3>
      </div>
      <div class="config-grid">
        <div class="config-item">
          <label>当前可用现金</label>
          <input v-model.number="currentCash" type="number" min="0" step="1000" class="tech-input" />
        </div>
      </div>

      <div class="holdings-section">
        <div class="section-row">
          <div class="param-header">当前持仓</div>
          <button class="small-btn" @click="addHolding">新增持仓</button>
        </div>
        <div class="holding-row" v-for="(item, index) in holdings" :key="index">
          <input v-model="item.stock_code" type="text" placeholder="股票代码，如 600036.SH" class="tech-input" />
          <input v-model.number="item.shares" type="number" min="0" step="100" placeholder="股数" class="tech-input" />
          <input v-model.number="item.cost_price" type="number" min="0" step="0.01" placeholder="成本价" class="tech-input" />
          <button class="small-btn danger-btn" @click="removeHolding(index)">删除</button>
        </div>
      </div>

      <div class="action-row">
        <button class="run-btn" @click="generatePlan" :disabled="planning">{{ planning ? '生成中...' : '生成明日计划' }}</button>
      </div>
    </div>

    <div v-if="planData" class="plan-result-grid">
      <div class="info-card">
        <div class="card-header">
          <h3>📌 计划摘要</h3>
        </div>
        <div class="strategy-info">
          <div class="strategy-point"><span class="strategy-label">信号日：</span><span class="strategy-value">{{ planData.signal_date }}</span></div>
          <div class="strategy-point"><span class="strategy-label">计划执行日：</span><span class="strategy-value">{{ planData.plan_date }}</span></div>
          <div class="strategy-point"><span class="strategy-label">目标组合：</span><span class="strategy-value">{{ planData.target_codes.join('、') || '-' }}</span></div>
          <div class="strategy-point" v-for="(line, index) in planData.analysis || []" :key="index">
            <span class="strategy-label">说明 {{ index + 1 }}：</span>
            <span class="strategy-value">{{ line }}</span>
          </div>
        </div>
      </div>

      <div class="info-card">
        <div class="card-header">
          <h3>🛡️ 保留持仓</h3>
        </div>
        <div class="table-container slim-table">
          <table class="data-table">
            <thead>
              <tr>
                <th>股票</th>
                <th>股数</th>
                <th>得分</th>
                <th>原因</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in planData.keep_positions" :key="item.stock_code">
                <td>{{ item.stock_name }} / {{ item.stock_code }}</td>
                <td>{{ item.shares.toLocaleString() }}</td>
                <td>{{ item.score ?? '-' }}</td>
                <td>{{ item.reason }}</td>
              </tr>
              <tr v-if="!planData.keep_positions.length">
                <td colspan="4">无继续持有的仓位</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="chart-card full-span">
        <div class="chart-header">
          <h3>📨 明日委托建议</h3>
        </div>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>动作</th>
                <th>股票</th>
                <th>股数</th>
                <th>参考价格</th>
                <th>参考金额</th>
                <th>原因</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in planData.next_day_actions" :key="`${item.stock_code}-${item.action}-${index}`">
                <td><span class="trade-type" :class="{ buy: item.action === 'BUY', sell: item.action === 'SELL' }">{{ item.action }}</span></td>
                <td>{{ item.stock_name }} / {{ item.stock_code }}</td>
                <td>{{ item.shares.toLocaleString() }}</td>
                <td>¥{{ item.reference_price.toFixed(2) }}</td>
                <td>¥{{ formatNumber(item.reference_amount) }}</td>
                <td>{{ item.reason }}</td>
              </tr>
              <tr v-if="!planData.next_day_actions.length">
                <td colspan="6">当前持仓与目标组合一致，暂无需要委托的动作</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="chart-card full-span" v-if="planData.risk_orders && planData.risk_orders.length">
        <div class="chart-header">
          <h3>🧯 盘中风控单（止损）</h3>
        </div>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>动作</th>
                <th>股票</th>
                <th>股数</th>
                <th>止损触发价</th>
                <th>限价</th>
                <th>原因</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in planData.risk_orders" :key="`${item.stock_code}-${item.action}-${index}`">
                <td><span class="trade-type sell">{{ item.action }}</span></td>
                <td>{{ item.stock_name }} / {{ item.stock_code }}</td>
                <td>{{ item.shares.toLocaleString() }}</td>
                <td>¥{{ item.stop_price.toFixed(2) }}</td>
                <td>¥{{ item.limit_price.toFixed(2) }}</td>
                <td>{{ item.reason }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { apiFetch } from '../api'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const planning = ref(false)
const portfolioData = ref(null)
const planData = ref(null)
const strategies = ref([])
const periodOptions = ref([])
const universeOptions = ref([])
const selectedStrategyId = ref('')
const selectedUniverseId = ref('hs300')
const selectedPeriod = ref('2y')
const startDate = ref('')
const endDate = ref('')
const initialCapital = ref(100000)
const maxPositions = ref(3)
const cashReserveRatio = ref(0.1)
const strategyParams = ref({})
const currentCash = ref(100000)
const holdings = ref([])
const equityChartRef = ref(null)
let equityChartInstance = null

const currentStrategy = computed(() => strategies.value.find(item => item.id === selectedStrategyId.value) || null)

function goBack() {
  router.push({ name: 'Home' })
}

function encodeParams(value) {
  return encodeURIComponent(JSON.stringify(value ?? {}))
}

function decodeParams(value) {
  if (!value || typeof value !== 'string') return null
  try {
    return JSON.parse(decodeURIComponent(value))
  } catch (error) {
    return null
  }
}

function setQueryFromState() {
  const query = {
    universe: selectedUniverseId.value,
    strategy: selectedStrategyId.value,
    period: selectedPeriod.value,
    start: startDate.value || undefined,
    end: endDate.value || undefined,
    capital: String(initialCapital.value),
    positions: String(maxPositions.value),
    cash: String(cashReserveRatio.value),
    params: encodeParams(strategyParams.value),
  }
  Object.keys(query).forEach(key => {
    if (query[key] === undefined || query[key] === null || query[key] === '') {
      delete query[key]
    }
  })
  router.replace({ name: 'PortfolioBacktest', query })
}

function applyStateFromQuery() {
  const q = route.query || {}
  if (typeof q.universe === 'string') selectedUniverseId.value = q.universe
  if (typeof q.strategy === 'string') selectedStrategyId.value = q.strategy
  if (typeof q.period === 'string') selectedPeriod.value = q.period
  if (typeof q.start === 'string') startDate.value = q.start
  if (typeof q.end === 'string') endDate.value = q.end
  if (typeof q.capital === 'string' && !Number.isNaN(Number(q.capital))) initialCapital.value = Number(q.capital)
  if (typeof q.positions === 'string' && !Number.isNaN(Number(q.positions))) maxPositions.value = Number(q.positions)
  if (typeof q.cash === 'string' && !Number.isNaN(Number(q.cash))) cashReserveRatio.value = Number(q.cash)

  const decoded = typeof q.params === 'string' ? decodeParams(q.params) : null
  if (decoded && typeof decoded === 'object') {
    strategyParams.value = { ...strategyParams.value, ...decoded }
  }
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function valueClass(value) {
  return value >= 0 ? 'positive' : 'negative'
}

function applyStrategyDefaults(strategyId) {
  const strategy = strategies.value.find(item => item.id === strategyId)
  if (!strategy) return
  strategyParams.value = { ...strategy.defaults }
}

function addHolding() {
  holdings.value.push({ stock_code: '', shares: 0, cost_price: 0 })
}

function removeHolding(index) {
  holdings.value.splice(index, 1)
}

async function fetchCatalog() {
  const response = await apiFetch('/portfolio/strategies')
  const result = await response.json()
  strategies.value = result.strategies || []
  periodOptions.value = result.period_options || []
  universeOptions.value = result.universe_options || []
  selectedStrategyId.value = result.default_strategy_id || strategies.value[0]?.id || ''
  selectedUniverseId.value = result.default_universe_id || universeOptions.value[0]?.id || 'hs300'
  applyStrategyDefaults(selectedStrategyId.value)
}

async function runBacktest() {
  loading.value = true
  try {
    setQueryFromState()
    const response = await apiFetch('/portfolio/backtest/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        universe_id: selectedUniverseId.value,
        strategy_id: selectedStrategyId.value,
        period: selectedPeriod.value,
        start_date: startDate.value || null,
        end_date: endDate.value || null,
        initial_capital: initialCapital.value,
        max_positions: maxPositions.value,
        cash_reserve_ratio: cashReserveRatio.value,
        strategy_params: strategyParams.value,
      }),
    })
    const result = await response.json()
    if (!response.ok || result.detail) {
      throw new Error(result.detail || '组合回测失败')
    }
    portfolioData.value = result
  } catch (error) {
    console.error('Failed to run portfolio backtest:', error)
  } finally {
    loading.value = false
  }
}

async function generatePlan() {
  planning.value = true
  try {
    const response = await apiFetch('/portfolio/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        universe_id: selectedUniverseId.value,
        strategy_id: selectedStrategyId.value,
        max_positions: maxPositions.value,
        cash_reserve_ratio: cashReserveRatio.value,
        current_cash: currentCash.value,
        holdings: holdings.value.filter(item => item.stock_code.trim() && item.shares > 0),
        strategy_params: strategyParams.value,
      }),
    })
    const result = await response.json()
    if (!response.ok || result.detail) {
      throw new Error(result.detail || '明日计划生成失败')
    }
    planData.value = result
  } catch (error) {
    console.error('Failed to generate plan:', error)
  } finally {
    planning.value = false
  }
}

function renderEquityChart() {
  if (!equityChartRef.value || !portfolioData.value?.equity_curve) return
  if (equityChartInstance) {
    equityChartInstance.dispose()
  }
  equityChartInstance = echarts.init(equityChartRef.value)
  const dates = portfolioData.value.equity_curve.map(item => item.date)
  const equity = portfolioData.value.equity_curve.map(item => item.equity)
  const benchmarkEquity = (portfolioData.value.benchmark_curve || []).map(item => item.equity)
  const benchmarkName = `${portfolioData.value.benchmark?.label || '基准'}基准`
  const rebalances = portfolioData.value.rebalance_events.map(item => {
    const idx = dates.findIndex(date => date === item.signal_date)
    return idx >= 0 ? [idx, equity[idx]] : null
  }).filter(Boolean)

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
        if (!Array.isArray(params) || params.length === 0) return ''
        const dateLabel = params[0].axisValue
        const lines = params.map(item => {
          const name = item.seriesName
          const val = Array.isArray(item.value) ? item.value[1] : item.value
          if (val === null || val === undefined) return `${name}: -`
          return `${name}: ¥${formatNumber(val)}`
        })
        return `${dateLabel}<br/>${lines.join('<br/>')}`
      },
    },
    legend: {
      data: ['资金曲线', benchmarkName, '调仓节点'],
      textStyle: { color: '#98a2b3' },
      top: 10,
    },
    grid: { left: '8%', right: '8%', top: 60, bottom: '10%' },
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
      {
        name: benchmarkName,
        type: 'line',
        data: benchmarkEquity.length === equity.length ? benchmarkEquity : [],
        smooth: true,
        lineStyle: { width: 1.5, color: '#94a3b8', type: 'dashed' },
        showSymbol: false,
      },
      {
        name: '调仓节点',
        type: 'scatter',
        data: rebalances,
        symbolSize: 12,
        itemStyle: { color: '#ffd93d', borderColor: '#fff', borderWidth: 1 },
      },
    ],
  })
}

function handleResize() {
  equityChartInstance?.resize()
}

watch(selectedStrategyId, value => {
  if (value) {
    applyStrategyDefaults(value)
  }
})

watch([startDate, endDate], ([s, e]) => {
  if (s) {
    selectedPeriod.value = 'custom'
  }
})

watch(
  () => [loading.value, portfolioData.value],
  async ([isLoading, data]) => {
    if (isLoading || !data) return
    await nextTick()
    renderEquityChart()
  },
  { flush: 'post' },
)

onMounted(async () => {
  await fetchCatalog()
  applyStateFromQuery()
  applyStrategyDefaults(selectedStrategyId.value)
  await runBacktest()
  await generatePlan()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
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
.small-btn {
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

.card-header,
.chart-header {
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
.metrics-section,
.plan-result-grid,
.two-column-grid {
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
.summary-bar,
.strategy-value,
.data-table td,
.loading-text,
.empty-text {
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

.param-section,
.holdings-section {
  margin-top: 1.5rem;
}

.section-row,
.action-row,
.summary-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.summary-bar {
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.holding-row {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr auto;
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.run-btn,
.small-btn {
  padding: 0.9rem 1.6rem;
  border-radius: 10px;
  border: 1px solid rgba(0, 212, 255, 0.35);
  background: linear-gradient(135deg, rgba(0, 212, 255, 0.24) 0%, rgba(0, 255, 136, 0.12) 100%);
  color: #fff;
  font-weight: 600;
}

.small-btn {
  padding: 0.6rem 1rem;
}

.danger-btn {
  border-color: rgba(255, 107, 107, 0.35);
  background: rgba(255, 107, 107, 0.12);
}

.run-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
  white-space: nowrap;
}

.chart-container {
  width: 100%;
  height: 460px;
}

.table-container {
  overflow-x: auto;
}

.slim-table {
  max-height: 420px;
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
  vertical-align: top;
}

.data-table td {
  padding: 0.875rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  vertical-align: top;
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

.plan-card {
  margin-top: 2rem;
}

.full-span {
  grid-column: 1 / -1;
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

@media (max-width: 900px) {
  .holding-row {
    grid-template-columns: 1fr;
  }
}
</style>
