import { createRouter, createWebHashHistory } from 'vue-router'
import Home from '../views/Home.vue'
import StockDetail from '../views/StockDetail.vue'
import DataViewer from '../views/DataViewer.vue'
import Backtest from '../views/Backtest.vue'

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
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router