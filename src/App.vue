<script setup>
import { onMounted, ref, computed } from 'vue'
import { loadGeoData, useGeoData } from './composables/useGeoData'
import StatsCard from './components/StatsCard.vue'
import PieChart from './components/PieChart.vue'
import BarChart from './components/BarChart.vue'
import DataTable from './components/DataTable.vue'
import StudyTable from './components/StudyTable.vue'

const viewMode = ref('study')

const {
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
  yearStats,
  averageCompleteness
} = useGeoData()

onMounted(loadGeoData)

const statsCards = computed(() => [
  {
    title: '独立研究',
    value: totalStudies.value,
    icon: 'Collection',
    color: '#1f4b3f'
  },
  {
    title: 'GEO 数据集',
    value: totalDatasets.value,
    icon: 'Document',
    color: '#496a5d'
  },
  {
    title: '直接老化证据',
    value: primaryDatasetCount.value,
    icon: 'DataAnalysis',
    color: '#9a6a42'
  },
  {
    title: '名义样本数',
    value: nominalSamples.value.toLocaleString(),
    icon: 'Connection',
    color: '#747f76'
  }
])
</script>

<template>
  <div class="site-shell min-h-screen">
    <header class="page-header">
      <div class="page-header__inner">
        <div class="brand-mark" aria-hidden="true">SA</div>
        <div class="page-header__copy">
          <div class="eyebrow">NCBI GEO · RESEARCH-GRADE CURATION V2</div>
          <h1>Skin Aging GEO Dataset Explorer</h1>
          <p>以 Study Family 与 GSE 双层组织皮肤老化、光老化和细胞衰老组学证据</p>
        </div>
        <div class="update-status">
          <span class="update-status__dot"></span>
          Rule-curated · Daily sync
        </div>
      </div>
    </header>

    <div v-if="loading" class="flex items-center justify-center py-20">
      <el-icon class="is-loading text-4xl text-brand"><Loading /></el-icon>
      <span class="ml-3 text-gray-500">加载双层策展数据中...</span>
    </div>

    <div v-else-if="error" class="px-8 py-20 text-center">
      <el-result icon="error" title="数据加载失败" :sub-title="error">
        <template #extra>
          <el-button type="primary" @click="loadGeoData()">重试</el-button>
        </template>
      </el-result>
    </div>

    <main v-else class="content-shell">
      <section class="section-intro">
        <div>
          <div class="eyebrow">CURATED EVIDENCE OVERVIEW</div>
          <h2>研究数据概览</h2>
        </div>
        <p>Study Family 用于折叠同一论文下的 SuperSeries、SubSeries 与多组学 GSE</p>
      </section>

      <section class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatsCard
          v-for="card in statsCards"
          :key="card.title"
          v-bind="card"
        />
      </section>

      <div class="scope-note mb-6">
        <strong>统计口径：</strong>
        “独立研究”按 PMID、Series relation 和规范化标题归并；“名义样本数”是各 GSE
        的 Sample_Count 之和，尚未跨 GSE/GSM 去重。当前关键元数据平均完整度为
        {{ averageCompleteness }}%。
      </div>

      <section class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div class="chart-container">
          <div class="chart-kicker">STUDY TIMELINE</div>
          <div class="chart-title">独立研究提交趋势</div>
          <BarChart :data="yearStats" xKey="name" yKey="value" color="#315f50" />
        </div>

        <div class="chart-container">
          <div class="chart-kicker">PRIMARY AGING DOMAINS</div>
          <div class="chart-title">GSE 主主题分层</div>
          <PieChart :data="scopeStats" />
        </div>
      </section>

      <section class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div class="chart-container">
          <div class="chart-kicker">MODALITIES</div>
          <div class="chart-title">组学类型分布</div>
          <BarChart :data="dataTypeStats" xKey="name" yKey="value" color="#6e887a" horizontal />
        </div>

        <div class="chart-container">
          <div class="chart-kicker">ORGANISMS</div>
          <div class="chart-title">物种分布</div>
          <BarChart :data="organismStats" xKey="name" yKey="value" color="#a8754e" horizontal />
        </div>
      </section>

      <section>
        <div class="section-intro section-intro--table">
          <div>
            <div class="eyebrow">CURATED CATALOGUE</div>
            <h2>{{ viewMode === 'study' ? 'Study Family 目录' : 'GSE 数据集目录' }}</h2>
          </div>
          <div class="view-switch" role="group" aria-label="目录视图切换">
            <button :class="{ active: viewMode === 'study' }" @click="viewMode = 'study'">
              研究视图 · {{ studyFamilies.length }}
            </button>
            <button :class="{ active: viewMode === 'dataset' }" @click="viewMode = 'dataset'">
              GSE 视图 · {{ geoData.length }}
            </button>
          </div>
        </div>

        <StudyTable
          v-if="viewMode === 'study'"
          :studies="studyFamilies"
          :datasets="geoData"
        />
        <DataTable v-else :data="geoData" />
      </section>
    </main>

    <footer class="page-footer">
      <p>Data source: NCBI Gene Expression Omnibus · Schema v2.0</p>
      <p>Deterministic relevance rules + versioned human adjudication · AI summaries only</p>
    </footer>
  </div>
</template>
