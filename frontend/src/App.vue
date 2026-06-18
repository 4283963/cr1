<template>
  <div class="app-container">
    <div class="header">
      <h1>🌊 海洋牧场水下设备监控系统</h1>
      <div class="header-info">
        <span class="status-text">在线网箱: {{ cages.length }} 个</span>
        <span class="update-time">最后更新: {{ lastUpdateTime }}</span>
        <button class="refresh-btn" @click="fetchData">手动刷新</button>
      </div>
    </div>

    <div class="main-content">
      <Ocean3D :cages="cages" @cage-click="handleCageClick" />

      <div class="side-panel">
        <h3>网箱列表</h3>
        <div class="cage-list">
          <div
            v-for="cage in cages"
            :key="cage.id"
            class="cage-item"
            :class="[cage.status, { active: selectedCage && selectedCage.id === cage.id }]"
            @click="handleCageClick(cage)"
          >
            <div class="cage-name">{{ cage.name }}</div>
            <div class="cage-data">
              <span>🌡️ {{ cage.temperature }}°C</span>
              <span>🧂 {{ cage.salinity }}‰</span>
            </div>
            <div class="cage-depth">深度: {{ cage.depth }}m</div>
          </div>
        </div>

        <div class="legend">
          <h4>状态图例</h4>
          <div class="legend-item"><span class="dot normal"></span> 正常</div>
          <div class="legend-item"><span class="dot warning"></span> 警告</div>
          <div class="legend-item"><span class="dot error"></span> 故障</div>
        </div>
      </div>
    </div>

    <SensorChart
      v-if="selectedCage"
      :cage="selectedCage"
      @close="selectedCage = null"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import Ocean3D from './components/Ocean3D.vue'
import SensorChart from './components/SensorChart.vue'
import { getCages } from './utils/api.js'

const cages = ref([])
const selectedCage = ref(null)
const lastUpdateTime = ref('--')
let refreshTimer = null
let isFetching = false

const fetchData = async () => {
  if (isFetching) return
  isFetching = true
  try {
    const data = await getCages()
    cages.value = data

    if (selectedCage.value) {
      const updated = data.find(c => c.id === selectedCage.value.id)
      if (updated) {
        selectedCage.value = { ...updated }
      }
    }

    const now = new Date()
    lastUpdateTime.value = now.toLocaleTimeString('zh-CN')
  } catch (err) {
    console.error('获取数据失败:', err)
  } finally {
    isFetching = false
  }
}

const handleCageClick = (cage) => {
  selectedCage.value = cage
}

onMounted(() => {
  fetchData()
  refreshTimer = setInterval(fetchData, 10000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.app-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #0a1628 0%, #1a3a5c 100%);
  color: #fff;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: rgba(0, 20, 40, 0.8);
  border-bottom: 1px solid rgba(0, 150, 255, 0.3);
  z-index: 10;
}

.header h1 {
  font-size: 20px;
  font-weight: 600;
  color: #4fc3f7;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 20px;
  font-size: 14px;
}

.status-text {
  color: #81c784;
}

.update-time {
  color: #90a4ae;
}

.refresh-btn {
  padding: 6px 16px;
  background: #1976d2;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.3s;
}

.refresh-btn:hover {
  background: #1565c0;
}

.main-content {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
}

.side-panel {
  width: 280px;
  background: rgba(0, 20, 40, 0.7);
  border-left: 1px solid rgba(0, 150, 255, 0.3);
  padding: 16px;
  overflow-y: auto;
  z-index: 5;
}

.side-panel h3 {
  font-size: 16px;
  margin-bottom: 12px;
  color: #4fc3f7;
  border-bottom: 1px solid rgba(0, 150, 255, 0.3);
  padding-bottom: 8px;
}

.cage-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cage-item {
  padding: 12px;
  background: rgba(25, 118, 210, 0.2);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  border-left: 3px solid transparent;
}

.cage-item:hover {
  background: rgba(25, 118, 210, 0.4);
  transform: translateX(4px);
}

.cage-item.active {
  background: rgba(25, 118, 210, 0.5);
  border-left-color: #4fc3f7;
}

.cage-item.normal {
  border-left-color: #4caf50;
}

.cage-item.warning {
  border-left-color: #ff9800;
}

.cage-item.error {
  border-left-color: #f44336;
}

.cage-name {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 6px;
}

.cage-data {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #b0bec5;
  margin-bottom: 4px;
}

.cage-depth {
  font-size: 11px;
  color: #78909c;
}

.legend {
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid rgba(0, 150, 255, 0.3);
}

.legend h4 {
  font-size: 13px;
  margin-bottom: 10px;
  color: #90a4ae;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #b0bec5;
  margin-bottom: 6px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.dot.normal {
  background: #4caf50;
}

.dot.warning {
  background: #ff9800;
}

.dot.error {
  background: #f44336;
}
</style>
