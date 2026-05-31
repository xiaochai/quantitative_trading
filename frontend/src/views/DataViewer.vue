<template>
  <div class="data-viewer-container">
    <div class="back-section">
      <button class="back-btn" @click="goBack">
        <span class="back-arrow">←</span>
        <span class="back-text">返回首页</span>
      </button>
    </div>

    <div class="header-section">
      <div class="header-glow"></div>
      <div class="header-content">
        <h1>📊 数据库数据浏览</h1>
        <p class="subtitle">Database Data Browser</p>
      </div>
    </div>

    <div class="tabs-section">
      <div 
        class="tab" 
        :class="{ active: activeTab === 'daily_quotes' }"
        @click="switchTab('daily_quotes')"
      >
        日线行情
      </div>
      <div 
        class="tab" 
        :class="{ active: activeTab === 'index_daily_quotes' }"
        @click="switchTab('index_daily_quotes')"
      >
        指数行情
      </div>
      <div 
        class="tab" 
        :class="{ active: activeTab === 'stock_fundamentals' }"
        @click="switchTab('stock_fundamentals')"
      >
        股票基本面
      </div>
      <div 
        class="tab" 
        :class="{ active: activeTab === 'stock_info' }"
        @click="switchTab('stock_info')"
      >
        股票信息
      </div>
    </div>

    <!-- 筛选区域 -->
    <div class="filter-section">
      <div class="filter-wrapper">
        <div class="filter-glow"></div>
        <input 
          type="text" 
          v-model="filterStockCode" 
          :placeholder="filterPlaceholder"
          @keyup.enter="applyFilter"
          class="filter-input"
        />
        <button @click="applyFilter" class="filter-btn">
          <span class="btn-text">筛选</span>
        </button>
        <button @click="clearFilter" class="clear-btn">
          <span class="btn-text">清除</span>
        </button>
      </div>
    </div>

    <div class="content-section">
      <div class="loading-wrapper" v-if="loading">
        <div class="loader">
          <div class="loader-ring"></div>
          <div class="loader-ring"></div>
          <div class="loader-ring"></div>
        </div>
        <p class="loading-text">加载中...</p>
      </div>

      <div v-else class="data-content">
        <div class="stats-info">
        <span class="stat-item">总记录数: {{ total }}</span>
        <span class="stat-item">当前页: {{ currentPage }} / {{ totalPages }}</span>
        </div>

        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
              <th v-for="col in tableColumns" :key="col.key">{{ col.label }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in tableData" :key="row.id">
              <td v-for="col in tableColumns" :key="col.key">
                {{ formatCellValue(row[col.key], col.key) }}
              </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination-section">
          <button 
            class="pagination-btn" 
            :disabled="currentPage <= 1" 
            @click="changePage(currentPage - 1)"
          >
            上一页
          </button>
          <span class="pagination-info">{{ currentPage }} / {{ totalPages }}</span>
          <button 
            class="pagination-btn" 
            :disabled="currentPage >= totalPages" 
            @click="changePage(currentPage + 1)"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiFetch } from '../api'

const router = useRouter()
const activeTab = ref('daily_quotes')
const loading = ref(false)
const currentPage = ref(1)
const total = ref(0)
const tableData = ref([])
const filterStockCode = ref('')
const PAGE_SIZE = 1000

const totalPages = computed(() => Math.ceil(total.value / PAGE_SIZE))

const tableColumns = computed(() => {
  const columns = {
    daily_quotes: [
      { key: 'id', label: 'ID' },
      { key: 'stock_code', label: '股票代码' },
      { key: 'trade_date', label: '交易日期' },
      { key: 'open', label: '开盘' },
      { key: 'close', label: '收盘' },
      { key: 'high', label: '最高' },
      { key: 'low', label: '最低' },
      { key: 'volume', label: '成交量' },
      { key: 'amount', label: '成交额' },
      { key: 'change_pct', label: '涨跌幅' },
      { key: 'change_20d_pct', label: '20日涨幅' },
      { key: 'turnover_rate', label: '换手率' },
      { key: 'market_cap', label: '市值' },
      { key: 'pe_ttm', label: 'PE-TTM' },
      { key: 'ma5', label: 'MA5' },
      { key: 'ma20', label: 'MA20' },
      { key: 'ma60', label: 'MA60' },
      { key: 'macd', label: 'MACD' },
      { key: 'macd_signal', label: 'MACD-Signal' },
      { key: 'macd_hist', label: 'MACD-Hist' },
      { key: 'rsi', label: 'RSI' },
      { key: 'boll_upper', label: 'BOLL-上' },
      { key: 'boll_middle', label: 'BOLL-中' },
      { key: 'boll_lower', label: 'BOLL-下' }
    ],
    index_daily_quotes: [
      { key: 'id', label: 'ID' },
      { key: 'index_code', label: '指数代码' },
      { key: 'trade_date', label: '交易日期' },
      { key: 'open', label: '开盘' },
      { key: 'close', label: '收盘' },
      { key: 'high', label: '最高' },
      { key: 'low', label: '最低' },
      { key: 'volume', label: '成交量' },
      { key: 'amount', label: '成交额' },
      { key: 'change_pct', label: '涨跌幅' }
    ],
    stock_fundamentals: [
      { key: 'id', label: 'ID' },
      { key: 'stock_code', label: '股票代码' },
      { key: 'report_date', label: '报告日期' },
      { key: 'pb', label: 'PB' },
      { key: 'roe', label: 'ROE' },
      { key: 'eps', label: 'EPS' },
      { key: 'eps_ttm', label: 'EPS-TTM' },
      { key: 'net_profit_growth', label: '净利润增长' },
      { key: 'revenue_growth', label: '营收增长' },
      { key: 'dividend_yield', label: '股息率' }
    ],
    stock_info: [
      { key: 'id', label: 'ID' },
      { key: 'stock_code', label: '股票代码' },
      { key: 'stock_name', label: '股票名称' },
      { key: 'industry_sw1', label: '申万一级' },
      { key: 'industry_sw2', label: '申万二级' },
      { key: 'is_st', label: 'ST' },
      { key: 'is_star_st', label: '*ST' },
      { key: 'is_delisted', label: '退市' },
      { key: 'delisted_date', label: '退市日期' },
      { key: 'listed_date', label: '上市日期' },
      { key: 'component_tags', label: '标签' },
      { key: 'report_date', label: '报告日期' }
    ]
  }
  return columns[activeTab.value] || []
})

const apiEndpoints = {
  daily_quotes: '/data/daily_quotes',
  index_daily_quotes: '/data/index_daily_quotes',
  stock_fundamentals: '/data/stock_fundamentals',
  stock_info: '/data/stock_info'
}

const filterParamName = computed(() => {
  return activeTab.value === 'index_daily_quotes' ? 'index_code' : 'stock_code'
})

const filterPlaceholder = computed(() => {
  if (activeTab.value === 'index_daily_quotes') {
    return '输入指数代码筛选 (如 000300.SH)，留空显示全部'
  }
  return '输入股票代码筛选 (如 600036.SH)，留空显示全部'
})

function goBack() {
  router.push({ name: 'Home' })
}

function formatCellValue(value, key) {
  if (value === null || value === undefined) {
    return '-'
  }
  if (typeof value === 'boolean') {
    return value ? '是' : '否'
  }
  if (typeof value === 'number') {
    if (key === 'volume' || key === 'amount' || key === 'market_cap') {
      return value.toLocaleString()
    }
    return value.toFixed ? value.toFixed(4) : value
  }
  return value
}

async function loadData() {
  loading.value = true
  try {
    const endpoint = apiEndpoints[activeTab.value]
    let url = `${endpoint}?page=${currentPage.value}&page_size=${PAGE_SIZE}`
    if (filterStockCode.value) {
      url += `&${filterParamName.value}=${encodeURIComponent(filterStockCode.value)}`
    }
    const response = await apiFetch(url)
    const data = await response.json()
    total.value = data.total
    tableData.value = data.items
  } catch (error) {
    console.error('加载数据失败:', error)
  } finally {
    loading.value = false
  }
}

function switchTab(tab) {
  activeTab.value = tab
  currentPage.value = 1
  loadData()
}

function changePage(page) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  loadData()
}

function applyFilter() {
  currentPage.value = 1
  loadData()
}

function clearFilter() {
  filterStockCode.value = ''
  currentPage.value = 1
  loadData()
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.data-viewer-container {
  max-width: 1800px;
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
  font-size: 2rem;
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

.tabs-section {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.tab {
  flex: 1;
  padding: 1rem 2rem;
  background: rgba(15,23,42,0.8);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 12px;
  color: #98a2b3;
  font-size: 1rem;
  font-weight: 500;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
}

.tab:hover {
  border-color: rgba(0,212,255,0.4);
  color: #00d4ff;
}

.tab.active {
  background: linear-gradient(135deg, rgba(0,212,255,0.2) 0%, rgba(0,255,136,0.1) 100%);
  border-color: rgba(0,212,255,0.5);
  color: #fff;
}

.filter-section {
  margin-bottom: 2rem;
}

.filter-wrapper {
  position: relative;
  display: flex;
  gap: 1rem;
  max-width: 1000px;
}

.filter-glow {
  position: absolute;
  inset: -2px;
  background: linear-gradient(90deg, #00d4ff, #00ff88, #00d4ff);
  border-radius: 12px;
  opacity: 0;
  transition: opacity 0.3s;
  filter: blur(4px);
  z-index: 0;
}

.filter-wrapper:focus-within .filter-glow {
  opacity: 0.5;
}

.filter-input {
  flex: 1;
  position: relative;
  z-index: 1;
  padding: 1rem 1.5rem;
  background: rgba(15,23,42,0.8);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  color: #fff;
  font-size: 1rem;
  outline: none;
  transition: all 0.3s;
}

.filter-input:focus {
  border-color: rgba(0,212,255,0.5);
}

.filter-input::placeholder {
  color: #475467;
}

.filter-btn,
.clear-btn {
  position: relative;
  z-index: 1;
  padding: 1rem 2rem;
  background: linear-gradient(135deg, #00d4ff 0%, #00a3cc 100%);
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.3s;
}

.filter-btn:hover,
.clear-btn:hover {
  transform: scale(1.02);
  box-shadow: 0 0 30px rgba(0,212,255,0.4);
}

.clear-btn {
  background: rgba(15,23,42,0.8);
  border: 1px solid rgba(255,255,255,0.1);
}

.clear-btn:hover {
  box-shadow: none;
  border-color: rgba(0,212,255,0.4);
}

.content-section {
  background: linear-gradient(135deg, rgba(15,23,42,0.9) 0%, rgba(15,23,42,0.7) 100%);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 2rem;
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

.stats-info {
  display: flex;
  gap: 2rem;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}

.stat-item {
  color: #98a2b3;
  font-size: 0.875rem;
  letter-spacing: 1px;
}

.table-container {
  max-height: 600px;
  overflow-x: auto;
  overflow-y: auto;
  margin-bottom: 1.5rem;
}

.table-container::-webkit-scrollbar {
  width: 6px;
  height: 6px;
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
  font-size: 0.8125rem;
}

.data-table thead {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgba(15,23,42,0.95);
}

.data-table th {
  padding: 0.875rem 1rem;
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
  padding: 0.625rem 1rem;
  color: #98a2b3;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  white-space: nowrap;
}

.data-table tbody tr:hover {
  background: rgba(0,212,255,0.05);
}

.pagination-section {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255,255,255,0.06);
}

.pagination-btn {
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

.pagination-btn:hover:not(:disabled) {
  border-color: rgba(0,212,255,0.4);
  color: #00d4ff;
}

.pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination-info {
  color: #98a2b3;
  font-size: 0.875rem;
  letter-spacing: 1px;
}
</style>
