<script setup>
import { onMounted, ref, computed } from 'vue'
import { loadGeoData, useGeoData } from './composables/useGeoData'
import StatsCard from './components/StatsCard.vue'
import PieChart from './components/PieChart.vue'
import BarChart from './components/BarChart.vue'
import DataTable from './components/DataTable.vue'

const {
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
} = useGeoData()

onMounted(() => {
  loadGeoData()
})

// 统计卡片数据
const statsCards = computed(() => [
  {
    title: '数据集总数',
    value: totalDatasets.value,
    icon: 'Document',
    color: '#1f4b3f'
  },
  {
    title: '样本总数',
    value: totalSamples.value.toLocaleString(),
    icon: 'DataAnalysis',
    color: '#496a5d'
  },
  {
    title: '物种数',
    value: uniqueOrganisms.value,
    icon: 'Connection',
    color: '#9a6a42'
  },
  {
    title: '国家/地区',
    value: uniqueCountries.value,
    icon: 'Location',
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
          <div class="eyebrow">NCBI GEO · CURATED RESEARCH INDEX</div>
          <h1>Skin Aging GEO Dataset Explorer</h1>
          <p>皮肤老化、光老化与细胞衰老相关组学数据集 · 两阶段规则策展</p>
        </div>
        <div class="update-status">
          <span class="update-status__dot"></span>
          Daily sync
        </div>
      </div>
    </header>

    <div v-if="loading" class="flex items-center justify-center py-20">
      <el-icon class="is-loading text-4xl text-brand"><Loading /></el-icon>
      <span class="ml-3 text-gray-500">加载数据中...</span>
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
          <div class="eyebrow">DATA OVERVIEW</div>
          <h2>研究数据概览</h2>
        </div>
        <p>覆盖转录组、单细胞、空间组学、甲基化及染色质可及性数据</p>
      </section>

      <section class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatsCard
          v-for="card in statsCards"
          :key="card.title"
          :title="card.title"
          :value="card.value"
          :icon="card.icon"
          :color="card.color"
        />
      </section>

      <section class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div class="chart-container">
          <div class="chart-kicker">TIMELINE</div>
          <div class="chart-title">数据集提交趋势</div>
          <BarChart :data="yearStats" xKey="name" yKey="value" color="#315f50" />
        </div>

        <div class="chart-container">
          <div class="chart-kicker">AGING DOMAINS</div>
          <div class="chart-title">皮肤老化主题分层</div>
          <PieChart :data="scopeStats" />
        </div>
      </section>

      <section class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div class="chart-container">
          <div class="chart-kicker">MODALITIES</div>
          <div class="chart-title">数据类型分布</div>
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
            <div class="eyebrow">DATASET CATALOGUE</div>
            <h2>数据集目录</h2>
          </div>
          <p>按老化主题、数据类型和物种筛选，并展开查看原始实验设计</p>
        </div>
        <DataTable :data="geoData" />
      </section>
    </main>

    <footer class="page-footer">
      <p>Data source: NCBI Gene Expression Omnibus</p>
      <p>Daily two-stage rule curation · No AI relevance review</p>
    </footer>
  </div>
</template>
