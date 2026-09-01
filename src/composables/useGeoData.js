import { ref, computed } from 'vue'

const geoData = ref([])
const studyFamilies = ref([])
const loading = ref(true)
const error = ref(null)

export async function loadGeoData() {
  try {
    loading.value = true
    error.value = null
    const [datasetResponse, studyResponse] = await Promise.all([
      fetch('./data/geo_data.json'),
      fetch('./data/study_families.json')
    ])
    if (!datasetResponse.ok || !studyResponse.ok) {
      throw new Error('Failed to load curated dataset or study-family data')
    }
    const [datasets, studies] = await Promise.all([
      datasetResponse.json(),
      studyResponse.json()
    ])
    geoData.value = datasets.filter(d => (d.Curation_Status || 'active') === 'active')
    studyFamilies.value = studies
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const countValues = (records, getter) => {
  const counts = {}
  records.forEach(record => {
    const raw = getter(record)
    const values = Array.isArray(raw) ? raw : [raw]
    values.filter(Boolean).forEach(value => {
      counts[value] = (counts[value] || 0) + 1
    })
  })
  return Object.entries(counts)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
}

const scopeLabels = {
  intrinsic_skin_aging: '内源性皮肤老化',
  photoaging: '光老化',
  cellular_senescence: '细胞衰老',
  rejuvenation_intervention: '年轻化干预',
  aged_skin_repair: '老化皮肤修复',
  skin_appendage_aging: '附属器老化'
}

export function useGeoData() {
  const totalStudies = computed(() => studyFamilies.value.length)
  const totalDatasets = computed(() => geoData.value.length)
  const primaryDatasetCount = computed(() =>
    geoData.value.filter(d => d.Dataset_Role === 'primary').length
  )
  const nominalSamples = computed(() =>
    geoData.value.reduce((sum, d) => sum + (parseInt(d.Sample_Count) || 0), 0)
  )

  const organismStats = computed(() =>
    countValues(geoData.value, d => d.Organism || 'Unknown')
  )
  const dataTypeStats = computed(() =>
    countValues(geoData.value, d => d.Data_Type || 'Other')
  )
  const scopeStats = computed(() =>
    countValues(geoData.value, d => d.Primary_Scope_Category || d.Scope_Category || 'other')
      .map(item => ({ ...item, name: scopeLabels[item.name] || item.name }))
  )
  const contextStats = computed(() =>
    countValues(geoData.value, d => d.Aging_Contexts || [])
  )
  const yearStats = computed(() => {
    const counts = {}
    studyFamilies.value.forEach(d => {
      const year = parseInt((d.Submission_Date || '').split('/')[0])
      if (!isNaN(year)) counts[year] = (counts[year] || 0) + 1
    })
    return Object.entries(counts)
      .map(([name, value]) => ({ name: parseInt(name), value }))
      .sort((a, b) => a.name - b.name)
  })

  const averageCompleteness = computed(() => {
    if (!geoData.value.length) return 0
    const total = geoData.value.reduce(
      (sum, d) => sum + (parseInt(d.Metadata_Completeness) || 0), 0
    )
    return Math.round(total / geoData.value.length)
  })

  return {
    geoData,
    studyFamilies,
    loading,
    error,
    totalStudies,
    totalDatasets,
    primaryDatasetCount,
    nominalSamples,
    organismStats,
    dataTypeStats,
    scopeStats,
    contextStats,
    yearStats,
    averageCompleteness
  }
}
