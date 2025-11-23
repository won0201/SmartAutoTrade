<template>
  <div class="asset-widget-container">
    <h3>자산 조회</h3>

    <!-- 검색 영역 -->
    <div class="search">
      <input
        v-model="assetInput"
        placeholder="종목 이름"
      />
      <select v-model="period">
        <option value="1M">1개월</option>
        <option value="3M">3개월</option>
        <option value="6M">6개월</option>
        <option value="1Y">1년</option>
      </select>
      <div class="button-group">
        <button @click="fetchAssetPrices">조회</button>
        <button @click="goToAssetList">종목 리스트</button>
      </div>
    </div>

    <!-- 로딩 / 상태 메시지 -->
    <p v-if="loadingMessage" class="loading-text">{{ loadingMessage }}</p>

    <!-- 결과 테이블 -->
    <div v-if="showTable" class="table-container">
      <div class="table-header">
        <h3> &nbsp;조회 결과</h3>
        <button class="close-btn" @click="closeTable">✕</button>
      </div>

      <div class="table-scroll">
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

      <!-- 기간 필터 후 데이터 없을 때 메시지 -->
      <p v-if="filteredByPeriod.length === 0">
        조회 결과가 없습니다.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";

// props로 기본값 전달
const props = defineProps({
  defaultSymbol: { type: String, default: "" },
  defaultPeriod: { type: String, default: "1M" },
});

const router = useRouter();
const assetInput = ref(props.defaultSymbol);
const period = ref(props.defaultPeriod);
const assets = ref([]);
const loadingMessage = ref("");
const showTable = ref(false);

// 서버에서 전체 자산 가격 가져오기 후 입력값 기준 필터
function fetchAssetPrices() {
  if (!assetInput.value.trim()) {
    loadingMessage.value = "\u00A0종목 코드 또는 이름을 입력하시오.";
    showTable.value = false;
    return;
  }

  loadingMessage.value = "\u00A0";

  fetch("http://13.211.78.215:2025/assets/prices")
    .then((res) => res.json())
    .then((data) => {
      assets.value = data.filter(
        (item) =>
          String(item.Code) === assetInput.value.trim() ||
          item.Name.includes(assetInput.value.trim())
      );
      if (assets.value.length === 0) {
        loadingMessage.value = "\u00A0해당 종목 데이터를 준비중입니다...";
        showTable.value = false;
      } else {
        loadingMessage.value = "";
        showTable.value = true;
      }
    })
    .catch((err) => {
      console.error(err);
      loadingMessage.value = "\u00A0데이터 조회 중 오류 발생";
      showTable.value = false;
    });
}

// x 버튼 클릭 시 테이블 닫기
function closeTable() {
  showTable.value = false;
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
  return assets.value.filter((item) => new Date(item.Date) >= startDate);
});

// 날짜 포맷팅
function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString();
}

// 라우터 이동
function goToAssetList() {
  router.push({
    name: "AssetList",
    query: { symbol: assetInput.value, period: period.value },
  });
}

</script>
<style>

/* 부모 요소 제약 제거 */
.parent-element {
  width: 10vw; /* 뷰포트 너비로 설정 */
}


.asset-widget-container {
  border: 1px solid #2C2C2C;
  font-size: 45px;
  border-radius: 14px;
  width: 100%;
  max-width: 2400px;
  padding: 50px 50px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  text-align: center;
  min-height: 400px;
  transform: none; /* transform 속성 제거 */
}

/* 검색창 & 버튼 */
input,
select {
  background: #0f0f0f;
  border: 1px solid #333;
  border-radius: 8px;
  color: #E5E5E5;
  font-size: 30px;
  padding: 14px;
  width: 100%;
  margin-top: 5px;
  margin-bottom: 10px;
  box-sizing: border-box;
  box-shadow: inset 0 0 5px rgba(255, 255, 255, 0.05);
}

input:focus,
select:focus {
  outline: none;
  border-color: #0077ff;
  box-shadow: 0 0 8px rgba(0, 119, 255, 0.4);
}

.button-group {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 20px;
  margin-bottom: 50px;
  justify-content: center;
}

.button-group button {
  flex: 1;
  background: linear-gradient(180deg, #004C97 0%, #002C5C 100%);
  color: #fff;
  border: none;
  border-radius: 6px;
  padding: 12px 18px;
  font-size: 27px;
  font-weight: 600;
  cursor: pointer;
}

.button-group button:hover {
  background: linear-gradient(180deg, #0059b3 0%, #003366 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(0, 100, 255, 0.3);
}

/* 테이블 */
.table-container {
  position: relative;
  font-size: 30px;
  background-color: #0A0A0A;
  color: #f5f5f5;
  padding: 16px;
  border-radius: 12px;
  max-height: 400px;
  overflow-y: auto;
  overflow-x: hidden;
  border: 2px solid transparent;
  background-clip: padding-box;
  box-shadow: 0 0 15px rgba(0, 120, 255, 0.5);
  border-image: linear-gradient(135deg, #0077ff, #00d4ff) 1;
  margin-right: 300px;
}

.table-container::-webkit-scrollbar {
  width: 15px;
}

.table-container::-webkit-scrollbar-track {
  background: #0A0A0A;
  border-radius: 6px;
}

.table-container::-webkit-scrollbar-thumb {
  background-color: #ffffff80;
  border-radius: 6px;
}

.table-container::-webkit-scrollbar-thumb:hover {
  background-color: #ffffffaa;
}

.table-header {
  display: flex;
  font-size: 40px;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2px;
}

.home-table {
  width: 100%;
  border-collapse: collapse;
  background-color: #101010;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 20px;
}

.home-table th,
.home-table td {
  padding: 8px 12px;
  text-align: center;
  border-bottom: 1px solid #2a2a2a;
}

.home-table th {
  background-color: #131314;
  color: #fff;
  position: sticky;
  top: 0;
  z-index: 2;
}

tbody tr:hover {
  background-color: #1c1c1c;
  transition: 0.2s;
}

.close-btn {
  background: transparent;
  border: none;
  color: #fff;
  font-size: 50px;
  cursor: pointer;
}

.loading-text {
  font-size:  35px;
  color: #E5E5E5;
  text-align: center;
  margin-top: 10px;
}


</style>
