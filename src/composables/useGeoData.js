import { ref, computed } from 'vue'

const geoData = ref([])
const loading = ref(true)
const error = ref(null)

// 加载数据
export async function loadGeoData() {
  try {
    loading.value = true
    const response = await fetch('./data/geo_data.json')
    if (!response.ok) throw new Error('Failed to load data')
    geoData.value = await response.json()
    loading.value = false
  } catch (e) {
    error.value = e.message
    loading.value = false
  }
}

export function useGeoData() {
  // 基础统计
  const totalDatasets = computed(() => geoData.value.length)

  const totalSamples = computed(() =>
    geoData.value.reduce((sum, d) => sum + (parseInt(d.Sample_Count) || 0), 0)
  )

  // 物种分布
  const organismStats = computed(() => {
    const counts = {}
    geoData.value.forEach(d => {
      const org = d.Organism || 'Unknown'
      counts[org] = (counts[org] || 0) + 1
    })
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
  })

  // 数据类型分布
  const dataTypeStats = computed(() => {
    const counts = {}
    geoData.value.forEach(d => {
      const types = (d.Data_Type || 'Other').split(';').map(t => t.trim())
      types.forEach(type => {
        if (type) counts[type] = (counts[type] || 0) + 1
      })
    })
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
  })

  const scopeStats = computed(() => {
    const counts = {}
    geoData.value.forEach(d => {
      const scope = d.Scope_Category || 'other'
      counts[scope] = (counts[scope] || 0) + 1
    })
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
  })

  // 国家分布
  const countryStats = computed(() => {
    const counts = {}
    geoData.value.forEach(d => {
      const country = d.Country || 'Unknown'
      if (country && country !== 'Unknown') {
        counts[country] = (counts[country] || 0) + 1
      }
    })
    return Object.entries(counts)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
  })

  // 年份分布
  const yearStats = computed(() => {
    const counts = {}
    geoData.value.forEach(d => {
      const date = d.Submission_Date || ''
      const year = date.split('/')[0] || 'Unknown'
      if (year && year !== 'Unknown') {
        counts[year] = (counts[year] || 0) + 1
      }
    })
    return Object.entries(counts)
      .map(([name, value]) => ({ name: parseInt(name), value }))
      .filter(d => !isNaN(d.name))
      .sort((a, b) => a.name - b.name)
  })

  // 唯一国家数
  const uniqueCountries = computed(() =>
    new Set(geoData.value.map(d => d.Country).filter(c => c && c !== 'Unknown')).size
  )

  // 唯一物种数
  const uniqueOrganisms = computed(() =>
    new Set(geoData.value.map(d => d.Organism).filter(o => o)).size
  )

  return {
    geoData,
    loading,
    error,
    totalDatasets,
    totalSamples,
    organismStats,
    dataTypeStats,
    scopeStats,
    countryStats,
    yearStats,
    uniqueCountries,
    uniqueOrganisms
  }
}
