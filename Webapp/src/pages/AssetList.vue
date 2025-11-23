<template>
  <div class="asset-container">
    <h2>자산 분류 트리</h2>
    <div class="tree-container">
      <ul class="tree-root">
        <li v-for="(group, initial) in groupedAssets" :key="initial">
          <div class="tree-initial">{{ initial }}</div>
          <ul>
            <li v-for="(item, index) in sortedGroup(group)" :key="item.Code" class="tree-item">
              <span class="item-text">{{ item.Name }} ({{ item.Code }})</span>
              <span v-if="index < group.length - 1" class="arrow">→</span>
            </li>
          </ul>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'

const assets = ref([])
const sortAsc = ref(true)

onMounted(async () => {
  const res = await fetch("http://13.211.78.215:2026")
  assets.value = await res.json()
})

function getInitial(name) {
  const firstChar = name?.[0]
  if (!firstChar) return '#'
  const code = firstChar.charCodeAt(0)
  if (code >= 0xAC00 && code <= 0xD7A3) {
    const initials = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
    return initials[Math.floor((code - 0xAC00) / 588)]
  }
  return firstChar.toUpperCase()
}

const groupedAssets = computed(() => {
  const groups = {}
  assets.value.forEach(item => {
    const initial = getInitial(item.Name)
    if (!groups[initial]) groups[initial] = []
    groups[initial].push(item)
  })
  return Object.fromEntries(Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0])))
})

function sortedGroup(group) {
  return [...group].sort((a, b) => {
    const nameA = a.Name?.toUpperCase() || ''
    const nameB = b.Name?.toUpperCase() || ''
    return sortAsc.value ? nameA.localeCompare(nameB) : nameB.localeCompare(nameA)
  })
}
</script>

<style>
/* 전체 컨테이너 */
.asset-container {
  padding: 20px;
  font-family: 'Nexon Lv2 Gothic', sans-serif;
  background-color: #000000;
  color: #FFFFFF;
}

/* 헤더 */
.asset-container h2 {
  font-size: 100px; /* 헤더 고정 크기 */
  margin-bottom: 20px;
}

/* 트리 초성 */
.tree-initial {
  font-weight: 700;
  font-size: 50px;
  margin-top: 12px;
  color: #FFD700;
}

/* 링크드리스트 스타일 (배경 없음, 테두리 없음) */
.tree-item {
  display: inline-flex;
  align-items: center;
  margin-right: 8px;
  font-size: 40px; /* 아이템 고정 크기 */
  padding: 2px 4px;
  background-color: transparent;
  border: none;
  color: #FFFFFF;
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.2s, transform 0.2s;
}

.tree-item:hover {
  color: #3498db; /* 호버 시 파란색 */
  transform: translateY(-1px);
}

/* 화살표 */
.arrow {
  margin: 0 5px;
  color: #FFD700;
  font-weight: bold;
  vertical-align: middle;
}

/* 요약 박스 */
.summary-box {
  background-color: #333333;
  color: #FFFFFF;
  padding: 8px 12px;
  border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.4);
  margin-bottom: 10px;
}

.tree-initial-wrapper {
  display: flex;
  align-items: center;
  gap: 12px; /* 초성과 동그라미 사이 간격 */
  margin-top: 12px;
}

.circle {
  width: 60px;       /* 동그라미 크기 */
  height: 60px;
  border-radius: 50%;
  background-color: #FFD700; /* 동그라미 색상 */
}
</style>
