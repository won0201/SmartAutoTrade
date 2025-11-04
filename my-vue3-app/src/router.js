import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import RiskAnalysis from '../pages/RiskAnalysis.vue'
import AssetList from '../pages/AssetList.vue'

const routes = [
  { path: '/', name: 'Home', component: HomePage },
  { path: '/assets', name: 'AssetList', component: AssetList },
  { path: '/risk-analysis', name: 'RiskAnalysis', component: RiskAnalysis },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router