<template>
  <div
    class="detection-card"
    @click="toggleZoom"
    :class="{ zoomed: isZoomed }"
  >
    <!-- 왼쪽 이미지 영역 -->
    <div class="card-left">
      <img v-if="imageSrc && !error" :src="imageSrc" alt="Graph" />
      <div v-else-if="loading" class="loading">로딩 중...</div>
      <div v-else-if="error" class="error">이미지 로딩 실패</div>
    </div>

    <!-- 오른쪽 설명 영역 -->
    <div class="card-right">
      <h3 style="font-size:40px;">{{ title }}</h3>
      <p>{{ description || " " }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from "vue";

const props = defineProps({
  title: { type: String, required: true },
  description: { type: String, default: "" },
  imgUrl: { type: String, required: true },
  refreshInterval: { type: Number, default: 10000 } // ms
});

const isZoomed = ref(false);
const imageSrc = ref(null);
const loading = ref(false);
const error = ref(false);
let intervalId = null;

// ObjectURL 관리
let currentBlobUrl = null;

async function fetchImage() {
  if (!props.imgUrl) return;

  loading.value = true;
  error.value = false;

  try {
    // PNG를 직접 fetch
    const res = await fetch(`${props.imgUrl}?t=${Date.now()}`, { mode: "cors" });
    if (!res.ok) throw new Error("이미지 fetch 실패");

    const blob = await res.blob();

    // 기존 ObjectURL 해제
    if (currentBlobUrl) URL.revokeObjectURL(currentBlobUrl);

    currentBlobUrl = URL.createObjectURL(blob);
    imageSrc.value = currentBlobUrl;
  } catch (err) {
    console.error("[DetectionCard ERROR]", err);
    error.value = true;
  } finally {
    loading.value = false;
  }
}

const toggleZoom = () => {
  isZoomed.value = !isZoomed.value;
};

onMounted(() => {
  fetchImage();
  if (props.refreshInterval > 0) {
    intervalId = setInterval(fetchImage, props.refreshInterval);
  }
});

onBeforeUnmount(() => {
  if (intervalId) clearInterval(intervalId);
  if (currentBlobUrl) URL.revokeObjectURL(currentBlobUrl);
});

// URL 변경 시 새로 fetch
watch(() => props.imgUrl, () => fetchImage());
</script>


<style scoped>
.detection-card {
  display: flex;
  flex-direction: row;
  gap: 20px;
  background-color: #111;
  border-radius: 12px;
  padding: 16px;
  color: #fff;
  cursor: pointer;
  width: 100%;
  max-width: 100%;
  box-shadow: 0 2px 6px rgba(0,0,0,0.4);
  transition: all 0.3s ease;
}

.card-left {
  flex: 2;
  overflow: hidden;
  max-width: 0;
  opacity: 0;
  transition: max-width 0.5s ease, opacity 0.5s ease;
}

.detection-card.zoomed .card-left {
  max-width: 120%;
  opacity: 1;
}

.card-left img {
  width: 100%;
  height: auto;
  border-radius: 8px;
}

.card-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-top: 2rem;
  margin-bottom: 2rem;
  color: #e5e5e5;
}

.card-right h3 {
  margin: 0 0 10px 0;
  font-size: 2rem;
}

.card-right p {
  margin: 0;
  font-size: 1.6rem;
}

.detection-card.zoomed {
  position: fixed;
  top: 60%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 95vw;
  height: auto;
  z-index: 9999;
  box-shadow: 0 5px 32px rgba(0,0,0,0.8);
  border-radius: 16px;
  background-color: #111;
}

.detection-card.zoomed img {
  width: 100%;
  object-fit: contain;
}

/* 반응형 */
@media (max-width: 1300px) {
  .detection-card {
    flex-direction: column;
  }
  .card-right {
    margin-top: 16px;
  }
}

.loading {
  color: #ccc;
  text-align: center;
}

.error {
  color: red;
  text-align: center;
}
</style>
