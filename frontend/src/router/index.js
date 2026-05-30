import { createRouter, createWebHashHistory } from 'vue-router'
import Home from '../views/Home.vue'
import StockDetail from '../views/StockDetail.vue'
import DataViewer from '../views/DataViewer.vue'
import Backtest from '../views/Backtest.vue'
import PortfolioBacktest from '../views/PortfolioBacktest.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/stock/:code',
    name: 'StockDetail',
    component: StockDetail
  },
  {
    path: '/data-viewer',
    name: 'DataViewer',
    component: DataViewer
  },
  {
    path: '/backtest',
    name: 'Backtest',
    component: Backtest
  },
  {
    path: '/portfolio-backtest',
    name: 'PortfolioBacktest',
    component: PortfolioBacktest
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
