<script setup>
import { ref, onMounted, watch } from 'vue'
import { init } from '../echarts'

const props = defineProps({
  data: Array
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

  const colors = ['#315f50', '#6e887a', '#a8754e', '#b5a078', '#74808a', '#8d6f69', '#9aa39a', '#c4c0b2']

  chart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
      backgroundColor: '#1d2924',
      borderWidth: 0,
      textStyle: { color: '#f7f5ef', fontSize: 12 }
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: {
        fontSize: 12,
        color: '#5f6963'
      }
    },
    series: [
      {
        type: 'pie',
        radius: ['48%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 2,
          borderColor: '#fbfaf6',
          borderWidth: 3
        },
        label: {
          show: false
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        data: props.data.map((d, i) => ({
          value: d.value,
          name: d.name,
          itemStyle: { color: colors[i % colors.length] }
        }))
      }
    ]
  })
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
