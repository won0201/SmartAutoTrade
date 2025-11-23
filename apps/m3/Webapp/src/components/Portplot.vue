<template>
  <div class="plot-container">
    <h3>{{ title }}</h3>

    <div v-if="loading">그래프 로딩 중...</div>
    <div v-if="error" class="error">이미지 로딩 실패</div>

    <img v-if="imageSrc && !error" :src="imageSrc" :alt="title" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from "vue";

const props = defineProps({
  title: String,
  url: String,           // 반드시 서버 PNG URL 전달
  refreshInterval: Number // optional, ms 단위
});

const imageSrc = ref(null);
const loading = ref(false);
const error = ref(false);
let intervalId = null;

async function fetchImage() {
  if (!props.url) {
    console.warn("ESPlot: URL이 제공되지 않음.");
    return;
  }

  loading.value = true;
  error.value = false;

  try {
    const res = await fetch(props.url);

    if (!res.ok) throw new Error(`이미지 fetch 실패: ${res.status}`);

    const blob = await res.blob();              // JSON이 아닌 PNG blob
    imageSrc.value = URL.createObjectURL(blob); // Object URL 생성
  } catch (err) {
    console.error("[ESPlot ERROR]", err);
    error.value = true;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchImage();

  if (props.refreshInterval && props.refreshInterval > 0) {
    intervalId = setInterval(fetchImage, props.refreshInterval);
  }
});

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId);
});

// URL 변경 시 자동 갱신
watch(() => props.url, () => fetchImage());
</script>

<style scoped>
.plot-container {
  text-align: center;
  margin: 1rem 0;
}
img {
  max-width: 100%;
  height: auto;
}
.error {
  color: red;
}
</style>
