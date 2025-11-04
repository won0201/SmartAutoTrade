<template>
  <div class="asset-container">
    <h2>자산 리스트</h2>
    <table class="asset-table">
      <thead>
        <tr>
          <th>Code</th>
          <th @click="sortByName" class="sortable">
            Name
            <span v-if="sortAsc">▲</span>
            <span v-else>▼</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in sortedAssets" :key="item.Code">
          <td>{{ item.Code }}</td>
          <td>{{ item.Name }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const assets = ref([])
const sortAsc = ref(true)

onMounted(async () => {
  const res = await fetch('http://localhost:8080/assets')
  assets.value = await res.json()
})

const sortedAssets = computed(() => {
  return [...assets.value].sort((a, b) => {
    const nameA = a.Name?.toUpperCase() || ''
    const nameB = b.Name?.toUpperCase() || ''
    return sortAsc.value
      ? nameA.localeCompare(nameB)
      : nameB.localeCompare(nameA)
  })
})

function sortByName() {
  sortAsc.value = !sortAsc.value
}
</script>

<style scoped>
.asset-container {
  padding: 20px;
  font-family: 'Nexon Lv2 Gothic', sans-serif;
}

.asset-table {
  width: 100%;
  border-collapse: collapse;
}

.asset-table th {
  border: 1px solid #ccc;
  padding: 8px 12px;
  text-align: left;
   font-family: 'Nexon Lv1 Gothic', sans-serif;
}

.asset-table td {
  border: 1px solid #ccc;
  padding: 8px 12px;
  text-align: left;
   font-family: 'Nexon Lv2 Gothic', sans-serif;
}

.asset-table th.sortable {
  cursor: pointer;
  background-color: rgba(227, 203, 48, 0.87);
  user-select: none;
}

.asset-table th.sortable:hover {
  background-color: #e0e0e0;
}
</style>