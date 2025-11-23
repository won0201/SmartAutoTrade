import RiskAnalysis from './pages/RiskAnalysis.vue'
import AssetList from './pages/AssetList.vue'
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'RiskAnalysis', component: RiskAnalysis }, // 홈 페이지
  { path: '/assets', name: 'AssetList', component: AssetList },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router