<template>
  <div class="detail-container">
    <!-- 返回按钮 -->
    <div class="back-section">
      <button class="back-btn" @click="goBack">
        <span class="back-arrow">←</span>
        <span class="back-text">返回首页</span>
      </button>
    </div>

    <!-- 头部信息 -->
    <div class="header-section">
      <div class="header-glow"></div>
      <div class="header-content">
        <h1 class="stock-title">{{ stockInfo?.stock_name || stockCode }}</h1>
        <p class="stock-subtitle">{{ stockCode }} - 股票详情分析</p>
      </div>
    </div>

    <!-- 加载状态 -->
    <div class="loading-wrapper" v-if="loading">
      <div class="loader">
        <div class="loader-ring"></div>
        <div class="loader-ring"></div>
        <div class="loader-ring"></div>
      </div>
      <p class="loading-text">加载中...</p>
    </div>

    <div v-else-if="quotes.length > 0">
      <!-- 股票基本信息卡片 -->
      <div class="info-card" v-if="stockInfo">
        <div class="card-header">
          <h3>📋 基本信息</h3>
        </div>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">股票代码(Code)</span>
            <span class="info-value">{{ stockInfo.stock_code }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">股票名称(Name)</span>
            <span class="info-value">{{ stockInfo.stock_name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">申万一级行业(SW1)</span>
            <span class="info-value">{{ stockInfo.industry_sw1 || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">申万二级行业(SW2)</span>
            <span class="info-value">{{ stockInfo.industry_sw2 || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">是否ST(ST)</span>
            <span class="info-value" :class="{'warning': stockInfo.is_st}">{{ stockInfo.is_st ? '是' : '否' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">是否*ST(*ST)</span>
            <span class="info-value" :class="{'warning': stockInfo.is_star_st}">{{ stockInfo.is_star_st ? '是' : '否' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">是否退市(Delisted)</span>
            <span class="info-value" :class="{'danger': stockInfo.is_delisted}">{{ stockInfo.is_delisted ? '是' : '否' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">上市日期(Listed)</span>
            <span class="info-value">{{ stockInfo.listed_date || '-' }}</span>
          </div>
        </div>
        <!-- 成分标签 -->
        <div class="component-tags-section" v-if="stockInfo.component_tags && stockInfo.component_tags.length > 0">
          <span class="info-label">成分指数(Indices)</span>
          <div class="component-tags">
            <span class="component-tag" v-for="(tag, index) in stockInfo.component_tags" :key="index">{{ tag }}</span>
          </div>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="stats-section" v-if="latestQuote">
        <div class="stat-card">
          <div class="stat-label">最新收盘价(Close)</div>
          <div class="stat-value">{{ latestQuote.close != null ? latestQuote.close.toFixed(2) : '-' }}</div>
        </div>
        <div class="stat-card" :class="{'stat-up': latestQuote.change_pct != null && latestQuote.change_pct >= 0, 'stat-down': latestQuote.change_pct != null && latestQuote.change_pct < 0}">
          <div class="stat-label">涨跌幅(Change)</div>
          <div class="stat-value">
            {{ latestQuote.change_pct != null ? (latestQuote.change_pct >= 0 ? '+' : '') + latestQuote.change_pct.toFixed(2) + '%' : '-' }}
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">市盈率(PE-TTM)</div>
          <div class="stat-value">{{ latestQuote.pe_ttm != null ? latestQuote.pe_ttm.toFixed(2) : '-' }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">市值(Market Cap)</div>
          <div class="stat-value">{{ formatMarketCap(latestQuote.market_cap) }}</div>
        </div>
      </div>

      <!-- 图表区域 -->
      <div class="charts-container">
        <!-- K线图 -->
        <div class="chart-card">
          <div class="chart-header">
            <h3>📊 K线图与均线(K-line & MA)</h3>
          </div>
          <div ref="klineChart" class="chart-container"></div>
        </div>

        <!-- MACD -->
        <div class="chart-card">
          <div class="chart-header">
            <h3>📈 MACD指标</h3>
          </div>
          <div ref="macdChart" class="chart-container"></div>
        </div>

        <!-- RSI -->
        <div class="chart-card">
          <div class="chart-header">
            <h3>📉 RSI指标</h3>
          </div>
          <div ref="rsiChart" class="chart-container"></div>
        </div>

        <!-- 布林带 -->
        <div class="chart-card">
          <div class="chart-header">
            <h3>🔍 布林带(Bollinger Bands)</h3>
          </div>
          <div ref="bollChart" class="chart-container"></div>
        </div>
      </div>

      <!-- 财务基本面数据 -->
      <div class="chart-card" v-if="fundamentals.length > 0">
        <div class="chart-header">
          <h3>📊 财务基本面数据</h3>
        </div>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>报告期(Report)</th>
                <th>市净率(PB)</th>
                <th>净资产收益率(ROE)</th>
                <th>每股收益(EPS)</th>
                <th>每股收益(EPS-TTM)</th>
                <th>净利润增速(NetProfit)</th>
                <th>营收增速(Revenue)</th>
                <th>股息率(Dividend)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="f in fundamentals" :key="f.report_date">
                <td class="date-cell">{{ f.report_date }}</td>
                <td>{{ f.pb != null ? f.pb.toFixed(2) : '-' }}</td>
                <td>{{ f.roe != null ? f.roe.toFixed(2) + '%' : '-' }}</td>
                <td>{{ f.eps != null ? f.eps.toFixed(3) : '-' }}</td>
                <td>{{ f.eps_ttm != null ? f.eps_ttm.toFixed(3) : '-' }}</td>
                <td :class="{'change-up': f.net_profit_growth != null && f.net_profit_growth >= 0, 'change-down': f.net_profit_growth != null && f.net_profit_growth < 0}">
                  {{ f.net_profit_growth != null ? (f.net_profit_growth >= 0 ? '+' : '') + f.net_profit_growth.toFixed(2) + '%' : '-' }}
                </td>
                <td :class="{'change-up': f.revenue_growth != null && f.revenue_growth >= 0, 'change-down': f.revenue_growth != null && f.revenue_growth < 0}">
                  {{ f.revenue_growth != null ? (f.revenue_growth >= 0 ? '+' : '') + f.revenue_growth.toFixed(2) + '%' : '-' }}
                </td>
                <td>{{ f.dividend_yield != null ? f.dividend_yield.toFixed(2) + '%' : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 日线数据表格 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>📋 日线行情数据</h3>
        </div>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>日期(Date)</th>
                <th>开盘(Open)</th>
                <th>收盘(Close)</th>
                <th>最高(High)</th>
                <th>最低(Low)</th>
                <th>成交量(Volume)</th>
                <th>成交额(Amount)</th>
                <th>涨跌幅(Change)</th>
                <th>20日涨幅(20d)</th>
                <th>换手率(Turnover)</th>
                <th>MA5</th>
                <th>MA20</th>
                <th>MA60</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in recentQuotes" :key="q.trade_date">
                <td class="date-cell">{{ q.trade_date }}</td>
                <td>{{ q.open != null ? q.open.toFixed(2) : '-' }}</td>
                <td>{{ q.close != null ? q.close.toFixed(2) : '-' }}</td>
                <td>{{ q.high != null ? q.high.toFixed(2) : '-' }}</td>
                <td>{{ q.low != null ? q.low.toFixed(2) : '-' }}</td>
                <td class="num-cell">{{ formatVolume(q.volume) }}</td>
                <td class="num-cell">{{ formatAmount(q.amount) }}</td>
                <td :class="{'change-up': q.change_pct != null && q.change_pct >= 0, 'change-down': q.change_pct != null && q.change_pct < 0}">
                  {{ q.change_pct != null ? (q.change_pct >= 0 ? '+' : '') + q.change_pct.toFixed(2) + '%' : '-' }}
                </td>
                <td :class="{'change-up': q.change_20d_pct != null && q.change_20d_pct >= 0, 'change-down': q.change_20d_pct != null && q.change_20d_pct < 0}">
                  {{ q.change_20d_pct != null ? (q.change_20d_pct >= 0 ? '+' : '') + q.change_20d_pct.toFixed(2) + '%' : '-' }}
                </td>
                <td>{{ q.turnover_rate != null ? q.turnover_rate.toFixed(2) + '%' : '-' }}</td>
                <td>{{ q.ma5 != null ? q.ma5.toFixed(2) : '-' }}</td>
                <td>{{ q.ma20 != null ? q.ma20.toFixed(2) : '-' }}</td>
                <td>{{ q.ma60 != null ? q.ma60.toFixed(2) : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 技术指标详情 -->
      <div class="chart-card">
        <div class="chart-header">
          <h3>🔧 技术指标详情</h3>
        </div>
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>日期(Date)</th>
                <th>MACD</th>
                <th>MACD信号(Signal)</th>
                <th>MACD柱状图(Hist)</th>
                <th>RSI</th>
                <th>布林带上轨(Upper)</th>
                <th>布林带中轨(Middle)</th>
                <th>布林带下轨(Lower)</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="q in recentQuotes" :key="q.trade_date">
                <td class="date-cell">{{ q.trade_date }}</td>
                <td :class="{'change-up': q.macd != null && q.macd >= 0, 'change-down': q.macd != null && q.macd < 0}">
                  {{ q.macd != null ? q.macd.toFixed(4) : '-' }}
                </td>
                <td :class="{'change-up': q.macd_signal != null && q.macd_signal >= 0, 'change-down': q.macd_signal != null && q.macd_signal < 0}">
                  {{ q.macd_signal != null ? q.macd_signal.toFixed(4) : '-' }}
                </td>
                <td :class="{'change-up': q.macd_hist != null && q.macd_hist >= 0, 'change-down': q.macd_hist != null && q.macd_hist < 0}">
                  {{ q.macd_hist != null ? q.macd_hist.toFixed(4) : '-' }}
                </td>
                <td>{{ q.rsi != null ? q.rsi.toFixed(2) : '-' }}</td>
                <td>{{ q.boll_upper != null ? q.boll_upper.toFixed(2) : '-' }}</td>
                <td>{{ q.boll_middle != null ? q.boll_middle.toFixed(2) : '-' }}</td>
                <td>{{ q.boll_lower != null ? q.boll_lower.toFixed(2) : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { apiFetch } from '../api'

const route = useRoute()
const router = useRouter()
const stockCode = computed(() => route.params.code)

const loading = ref(false)
const quotes = ref([])
const stockInfo = ref(null)
const fundamentals = ref([])
const klineChart = ref(null)
const macdChart = ref(null)
const rsiChart = ref(null)
const bollChart = ref(null)
let klineChartInstance = null
let macdChartInstance = null
let rsiChartInstance = null
let bollChartInstance = null

const latestQuote = computed(() => quotes.value[quotes.value.length - 1])
const recentQuotes = computed(() => quotes.value.slice().reverse().slice(0, 60))

function goBack() {
  router.push({ name: 'Home' })
}

function formatMarketCap(cap) {
  if (!cap) return '-'
  if (cap >= 10000) return (cap / 10000).toFixed(2) + ' 万亿'
  return cap.toFixed(2) + ' 亿'
}

function formatVolume(vol) {
  if (!vol) return '-'
  if (vol >= 100000000) return (vol / 100000000).toFixed(2) + ' 亿'
  if (vol >= 10000) return (vol / 10000).toFixed(2) + ' 万'
  return vol.toString()
}

function formatAmount(amt) {
  if (!amt) return '-'
  if (amt >= 100000000) return (amt / 100000000).toFixed(2) + ' 亿'
  if (amt >= 10000) return (amt / 10000).toFixed(2) + ' 万'
  return amt.toFixed(0)
}

async function loadStockData() {
  const code = stockCode.value
  if (!code) return

  loading.value = true
  try {
    // 加载股票信息
    const infoRes = await apiFetch(`/stock/${code}/info`)
    stockInfo.value = await infoRes.json()
    
    // 加载日线数据
    const quotesRes = await apiFetch(`/stock/${code}/quotes`)
    quotes.value = await quotesRes.json()
    
    // 加载财务数据
    const fundRes = await apiFetch(`/stock/${code}/fundamentals`)
    fundamentals.value = await fundRes.json()
    
    loading.value = false
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 150))
    renderCharts()
  } catch (error) {
    console.error('加载数据失败:', error)
    loading.value = false
  }
}

function renderCharts() {
  renderKlineChart()
  renderMacdChart()
  renderRsiChart()
  renderBollChart()
}

function renderKlineChart() {
  if (!klineChart.value) return
  if (klineChartInstance) {
    klineChartInstance.dispose()
  }
  klineChartInstance = echarts.init(klineChart.value)

  // 只保留有完整K线数据的记录
  const validQuotes = quotes.value.filter(q => q.open != null && q.close != null && q.high != null && q.low != null)
  
  const dates = validQuotes.map(q => q.trade_date)
  const klineData = validQuotes.map(q => [q.open, q.close, q.low, q.high])
  const volumes = validQuotes.map(q => q.volume)
  const amounts = validQuotes.map(q => q.amount)
  const ma5 = validQuotes.map(q => q.ma5)
  const ma20 = validQuotes.map(q => q.ma20)
  const ma60 = validQuotes.map(q => q.ma60)

  const formatAmount = (value) => {
    if (value == null) return '-'
    if (value >= 100000000) return (value / 100000000).toFixed(2) + ' 亿'
    if (value >= 10000) return (value / 10000).toFixed(2) + ' 万'
    return value.toFixed(0)
  }

  const formatVolume = (value) => {
    if (value == null) return '-'
    if (value >= 100000000) return (value / 100000000).toFixed(2) + ' 亿'
    if (value >= 10000) return (value / 10000).toFixed(2) + ' 万'
    return value.toString()
  }

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: 'rgba(15,23,42,0.95)',
      borderColor: 'rgba(0,212,255,0.3)',
      textStyle: { color: '#fff' },
      borderWidth: 1,
      formatter: function(params) {
        let result = ''
        const dataIndex = params[0].dataIndex
        const quote = validQuotes[dataIndex]
        
        if (quote) {
          result += `<div style="font-weight: bold; margin-bottom: 8px;">${quote.trade_date}</div>`
          result += `<div style="margin: 4px 0;">开: ${quote.open?.toFixed(2) || '-'} </div>`
          result += `<div style="margin: 4px 0;">收: ${quote.close?.toFixed(2) || '-'} </div>`
          result += `<div style="margin: 4px 0;">高: ${quote.high?.toFixed(2) || '-'} </div>`
          result += `<div style="margin: 4px 0;">低: ${quote.low?.toFixed(2) || '-'} </div>`
          result += `<div style="margin: 4px 0;">成交量: ${formatVolume(quote.volume)} </div>`
          result += `<div style="margin: 4px 0;">成交额: ${formatAmount(quote.amount)} </div>`
          
          params.forEach(p => {
            if (p.seriesName.includes('MA')) {
              result += `<div style="margin: 4px 0;">${p.seriesName}: ${p.value?.toFixed(2) || '-'} </div>`
            }
          })
        }
        
        return result
      }
    },
    legend: {
      data: ['K线', 'MA5', 'MA20', 'MA60'],
      textStyle: { color: '#98a2b3' },
      top: 10
    },
    grid: [
      { left: '10%', right: '10%', top: 70, height: '50%' },
      { left: '10%', right: '10%', top: '73%', height: '15%' }
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        scale: true,
        boundaryGap: false,
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
        axisLabel: { color: '#667085' },
        splitLine: { show: false }
      },
      {
        type: 'category',
        gridIndex: 1,
        data: dates,
        scale: true,
        boundaryGap: false,
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
        axisLabel: { color: '#667085' },
        splitLine: { show: false }
      }
    ],
    yAxis: [
      {
        scale: true,
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
        axisLabel: { color: '#667085' },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
      },
      {
        scale: true,
        gridIndex: 1,
        axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
        axisLabel: { color: '#667085' },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
      }
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 }
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
        name: 'MA5',
        type: 'line',
        data: ma5,
        smooth: true,
        lineStyle: { width: 1.5, color: '#ff6b6b' },
        showSymbol: false
      },
      {
        name: 'MA20',
        type: 'line',
        data: ma20,
        smooth: true,
        lineStyle: { width: 1.5, color: '#ffd93d' },
        showSymbol: false
      },
      {
        name: 'MA60',
        type: 'line',
        data: ma60,
        smooth: true,
        lineStyle: { width: 1.5, color: '#00d4ff' },
        showSymbol: false
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: volumes,
        itemStyle: {
          color: function(params) {
            const index = params.dataIndex
            const quote = validQuotes[index]
            return quote?.close >= quote?.open ? 'rgba(255,107,107,0.7)' : 'rgba(0,255,136,0.7)'
          }
        }
      }
    ]
  }
  klineChartInstance.setOption(option)
}

function renderMacdChart() {
  if (!macdChart.value) return
  if (macdChartInstance) {
    macdChartInstance.dispose()
  }
  macdChartInstance = echarts.init(macdChart.value)

  // 只保留有MACD数据的记录
  const validQuotes = quotes.value.filter(q => q.macd != null && q.macd_signal != null && q.macd_hist != null)
  
  const dates = validQuotes.map(q => q.trade_date)
  const macd = validQuotes.map(q => q.macd)
  const macdSignal = validQuotes.map(q => q.macd_signal)
  const macdHist = validQuotes.map(q => q.macd_hist)

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
      data: ['MACD', 'Signal', 'Histogram'],
      textStyle: { color: '#98a2b3' },
      top: 10
    },
    grid: { left: '10%', right: '10%', top: 70, bottom: '10%' },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#667085' },
      splitLine: { show: false }
    },
    yAxis: {
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#667085' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    dataZoom: [{ type: 'inside', start: 0, end: 100 }],
    series: [
      {
        name: 'MACD',
        type: 'line',
        data: macd,
        smooth: true,
        lineStyle: { width: 2, color: '#00d4ff' },
        showSymbol: false
      },
      {
        name: 'Signal',
        type: 'line',
        data: macdSignal,
        smooth: true,
        lineStyle: { width: 2, color: '#ff6b6b' },
        showSymbol: false
      },
      {
        name: 'Histogram',
        type: 'bar',
        data: macdHist,
        itemStyle: {
          color: function(params) {
            return params.value >= 0 ? 'rgba(255,107,107,0.7)' : 'rgba(0,255,136,0.7)'
          }
        }
      }
    ]
  }
  macdChartInstance.setOption(option)
}

function renderRsiChart() {
  if (!rsiChart.value) return
  if (rsiChartInstance) {
    rsiChartInstance.dispose()
  }
  rsiChartInstance = echarts.init(rsiChart.value)

  // 只保留有RSI数据的记录
  const validQuotes = quotes.value.filter(q => q.rsi != null)
  
  const dates = validQuotes.map(q => q.trade_date)
  const rsi = validQuotes.map(q => q.rsi)

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
      data: ['RSI', '超买线70', '超卖线30'],
      textStyle: { color: '#98a2b3' },
      top: 10
    },
    grid: { left: '10%', right: '10%', top: 70, bottom: '10%' },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#667085' },
      splitLine: { show: false }
    },
    yAxis: {
      min: 0,
      max: 100,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#667085' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    dataZoom: [{ type: 'inside', start: 0, end: 100 }],
    series: [
      {
        name: 'RSI',
        type: 'line',
        data: rsi,
        smooth: true,
        lineStyle: { width: 2, color: '#ffd93d' },
        showSymbol: false
      },
      {
        name: '超买线70',
        type: 'line',
        data: new Array(dates.length).fill(70),
        lineStyle: { width: 1, color: 'rgba(255,107,107,0.4)', type: 'dashed' },
        showSymbol: false
      },
      {
        name: '超卖线30',
        type: 'line',
        data: new Array(dates.length).fill(30),
        lineStyle: { width: 1, color: 'rgba(0,255,136,0.4)', type: 'dashed' },
        showSymbol: false
      }
    ]
  }
  rsiChartInstance.setOption(option)
}

function renderBollChart() {
  if (!bollChart.value) return
  if (bollChartInstance) {
    bollChartInstance.dispose()
  }
  bollChartInstance = echarts.init(bollChart.value)

  // 只保留有布林带数据的记录
  const validQuotes = quotes.value.filter(q => 
    q.close != null && q.boll_upper != null && q.boll_middle != null && q.boll_lower != null
  )
  
  const dates = validQuotes.map(q => q.trade_date)
  const close = validQuotes.map(q => q.close)
  const bollUpper = validQuotes.map(q => q.boll_upper)
  const bollMiddle = validQuotes.map(q => q.boll_middle)
  const bollLower = validQuotes.map(q => q.boll_lower)

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
      data: ['收盘价', '上轨', '中轨', '下轨'],
      textStyle: { color: '#98a2b3' },
      top: 10
    },
    grid: { left: '10%', right: '10%', top: 70, bottom: '10%' },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#667085' },
      splitLine: { show: false }
    },
    yAxis: {
      scale: true,
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      axisLabel: { color: '#667085' },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    dataZoom: [{ type: 'inside', start: 0, end: 100 }],
    series: [
      {
        name: '收盘价',
        type: 'line',
        data: close,
        smooth: true,
        lineStyle: { width: 2, color: '#fff' },
        showSymbol: false
      },
      {
        name: '上轨',
        type: 'line',
        data: bollUpper,
        smooth: true,
        lineStyle: { width: 1.5, color: '#ff6b6b' },
        showSymbol: false
      },
      {
        name: '中轨',
        type: 'line',
        data: bollMiddle,
        smooth: true,
        lineStyle: { width: 1.5, color: '#ffd93d' },
        showSymbol: false
      },
      {
        name: '下轨',
        type: 'line',
        data: bollLower,
        smooth: true,
        lineStyle: { width: 1.5, color: '#00ff88' },
        showSymbol: false
      }
    ]
  }
  bollChartInstance.setOption(option)
}

onMounted(() => {
  loadStockData()
  window.addEventListener('resize', () => {
    klineChartInstance?.resize()
    macdChartInstance?.resize()
    rsiChartInstance?.resize()
    bollChartInstance?.resize()
  })
})
</script>

<style scoped>
.detail-container {
  max-width: 1600px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
}

/* 返回按钮 */
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

/* 头部区域 */
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

.stock-title {
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

.stock-subtitle {
  color: #667085;
  font-size: 0.875rem;
  letter-spacing: 3px;
  text-transform: uppercase;
}

/* 加载状态 */
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

/* 信息卡片 */
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

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background: rgba(0,0,0,0.2);
  border-radius: 10px;
}

.info-label {
  color: #667085;
  font-size: 0.75rem;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.info-value {
  color: #fff;
  font-size: 1rem;
  font-weight: 500;
}

.info-value.warning {
  color: #ffd93d;
}

.info-value.danger {
  color: #ff6b6b;
}

/* 成分标签 */
.component-tags-section {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid rgba(255,255,255,0.06);
}

.component-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.component-tag {
  padding: 0.5rem 1rem;
  background: linear-gradient(135deg, rgba(0,212,255,0.2) 0%, rgba(0,255,136,0.1) 100%);
  border: 1px solid rgba(0,212,255,0.3);
  border-radius: 8px;
  color: #00d4ff;
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 1px;
  transition: all 0.3s ease;
}

.component-tag:hover {
  border-color: rgba(0,255,136,0.5);
  color: #00ff88;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,212,255,0.2);
}

/* 统计卡片 */
.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  position: relative;
  background: linear-gradient(135deg, rgba(15,23,42,0.8) 0%, rgba(15,23,42,0.6) 100%);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 1.5rem;
  text-align: center;
  overflow: hidden;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0,212,255,0.3);
}

.stat-up {
  border-color: rgba(255,107,107,0.2);
}

.stat-down {
  border-color: rgba(0,255,136,0.2);
}

.stat-label {
  color: #667085;
  font-size: 0.75rem;
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-bottom: 0.75rem;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #fff;
}

.stat-up .stat-value {
  color: #ff6b6b;
}

.stat-down .stat-value {
  color: #00ff88;
}

/* 图表容器 */
.charts-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.chart-card {
  position: relative;
  background: linear-gradient(135deg, rgba(15,23,42,0.9) 0%, rgba(15,23,42,0.7) 100%);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s ease;
  margin-bottom: 2rem;
}

.chart-card:hover {
  border-color: rgba(0,212,255,0.3);
}

.chart-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
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
  height: 400px;
  min-height: 400px;
  padding: 1rem;
}

/* 表格样式 */
.table-container {
  padding: 0 1.5rem 1.5rem;
  max-height: 600px;
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

.num-cell {
  font-family: 'SF Mono', monospace;
}

.change-up {
  color: #ff6b6b;
  font-weight: 600;
}

.change-down {
  color: #00ff88;
  font-weight: 600;
}
</style>
