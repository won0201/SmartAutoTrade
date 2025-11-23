<template>
  <div class="plot-container">
    <h3>{{ title }}</h3>

    <div v-if="loading">그래프 로딩 중...</div>
    <div v-if="error" class="error">이미지 로딩 실패</div>

    <!-- 항상 DOM 존재, fetch 완료 후 src 지정 -->
    <img v-show="url" :src="imageSrc" :alt="title" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from "vue";

const props = defineProps({
  title: String,
  url: String,
  refreshInterval: Number
});

const imageSrc = ref(null);
const loading = ref(false);
const error = ref(false);
let intervalId = null;

async function fetchImage() {
  if (!props.url) return;

  loading.value = true;
  error.value = false;

  try {
    const res = await fetch(props.url);
    if (!res.ok) throw new Error(`fetch 실패: ${res.status}`);

    const blob = await res.blob();
    if (imageSrc.value) URL.revokeObjectURL(imageSrc.value);
    imageSrc.value = URL.createObjectURL(blob);

  } catch (err) {
    console.error("[Portplot ERROR]", err);
    error.value = true;
  } finally {
    loading.value = false;
  }
}

onMounted(fetchImage);

if (props.refreshInterval && props.refreshInterval > 0) {
  intervalId = setInterval(fetchImage, props.refreshInterval);
}

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId);
  if (imageSrc.value) URL.revokeObjectURL(imageSrc.value);
});

watch(() => props.url, fetchImage);
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
