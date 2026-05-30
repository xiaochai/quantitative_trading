<template>
  <div class="home-container">
    <!-- 顶部标题栏 -->
    <div class="header-section">
      <div class="header-glow"></div>
      <div class="header-content">
        <h1>📈 QUANTITATIVE TRADING SYSTEM</h1>
        <p class="subtitle">股票数据分析与回测平台</p>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-section" v-if="summary">
      <div class="stat-card stat-card-primary">
        <div class="stat-icon">📊</div>
        <div class="stat-content">
          <div class="stat-label">STOCK QUANTITY</div>
          <div class="stat-value">{{ summary.total_stocks }}</div>
        </div>
        <div class="stat-glow stat-glow-cyan"></div>
      </div>
      <div class="stat-card stat-card-secondary">
        <div class="stat-icon">📅</div>
        <div class="stat-content">
          <div class="stat-label">LATEST DATE</div>
          <div class="stat-value">{{ summary.latest_date || '-' }}</div>
        </div>
        <div class="stat-glow stat-glow-green"></div>
      </div>
    </div>

    <!-- 功能操作区 -->
    <div class="action-section">
      <div class="input-wrapper">
        <div class="input-glow"></div>
        <input 
          type="text" 
          v-model="searchKeyword" 
          placeholder="输入股票代码或名称搜索"
          @keyup.enter="handleSearch"
          class="tech-input"
        />
        <button @click="handleSearch" class="tech-btn">
          <span class="btn-text">搜索</span>
          <span class="btn-glow"></span>
        </button>
      </div>
      <div class="quick-actions">
        <button @click="goToBacktest" class="quick-action-btn">
          <span class="btn-icon">📊</span>
          <span class="btn-text">策略回测</span>
        </button>
        <button @click="goToDataViewer" class="quick-action-btn">
          <span class="btn-icon">📋</span>
          <span class="btn-text">数据浏览</span>
        </button>
      </div>
    </div>

    <!-- 股票列表 -->
    <div class="stock-section">
      <div class="section-header">
        <h2>STOCK LIST</h2>
        <div class="divider"></div>
      </div>

      <div class="loading-wrapper" v-if="loading">
        <div class="loader">
          <div class="loader-ring"></div>
          <div class="loader-ring"></div>
          <div class="loader-ring"></div>
        </div>
        <p class="loading-text">LOADING...</p>
      </div>

      <div class="empty-state" v-else-if="stocks.length === 0">
        <div class="empty-icon">📭</div>
        <p class="empty-text">NO STOCK DATA</p>
        <p class="empty-hint">Use the input box above to add stocks</p>
      </div>

      <div class="stock-grid" v-else>
        <div 
          class="stock-card" 
          v-for="stock in stocks" 
          :key="stock.stock_code"
          @click="goToDetail(stock.stock_code)"
        >
          <div class="card-border"></div>
          <div class="card-content">
            <div class="stock-header">
              <div class="stock-name">{{ stock.stock_name }}</div>
              <div class="stock-code">{{ stock.stock_code }}</div>
            </div>
            <div class="stock-body">
              <div class="stock-price">
                <span class="price">{{ stock.latest_close?.toFixed(2) || '-' }}</span>
                <span 
                  class="change" 
                  :class="stock.change_pct >= 0 ? 'up' : 'down'"
                >
                  {{ stock.change_pct !== undefined ? `${stock.change_pct >= 0 ? '+' : ''}${stock.change_pct.toFixed(2)}%` : '-' }}
                </span>
              </div>
              <div class="stock-meta">
                <span class="meta-label">DATE:</span>
                <span class="meta-value">{{ stock.latest_date }}</span>
              </div>
            </div>
            <div class="stock-footer">
              <div class="action-btn">
                <span>VIEW DETAILS</span>
                <span class="arrow">→</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const loading = ref(false)
const stocks = ref([])
const summary = ref(null)
const searchKeyword = ref('')

async function fetchStocks(index = null, search = null) {
  loading.value = true
  try {
    let url = '/api/stocks'
    const params = new URLSearchParams()
    if (index) params.append('index', index)
    if (search) params.append('search', search)
    if (params.toString()) url += '?' + params.toString()
    
    const [stocksRes, summaryRes] = await Promise.all([
      fetch(url),
      fetch('/api/stocks/summary')
    ])
    stocks.value = await stocksRes.json()
    summary.value = await summaryRes.json()
  } catch (error) {
    console.error('Failed to fetch data:', error)
  } finally {
    loading.value = false
  }
}

function goToDetail(code) {
  router.push({ name: 'StockDetail', params: { code } })
}

function handleSearch() {
  const keyword = searchKeyword.value.trim()
  if (keyword) {
    fetchStocks(null, keyword)
  } else {
    loadHS300()
  }
}

function loadHS300() {
  searchKeyword.value = ''
  fetchStocks('沪深300', null)
}

function loadAllStocks() {
  searchKeyword.value = ''
  fetchStocks(null, null)
}

function goToDataViewer() {
  router.push({ name: 'DataViewer' })
}

function goToBacktest() {
  router.push({ name: 'Backtest' })
}

onMounted(() => {
  loadHS300()
})
</script>

<style scoped>
.home-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
}

/* 头部区域 */
.header-section {
  position: relative;
  text-align: center;
  margin-bottom: 3rem;
  padding: 3rem 0;
}

.header-glow {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 400px;
  height: 200px;
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
  text-shadow: 0 0 40px rgba(0,212,255,0.3);
}

@keyframes gradientMove {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.subtitle {
  color: #667085;
  font-size: 1rem;
  letter-spacing: 2px;
}

/* 统计卡片 */
.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.stat-card {
  position: relative;
  background: linear-gradient(135deg, rgba(15,23,42,0.8) 0%, rgba(15,23,42,0.6) 100%);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 2rem;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: 1.5rem;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-4px);
  border-color: rgba(0,212,255,0.3);
}

.stat-icon {
  font-size: 2.5rem;
  filter: drop-shadow(0 0 10px rgba(0,212,255,0.3));
}

.stat-content {
  flex: 1;
}

.stat-label {
  color: #667085;
  font-size: 0.75rem;
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: #fff;
}

.stat-glow {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  filter: blur(40px);
  opacity: 0.3;
}

.stat-glow-cyan {
  background: #00d4ff;
}

.stat-glow-green {
  background: #00ff88;
}

/* 操作区域 */
.action-section {
  margin-bottom: 3rem;
}

.input-wrapper {
  position: relative;
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  gap: 1rem;
}

.input-glow {
  position: absolute;
  inset: -2px;
  background: linear-gradient(90deg, #00d4ff, #00ff88, #00d4ff);
  border-radius: 12px;
  opacity: 0;
  transition: opacity 0.3s;
  filter: blur(4px);
  z-index: 0;
}

.input-wrapper:focus-within .input-glow {
  opacity: 0.5;
}

.tech-input {
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

.tech-input::placeholder {
  color: #475467;
}

.tech-input:focus {
  border-color: rgba(0,212,255,0.5);
}

.tech-btn {
  position: relative;
  padding: 1rem 2rem;
  background: linear-gradient(135deg, #00d4ff 0%, #00a3cc 100%);
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 1px;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s;
}

.tech-btn:hover {
  transform: scale(1.02);
  box-shadow: 0 0 30px rgba(0,212,255,0.4);
}

.btn-text {
  position: relative;
  z-index: 1;
}

.btn-glow {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
  transform: translateX(-100%);
}

.tech-btn:hover .btn-glow {
  animation: btnShine 0.6s ease;
}

@keyframes btnShine {
  100% { transform: translateX(100%); }
}

.quick-actions {
  display: flex;
  justify-content: center;
  margin-top: 1.5rem;
}

.quick-action-btn {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 2rem;
  background: linear-gradient(135deg, rgba(0,255,136,0.15) 0%, rgba(0,212,255,0.1) 100%);
  border: 1px solid rgba(0,212,255,0.3);
  border-radius: 12px;
  color: #fff;
  font-size: 0.9375rem;
  font-weight: 600;
  letter-spacing: 1px;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s ease;
}

.quick-action-btn:hover {
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 0 30px rgba(0,212,255,0.3);
  border-color: rgba(0,255,136,0.5);
}

.btn-icon {
  font-size: 1.25rem;
}

.btn-text {
  position: relative;
  z-index: 1;
}

/* 股票列表区域 */
.stock-section {
  position: relative;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.section-header h2 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #fff;
  letter-spacing: 2px;
}

.divider {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(0,212,255,0.5), transparent);
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

/* 空状态 */
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

.empty-hint {
  color: #475467;
  font-size: 0.875rem;
}

/* 股票网格 */
.stock-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.stock-card {
  position: relative;
  background: linear-gradient(135deg, rgba(15,23,42,0.9) 0%, rgba(15,23,42,0.7) 100%);
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s ease;
}

.card-border {
  position: absolute;
  inset: 0;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  pointer-events: none;
}

.stock-card:hover .card-border {
  border-color: rgba(0,212,255,0.4);
  box-shadow: inset 0 0 30px rgba(0,212,255,0.1);
}

.stock-card:hover {
  transform: translateY(-6px);
}

.card-content {
  position: relative;
  padding: 1.5rem;
}

.stock-header {
  padding-bottom: 1rem;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  margin-bottom: 1rem;
}

.stock-name {
  font-size: 1.125rem;
  font-weight: 600;
  color: #fff;
  margin-bottom: 0.25rem;
}

.stock-code {
  color: #667085;
  font-size: 0.75rem;
  letter-spacing: 1px;
  font-family: 'SF Mono', monospace;
}

.stock-body {
  margin-bottom: 1rem;
}

.stock-price {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.price {
  font-size: 1.75rem;
  font-weight: 700;
  color: #fff;
}

.change {
  font-size: 1rem;
  font-weight: 600;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
}

.change.up {
  background: rgba(0,255,136,0.1);
  color: #00ff88;
  border: 1px solid rgba(0,255,136,0.2);
}

.change.down {
  background: rgba(255,107,107,0.1);
  color: #ff6b6b;
  border: 1px solid rgba(255,107,107,0.2);
}

.stock-meta {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.meta-label {
  color: #475467;
  font-size: 0.75rem;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.meta-value {
  color: #98a2b3;
  font-size: 0.875rem;
  font-family: 'SF Mono', monospace;
}

.stock-footer {
  padding-top: 1rem;
  border-top: 1px solid rgba(255,255,255,0.06);
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  color: #00d4ff;
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 1px;
}

.action-btn .arrow {
  transition: transform 0.3s;
}

.stock-card:hover .arrow {
  transform: translateX(4px);
}
</style>
