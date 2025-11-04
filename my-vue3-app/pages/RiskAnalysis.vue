<template>
  <div class="risk-container">
    <h1>리스크 분석 페이지</h1>

    <!-- 홈으로 돌아가기 -->
    <button @click="goHome" class="btn">🏠 홈으로 돌아가기</button>

    <!-- 1️⃣ 리스크 요약 정보 -->
    <section class="section">
      <h2>Risk Summary</h2>
      <p>주요 지표 (ES, 샤프지수, Z-score)</p>
      <div class="summary-box">
        <ul>
          <li>📉 ES(Expected Shortfall, Volatility): {{ summary.expected }}</li>
          <li>⚖️ 샤프 지수(Sharpe Ratio): {{ summary.sharpe }}</li>
          <li>📘 표준화 점수(Z-score): {{ summary.zscore }}</li>
        </ul>
      </div>
    </section>

    <!-- 2️⃣ 포트폴리오 최적화 그래프 -->
    <section class="section">
      <h2 style="margin-top: 2em;">Portfolio Optimization</h2>
      <div class="chart-placeholder">
        <div v-if="plotUrl">
          <img :src="plotUrl" alt="최적화 결과 그래프" />
        </div>
        <div v-else>
          <p>📈 리스크 지표 차트</p>
          <p>📊 포트폴리오 구성표</p>
          <p>그래프가 여기에 표시됩니다 (예: Chart.js, Recharts 등)</p>
        </div>
      </div>
    </section>

    <!-- 3️⃣ 자산별 ES 그래프 -->
    <section class="section">
      <h2 style="margin-top: 3em;">자산별 ES(CVAR) 그래프</h2>
      <button class="btn" @click="toggleGraph" style="background-color: #ffffff; color: #030000;">
        {{ graphVisible ? '그래프 닫기' : '그래프 불러오기' }}
      </button>
      <img v-if="graphVisible && graphUrl" :src="graphUrl" alt="ES 그래프" />
    </section>

    <!-- 4️⃣ 실시간 리스크 알림 -->
    <section class="section">
      <h2 style="margin-top: 2em;">실시간 리스크 알림</h2>
      <ul>
        <li v-for="msg in messages" :key="msg.asset + msg.timestamp">
          [{{ msg.level }}] {{ msg.asset }} | Z={{ msg.z }} | Score={{ msg.score }}
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { useRouter } from "vue-router"

// ✅ 상태 변수
const summary = ref({
  expected: "0.02",
  sharpe: "1.42",
  zscore: "3"
})

const plotUrl = ref(null)
const graphUrl = ref(null)
const graphVisible = ref(false)
const messages = ref([])

// 🚀 라우터
const router = useRouter()

// 🏠 홈으로 이동
function goHome() {
  router.push("/")
}

// 📊 그래프 토글 및 로딩
function toggleGraph() {
  graphVisible.value = !graphVisible.value
  if (graphVisible.value && !graphUrl.value) {
    graphUrl.value = "http://localhost:8080/plot/es_cutoff_all"
  }
}


// 📈 포트폴리오 최적화 그래프 불러오기
onMounted(() => {
  fetch("http://localhost:8080/optimize/plot")
    .then(res => res.json())
    .then(data => {
      plotUrl.value = data.image
    })
    .catch(err => {
      console.error("그래프 로딩 실패:", err)
    })
})

// 🔄 WebSocket 실시간 리스크 알림 수신
onMounted(() => {
  const ws = new WebSocket("ws://localhost:8085/ws/alerts")

  ws.onopen = () => console.log(" WebSocket 연결 성공")
  ws.onclose = () => console.log(" WebSocket 연결 종료")
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    messages.value.unshift(data)
    if (messages.value.length > 20) messages.value.pop()
  }
})
</script>

<style scoped>
body {
  background-color: #030000;
  color: #f5f5f5;
  font-family: "Nexon Lv1 Gothic OTF Medium", sans-serif;
}

.risk-container {
  max-width: 800px;
  margin-bottom: 40px;
  margin-top:  80px;
  background-color: #1a1a1a;
  padding: 30px;
  border-radius: 10px;
  box-shadow: 0 0 20px rgba(0,0,0,0.7);
}

.section {
  margin-top: 20px;
  padding: 15px;
  background: #111;
  border-radius: 8px;
}

.summary-box {
  background: #222;
  color:white;
  padding: 10px;
  border-radius: 6px;
}

.btn {
  background-color: #03346E;
  color: #fff;
  border: none;
  padding: 8px 18px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 10px;
  transition: 0.2s;
}

.btn:hover {
  background-color: #02295C;
}

.chart-placeholder {
  background-color: #0d0d0d;
  color: #999;
  border: 1px dashed #333;
  padding: 30px;
  border-radius: 8px;
  text-align: center;
}

ul {
  list-style-type: none;
  padding: 0;
}

li {
  margin: 6px 0;
  font-size: 15px;
}
</style>

<style>
.risk-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
  font-family: "Nexon Lv2 Gothic", sans-serif;
  font-color: white;
}

.btn {
  background: rgb(3, 52, 110);
  color: white;
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  text-align: center;
  font-family: "Nexon Lv2 Gothic OTF Gothic", sans-serif;
}

.btn:hover {
  background: #43a047;
}

.section {
  margin-top: 32px;
}

.summary-box {
  margin-top: 5px;
  margin-bottom: 100px;
  background: #f9f9f9;
  color: #1a1a1a;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 0 8px rgba(0, 0, 0, 0.05);
}

.chart-placeholder {
  background: #e9eef7;
  margin-top: 50px;
  height: 250px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #555;
  font-family: "Nexon Lv1 Gothic", sans-serif;
  position: relative;
}

img {
  max-width: 100%;
  border-radius: 8px;
  border: 1px solid #ccc;
}

.risk-alerts ul {
  list-style: none;
  padding: 0;
  margin-bottom: 100px;
  font-family: "Nexon Lv1 Gothic OTF Gothic", sans-serif;
}

.risk-alerts li {
  padding: 0.25rem 0;
  border-bottom: 80px solid #eee;
  font-family: "Nexon Lv1 Gothic OTF Gothic", sans-serif;
}
</style>