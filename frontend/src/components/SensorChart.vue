<template>
  <div class="modal-overlay" @click.self="handleClose">
    <div class="modal-container">
      <div class="modal-header">
        <h3>📊 {{ cage.name }} - 历史数据</h3>
        <button class="close-btn" @click="handleClose">✕</button>
      </div>

      <div class="modal-body">
        <div class="cage-info">
          <div class="info-item">
            <span class="label">当前温度</span>
            <span class="value temp">{{ cage.temperature }}°C</span>
          </div>
          <div class="info-item">
            <span class="label">当前盐度</span>
            <span class="value salinity">{{ cage.salinity }}‰</span>
          </div>
          <div class="info-item">
            <span class="label">放置深度</span>
            <span class="value">{{ cage.depth }}m</span>
          </div>
          <div class="info-item">
            <span class="label">运行状态</span>
            <span class="value status" :class="cage.status">
              {{ statusText[cage.status] }}
            </span>
          </div>
        </div>

        <div class="time-range">
          <span class="range-label">时间范围:</span>
          <button
            v-for="r in timeRanges"
            :key="r.value"
            :class="{ active: selectedRange === r.value }"
            @click="selectRange(r.value)"
          >
            {{ r.label }}
          </button>
        </div>

        <div ref="chartRef" class="chart-container"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getCageHistory } from '../utils/api.js'

const props = defineProps({
  cage: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close'])

const chartRef = ref(null)
const selectedRange = ref(24)
let chartInstance = null

const statusText = {
  normal: '正常运行',
  warning: '警告',
  error: '故障'
}

const timeRanges = [
  { label: '6小时', value: 6 },
  { label: '12小时', value: 12 },
  { label: '24小时', value: 24 },
  { label: '48小时', value: 48 },
  { label: '72小时', value: 72 }
]

const initChart = () => {
  if (!chartRef.value) return
  chartInstance = echarts.init(chartRef.value)
  loadHistoryData()
}

const loadHistoryData = async () => {
  try {
    const data = await getCageHistory(props.cage.id, selectedRange.value)
    renderChart(data.data)
  } catch (err) {
    console.error('加载历史数据失败:', err)
  }
}

const renderChart = (data) => {
  if (!chartInstance) return

  const times = data.map(d => {
    const date = new Date(d.timestamp)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  })

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(0, 20, 40, 0.9)',
      borderColor: 'rgba(79, 195, 247, 0.5)',
      textStyle: { color: '#fff' },
      axisPointer: {
        type: 'cross',
        label: { backgroundColor: '#1976d2' }
      }
    },
    legend: {
      data: ['温度 (°C)', '盐度 (‰)'],
      textStyle: { color: '#b0bec5' },
      top: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '12%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: times,
      axisLine: { lineStyle: { color: '#37474f' } },
      axisLabel: { color: '#78909c', fontSize: 11 }
    },
    yAxis: [
      {
        type: 'value',
        name: '温度 (°C)',
        position: 'left',
        axisLine: { lineStyle: { color: '#ef5350' } },
        axisLabel: { color: '#78909c', fontSize: 11 },
        splitLine: { lineStyle: { color: 'rgba(55, 71, 79, 0.5)' } }
      },
      {
        type: 'value',
        name: '盐度 (‰)',
        position: 'right',
        axisLine: { lineStyle: { color: '#29b6f6' } },
        axisLabel: { color: '#78909c', fontSize: 11 },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '温度 (°C)',
        type: 'line',
        yAxisIndex: 0,
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        showSymbol: false,
        data: data.map(d => d.temperature),
        lineStyle: { color: '#ef5350', width: 2 },
        itemStyle: { color: '#ef5350' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(239, 83, 80, 0.3)' },
            { offset: 1, color: 'rgba(239, 83, 80, 0.02)' }
          ])
        }
      },
      {
        name: '盐度 (‰)',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        showSymbol: false,
        data: data.map(d => d.salinity),
        lineStyle: { color: '#29b6f6', width: 2 },
        itemStyle: { color: '#29b6f6' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(41, 182, 246, 0.3)' },
            { offset: 1, color: 'rgba(41, 182, 246, 0.02)' }
          ])
        }
      }
    ]
  }

  chartInstance.setOption(option)
}

const selectRange = (hours) => {
  selectedRange.value = hours
  loadHistoryData()
}

const handleClose = () => {
  emit('close')
}

const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize()
  }
}

let currentCageId = null

watch(() => props.cage, (newCage) => {
  if (newCage && newCage.id !== currentCageId) {
    currentCageId = newCage.id
    if (chartInstance) {
      loadHistoryData()
    }
  }
})

onMounted(() => {
  currentCageId = props.cage ? props.cage.id : null
  nextTick(() => {
    initChart()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  currentCageId = null
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-container {
  background: linear-gradient(135deg, #0d2137 0%, #1a3a5c 100%);
  border-radius: 12px;
  width: 700px;
  max-width: 90vw;
  max-height: 85vh;
  overflow: hidden;
  border: 1px solid rgba(79, 195, 247, 0.3);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(0, 30, 60, 0.5);
  border-bottom: 1px solid rgba(79, 195, 247, 0.3);
}

.modal-header h3 {
  color: #4fc3f7;
  font-size: 16px;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  color: #90a4ae;
  font-size: 18px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.3s;
}

.close-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.modal-body {
  padding: 20px;
}

.cage-info {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.info-item {
  background: rgba(25, 118, 210, 0.2);
  padding: 12px;
  border-radius: 8px;
  text-align: center;
}

.info-item .label {
  display: block;
  font-size: 12px;
  color: #78909c;
  margin-bottom: 6px;
}

.info-item .value {
  display: block;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.info-item .value.temp {
  color: #ef5350;
}

.info-item .value.salinity {
  color: #29b6f6;
}

.info-item .value.status.normal {
  color: #4caf50;
}

.info-item .value.status.warning {
  color: #ff9800;
}

.info-item .value.status.error {
  color: #f44336;
}

.time-range {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.range-label {
  font-size: 13px;
  color: #90a4ae;
  margin-right: 4px;
}

.time-range button {
  padding: 5px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(79, 195, 247, 0.3);
  color: #b0bec5;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.3s;
}

.time-range button:hover {
  background: rgba(79, 195, 247, 0.2);
  color: #fff;
}

.time-range button.active {
  background: #1976d2;
  color: #fff;
  border-color: #1976d2;
}

.chart-container {
  width: 100%;
  height: 320px;
}
</style>
