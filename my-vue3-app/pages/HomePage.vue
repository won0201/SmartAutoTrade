<template>
  <div class="container">
    <h1>자산 조회</h1>

    <!-- 검색 영역 -->
    <div class="search">
      <input v-model="assetInput" placeholder="종목 이름 (코드로 조회 시 앞부분 0 생략 후 입력)" />
      <select v-model="period">
        <option value="1M">1개월</option>
        <option value="3M">3개월</option>
        <option value="6M">6개월</option>
        <option value="1Y">1년</option>
      </select>
      <div class="button-group">
        <button @click="fetchAssetPrices">조회</button>
        <button @click="goToAssetList">종목 리스트</button>
        <button @click="goToRiskPage">리스크 분석</button>
      </div>
    </div>

    <!-- 로딩 / 상태 메시지 -->
    <p v-if="loadingMessage">{{ loadingMessage }}</p>

   <!-- 결과 테이블 -->
<div v-if="assets.length" class="table-container">
  <table class="home-table">
    <thead>
      <tr>
        <th>Date</th>
        <th>Name</th>
        <th>Code</th>
        <th>Open</th>
        <th>High</th>
        <th>Low</th>
        <th>Close</th>
        <th>Volume</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(item, idx) in filteredByPeriod" :key="idx">
        <td>{{ formatDate(item.Date) }}</td>
        <td>{{ item.Name }}</td>
        <td>{{ item.Code }}</td>
        <td>{{ item.Open }}</td>
        <td>{{ item.High }}</td>
        <td>{{ item.Low }}</td>
        <td>{{ item.Close }}</td>
        <td>{{ item.Volume }}</td>
      </tr>
    </tbody>
  </table>
</div>

    <p v-if="assets.length && filteredByPeriod.length === 0">
       조회하시오...
    </p>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const assetInput = ref("");
const period = ref("1M");
const assets = ref([]);
const loadingMessage = ref("");

// 서버에서 전체 자산 가격 가져오기 후 입력값 기준 필터
function fetchAssetPrices() {
  if (!assetInput.value.trim()) {
    loadingMessage.value = "\u00A0종목  코드 또는 이름을 입력하시오.";
    return;
  }

loadingMessage.value = "\u00A0데이터 조회 중...";

  fetch("http://localhost:8080/assets/prices")
    .then(res => res.json())
    .then(data => {
      assets.value = data.filter(
        item =>
          String(item.Code) === assetInput.value.trim() ||
          item.Name.includes(assetInput.value.trim())
      );
      if (assets.value.length === 0) {
        loadingMessage.value = "\u00A0해당 종목 데이터를 준비중입니다...";
      } else {
        loadingMessage.value = "";
      }
    })
    .catch(err => {
      console.error(err);
      loadingMessage.value = "\u00A0데이터 조회 중 오류 발생";
    });
}
// 기간 필터링
const filteredByPeriod = computed(() => {
  if (!assets.value.length) return [];
  const today = new Date();
  let startDate = new Date();
  switch (period.value) {
    case "1M":
      startDate.setMonth(today.getMonth() - 1);
      break;
    case "3M":
      startDate.setMonth(today.getMonth() - 3);
      break;
    case "6M":
      startDate.setMonth(today.getMonth() - 6);
      break;
    case "1Y":
      startDate.setFullYear(today.getFullYear() - 1);
      break;
    default:
      startDate.setMonth(today.getMonth() - 1);
  }
  return assets.value.filter(item => new Date(item.Date) >= startDate);
});

// 날짜 포맷팅
function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString();
}

// 라우터 이동
function goToAssetList() {
  router.push({ name: "AssetList", query: { symbol: assetInput.value, period: period.value } });
}

// 리스크 분석 페이지 이동
function goToRiskPage() {
  router.push({ name: "RiskAnalysis" });
}
</script>

<style>
/* body 및 container: 가운데 정렬 + 동적 크기 */
body {
  background-color: #030000;
  color: #f5f5f5;
  padding-top: 10px;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  font-family: "Nexon Lv1 Gothic OTF Medium", sans-serif;
  font-size: 17px;
}

.container {
  background-color: #1a1a1a;
  padding: 30px 20px;
  width: 100%;       /* 화면에 맞춰 동적 조절 */
  max-width: 500px; /* 최대 넓이 */
  max-height: 300px;
  border-radius: 10px;
  box-shadow: 0 0 20px rgba(0,0,0,0.7);
  box-sizing: border-box;
  margin-top: 5px;
    font-family: "Nexon Lv2 Gothic", sans-serif;
  font-size: 10px;
    position: relative;;
}

/* 입력창, 셀렉트 박스: 반응형 */
input, select {
  padding: 8px;
  margin-bottom: 10px;
  border-radius: 4px;
  font-size: 15px;
  border: 1px solid #ffffff33;
  background-color: #1a1a1a;
  color: #f5f5f5;
  width: 100%;           /* 화면에 맞게 늘어남 */
  max-width: 100%;       /* 부모 폭에 맞춤 */
  box-sizing: border-box;
    font-family: "Nexon Lv2 Gothic", sans-serif;
}

/* 버튼 그룹 */
.button-group {
  display: flex;
  flex-wrap: wrap;        /* 화면 좁으면 줄 바꿈 */
  gap: 10px;
  justify-content: flex-start;
  margin-top: 10px;
  font-family: "Nexon Lv2 Gothic", sans-serif;
}

.button-group button {
  background-color: #03346E;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 16px;
  flex: 11 auto;        /* 버튼이 동일 너비로 확장 */
  min-width: 120px;      /* 너무 작아지지 않도록 최소 너비 */
  font-family: "Nexon Lv1 Gothic", sans-serif;
}

.button-group button:hover {
  background-color: #02295C;
}

/* 테이블: 반응형 스크롤 */
.home-table {
  position: absolute;
  top: 160px;
  left: -60px;
  width: 100%;
  border-collapse: collapse;
  margin-top: 110px;
  table-layout: auto;
}


thead th, tbody td {
  padding: 8px;
  border: 1px solid #444;
  text-align: center;
  font-size: 14px;
}

tbody td:nth-child(1) {
  min-width: 90px;
  cursor: pointer;
}
tbody td:nth-child(2) {
  min-width: 80px;
  cursor: pointer;
}


h1 {
  margin-top: 5px;
  font-size: 24px;
}


table-wrapper {
  overflow-x: auto; /* 화면 좁으면 가로 스크롤 */
}

</style>