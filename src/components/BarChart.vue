<script setup>
import { ref, onMounted, watch } from 'vue'
import { init } from '../echarts'

const props = defineProps({
  data: Array,
  xKey: { type: String, default: 'name' },
  yKey: { type: String, default: 'value' },
  color: { type: String, default: '#315f50' },
  horizontal: { type: Boolean, default: false }
})

const chartRef = ref(null)
let chart = null

const initChart = () => {
  if (!chartRef.value) return
  chart = init(chartRef.value)
  updateChart()
}

const updateChart = () => {
  if (!chart || !props.data?.length) return

  const xData = props.data.map(d => d[props.xKey])
  const yData = props.data.map(d => d[props.yKey])

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1d2924',
      borderWidth: 0,
      textStyle: { color: '#f7f5ef', fontSize: 12 },
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(49, 95, 80, 0.07)' } }
    },
    grid: {
      left: props.horizontal ? '25%' : '10%',
      right: '5%',
      bottom: '15%',
      top: '10%',
      containLabel: false
    },
    xAxis: props.horizontal ? {
      type: 'value',
      splitLine: { lineStyle: { color: '#e6e5de' } },
      axisLabel: { fontSize: 11, color: '#778079' },
      axisLine: { show: false }
    } : {
      type: 'category',
      data: xData,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#d7dad3' } },
      axisLabel: {
        fontSize: 11,
        color: '#778079',
        rotate: xData.length > 6 ? 45 : 0
      }
    },
    yAxis: props.horizontal ? {
      type: 'category',
      data: xData,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { fontSize: 11, color: '#5f6963' }
    } : {
      type: 'value',
      splitLine: { lineStyle: { color: '#e6e5de' } },
      axisLabel: { fontSize: 11, color: '#778079' },
      axisLine: { show: false }
    },
    series: [{
      type: 'bar',
      data: yData,
      itemStyle: {
        color: props.color,
        borderRadius: props.horizontal ? [0, 2, 2, 0] : [2, 2, 0, 0]
      },
      barMaxWidth: 34
    }]
  }

  chart.setOption(option)
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', () => chart?.resize())
})

watch(() => props.data, updateChart, { deep: true })
</script>

<template>
  <div ref="chartRef" style="width: 100%; height: 280px;"></div>
</template>
