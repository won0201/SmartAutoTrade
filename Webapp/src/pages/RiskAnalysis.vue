<template>
  <div class="asset-page">
    <div class="page-header">
      <h1>Risk Analysis</h1>
      <button class="home-btn" @click="goHome">🏠 홈으로</button>
    </div>

    <div class="fixed-widget">
      <AssetWidget />
    </div>

    <div class="main-content">
      <div class="accordion-container">
        <div v-for="(chart, i) in charts" :key="chart.name" class="accordion-item">
          <div class="accordion-header" @click="toggleAccordion(i)">
            <span>{{ chart.name }}</span>
            <span>{{ chart.open ? '▲' : '▼' }}</span>
          </div>

          <!-- v-show 사용 -->
          <div class="accordion-body" v-show="chart.open">
            <PortfolioOptimization
              v-if="chart.name === 'Portfolio Optimization Result'"
              :url="chart.url"
              :refreshInterval="10000"
            />

            <ESplot
              v-if="chart.name === '시계열 조건부 변동성(ES) 그래프'"
              :title="chart.name"
              :url="chart.url"
              :refreshInterval="10000"
            />

            <div v-if="chart.name === 'Z-score 위험 알림'">
              <table class="risk-table">
                <thead>
                  <tr>
                    <th>Asset</th>
                    <th>Z-score</th>
                    <th>Score</th>
                    <th>Level</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="messages.length === 0">
                    <td colspan="5">데이터 없음</td>
                  </tr>
                  <tr v-for="(msg, index) in messages" :key="msg.asset + msg.Date + index">
                    <td>{{ msg.asset || '-' }}</td>
                    <td>{{ msg.Zscore != null ? msg.Zscore.toFixed(2) : '-' }}</td>
                    <td>{{ msg.Score != null ? msg.Score.toFixed(1) : '-' }}</td>
                    <td :class="msg.LevelClass || 'level-Normal'">{{ msg.Level || '-' }}</td>
                    <td>{{ msg.Date || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

          </div>
        </div>
      </div>

      <div class="cards-container">
        <DetectionCard
          v-for="card in graphCards"
          :key="card.title"
          :title="card.title"
          :imgUrl="card.url"
          :refreshInterval="10000"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";

import AssetWidget from "../components/AssetWidget.vue";
import ESplot from "../components/ESplot.vue";
import PortfolioOptimization from "../components/Portplot.vue";
import DetectionCard from "../components/DetectionCard.vue";

const router = useRouter();
const goHome = () => router.push("/");

// charts 배열
const charts = ref([
  { name: "Portfolio Optimization Result", url: "http://13.211.78.215:2025/optimize/plot", open: true },
  { name: "시계열 조건부 변동성(ES) 그래프", url: "http://13.211.78.215:2025/es_cutoff_all", open: true },
  { name: "Z-score 위험 알림", url: null, open: true },
]);

const toggleAccordion = (index) => {
  charts.value[index].open = !charts.value[index].open;
};

// 이상치 그래프 카드
const graphCards = ref([
  { title: "SVM Asset Anomaly Detection", url: "http://13.211.78.215:2025/svm/plot/svm_iso" },
  { title: "ANN Asset Anomaly Detection", url: "http://13.211.78.215:2025/ann/plot/ann_iso" },
]);

// WebSocket 상태
const messages = ref([]);
let ws = null;

onMounted(() => {
  ws = new WebSocket("ws://13.211.78.215:2025/ws/alerts");

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      const newMessages = Array.isArray(data) ? data : [data];
      messages.value = [...newMessages, ...messages.value].slice(0, 20);
    } catch (err) {
      console.error("WS 파싱 오류:", err);
    }
  };
});

onBeforeUnmount(() => {
  if (ws && ws.readyState === WebSocket.OPEN) ws.close();
});
</script>


<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";

// 컴포넌트 import
import AssetWidget from "../components/AssetWidget.vue";
import ESplot from "../components/ESplot.vue";
import PortfolioOptimization from "../components/Portplot.vue";
import DetectionCard from "../components/DetectionCard.vue";

// 라우터
const router = useRouter();
const goHome = () => router.push("/");

// --------------------
// 아코디언 차트 상태
// --------------------
const charts = ref([
  { name: "Portfolio Optimization Result", url: "http://13.211.78.215:2026/optimize/plot", open: true },
  { name: "시계열 조건부 변동성(ES) 그래프", url: "http://13.211.78.215:2026/es_cutoff_all", open: true },
  { name: "Z-score 위험 알림", url: null, open: true },
]);

const toggleAccordion = (index) => {
  charts.value[index].open = !charts.value[index].open;
};

// --------------------
// 이상치 그래프 카드 상태
// --------------------
const graphCards = ref([
  { title: "SVM Asset Anomaly Detection", url: "http://13.211.78.215:2026/svm/plot/svm_iso" },
  { title: "ANN Asset Anomaly Detection", url: "http://13.211.78.215:2026/ann/plot/ann_iso" },
]);

// --------------------
// Z-score WebSocket 상태
// --------------------
const messages = ref([]);
let ws = null;

onMounted(() => {
  ws = new WebSocket("ws://13.211.78.215:2026/ws/alerts");

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      const newMessages = Array.isArray(data) ? data : [data];
      messages.value = [...newMessages, ...messages.value].slice(0, 20);
    } catch (err) {
      console.error("WS 파싱 오류:", err);
    }
  };
});

onBeforeUnmount(() => {
  if (ws && ws.readyState === WebSocket.OPEN) ws.close();
});
</script>

<style scoped>
.asset-page {
  padding: 1rem;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.accordion-container {
  margin-top: 1rem;
}
.accordion-item {
  border: 1px solid #ccc;
  margin-bottom: 0.5rem;
  border-radius: 8px;
}
.accordion-header {
  padding: 0.5rem;
  cursor: pointer;
  background-color: #f5f5f5;
  display: flex;
  justify-content: space-between;
}
.accordion-body {
  padding: 0.5rem;
}
.cards-container {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-top: 1rem;
}

.asset-page { padding: 2rem; background-color: #000; color: #fff; min-height: 100vh; font-family: "Nexon Lv2 Gothic", sans-serif; }
.fixed-widget { position: fixed; top: 80px; right: 15rem; width: 650px; z-index: 1000; background: rgba(20,20,20,0.9); padding: 1rem; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; background: rgba(0,0,0,0.6); backdrop-filter: blur(10px); padding: 1rem 2rem; font-size: 5rem; border-radius: 0 0 20px 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
.home-btn { position: fixed; top: 20px; left: 20px; display: flex; align-items: center; gap: 8px; padding: 10px 22px; background: rgba(255,255,255,0.08); border-radius: 14px; color: #e0e0e0; font-weight: 600; font-size: 30px; cursor: pointer; }
.accordion-container { display: flex; flex-direction: column; gap: 3rem; }
.accordion-item { border-radius: 12px; overflow: hidden; background: rgba(30,30,30,0.85); box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
.accordion-header { padding: 1rem; cursor: pointer; display: flex; justify-content: space-between; align-items: center; font-weight: 600; font-size: 4rem; background: rgba(50,50,50,0.95); }
.accordion-body { padding: 1rem; text-align: center; background: rgba(20,20,20,0.9); }
.accordion-body img { width: 100%; border-radius: 12px; }
.risk-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 3rem; background-color: #0A0A0A; color: #E5E5E5; border-radius: 8px; }
.risk-table th, .risk-table td { padding: 10px 12px; text-align: center; }
.risk-table th { background-color: #002e5f; color: #fff; font-weight: 600; text-transform: uppercase; }
.risk-table td.level-High { color: #FF4C4C; font-weight: bold; }
.risk-table td.level-Warning { color: #FFA500; font-weight: bold; }
.risk-table td.level-Normal { color: #4CAF50; }
.cards-container { display: flex; gap: 2rem; margin-top: 2rem; flex-wrap: wrap; justify-content: center; width: 100%; }
</style>
