<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  data: Array
})

// 筛选条件
const searchText = ref('')
const selectedOrganism = ref('')
const selectedDataType = ref('')
const selectedScope = ref('')
const selectedCountry = ref('')

// 展开的行
const expandedRows = ref([])

// 获取筛选选项
const organisms = computed(() => {
  const set = new Set(props.data?.map(d => d.Organism).filter(Boolean))
  return Array.from(set).sort()
})

const dataTypes = computed(() => {
  const set = new Set()
  props.data?.forEach(d => {
    (d.Data_Type || '').split(';').forEach(t => {
      const trimmed = t.trim()
      if (trimmed) set.add(trimmed)
    })
  })
  return Array.from(set).sort()
})

const countries = computed(() => {
  const set = new Set(props.data?.map(d => d.Country).filter(Boolean))
  return Array.from(set).sort()
})

const scopes = computed(() => {
  const set = new Set(props.data?.map(d => d.Scope_Category).filter(Boolean))
  return Array.from(set).sort()
})

const scopeLabels = {
  intrinsic_skin_aging: '内源性皮肤老化',
  photoaging: '光老化',
  cellular_senescence: '细胞衰老',
  rejuvenation_intervention: '年轻化干预',
  aged_skin_repair: '老化皮肤修复',
  skin_appendage_aging: '皮肤附属器老化'
}

const formatScope = (scope) => scopeLabels[scope] || scope || 'Other'

// 筛选后的数据
const filteredData = computed(() => {
  if (!props.data) return []

  return props.data.filter(item => {
    // 搜索文本
    if (searchText.value) {
      const search = searchText.value.toLowerCase()
      const matchTitle = item.Title?.toLowerCase().includes(search)
      const matchSummary = item.Summary?.toLowerCase().includes(search)
      const matchAccession = item.Accession?.toLowerCase().includes(search)
      if (!matchTitle && !matchSummary && !matchAccession) return false
    }

    // 物种筛选
    if (selectedOrganism.value && item.Organism !== selectedOrganism.value) {
      return false
    }

    // 数据类型筛选
    if (selectedDataType.value) {
      const types = (item.Data_Type || '').split(';').map(t => t.trim())
      if (!types.includes(selectedDataType.value)) return false
    }

    if (selectedScope.value && item.Scope_Category !== selectedScope.value) {
      return false
    }

    // 国家筛选
    if (selectedCountry.value && item.Country !== selectedCountry.value) {
      return false
    }

    return true
  })
})

// 切换行展开
const toggleExpand = (row) => {
  const index = expandedRows.value.indexOf(row.Accession)
  if (index > -1) {
    expandedRows.value.splice(index, 1)
  } else {
    expandedRows.value.push(row.Accession)
  }
}

const isExpanded = (row) => expandedRows.value.includes(row.Accession)

// 清除筛选
const clearFilters = () => {
  searchText.value = ''
  selectedOrganism.value = ''
  selectedDataType.value = ''
  selectedScope.value = ''
  selectedCountry.value = ''
}

// 格式化数据类型显示
const formatDataType = (type) => {
  const colorMap = {
    'bulk RNA-seq': '#315f50',
    'scRNA-seq': '#6e887a',
    'spatial transcriptomics': '#a8754e',
    'DNA methylation': '#8d6f69',
    'scATAC-seq': '#74808a',
    'ATAC-seq': '#596978',
    'ChIP/CUT&RUN': '#7e655f',
    'expression microarray': '#8c7654',
    'miRNA/ncRNA profiling': '#826f8d'
  }
  return colorMap[type] || '#747f76'
}

// 打开GEO链接
const openGeoLink = (url) => {
  window.open(url, '_blank')
}
</script>

<template>
  <div class="data-table">
    <div class="filter-bar flex flex-wrap items-center gap-4">
      <el-input
        v-model="searchText"
        placeholder="搜索标题、摘要或 Accession"
        :prefix-icon="Search"
        clearable
        class="w-64"
      />

      <el-select v-model="selectedOrganism" placeholder="物种" clearable class="w-36">
        <el-option
          v-for="org in organisms"
          :key="org"
          :label="org"
          :value="org"
        />
      </el-select>

      <el-select v-model="selectedDataType" placeholder="数据类型" clearable class="w-44">
        <el-option
          v-for="type in dataTypes"
          :key="type"
          :label="type"
          :value="type"
        />
      </el-select>

      <el-select v-model="selectedScope" placeholder="老化主题" clearable class="w-44">
        <el-option
          v-for="scope in scopes"
          :key="scope"
          :label="formatScope(scope)"
          :value="scope"
        />
      </el-select>

      <el-select v-model="selectedCountry" placeholder="国家/地区" clearable class="w-36">
        <el-option
          v-for="country in countries"
          :key="country"
          :label="country"
          :value="country"
        />
      </el-select>

      <el-button @click="clearFilters" :icon="RefreshLeft">重置</el-button>

      <div class="result-count ml-auto">
        <strong>{{ filteredData.length }}</strong>
        <span>/ {{ data?.length || 0 }} datasets</span>
      </div>
    </div>

    <el-table
      :data="filteredData"
      stripe
      style="width: 100%"
      :row-class-name="({ row }) => isExpanded(row) ? 'expanded-row' : ''"
    >
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="detail-panel mx-4">
            <div class="ai-summary-card mb-4">
              <div class="label">相关性依据</div>
              <div class="content">
                {{ row.Relevance_Final_Reason || row.Relevance_Reason }}
              </div>
            </div>

            <div v-if="row.AI_Summary_CN" class="ai-summary-card mb-4">
              <div class="label">
                <el-icon><MagicStick /></el-icon>
                AI 辅助摘要
              </div>
              <div class="content">{{ row.AI_Summary_CN }}</div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div class="detail-section">
                  <div class="label">Summary</div>
                  <div class="value">{{ row.Summary }}</div>
                </div>

                <div class="detail-section" v-if="row.Overall_Design">
                  <div class="label">Overall Design</div>
                  <div class="value">{{ row.Overall_Design }}</div>
                </div>
              </div>

              <div>
                <div class="detail-section">
                  <div class="label">Platform</div>
                  <div class="value">{{ row.Platform || 'N/A' }}</div>
                </div>

                <div class="detail-section">
                  <div class="label">Lab / Institute</div>
                  <div class="value">{{ row.Lab || 'N/A' }} @ {{ row.Institute || 'N/A' }}</div>
                </div>

                <div class="detail-section">
                  <div class="label">Contributors</div>
                  <div class="value">{{ row.Contributors || 'N/A' }}</div>
                </div>

                <div class="detail-section">
                  <div class="label">Supplementary Size</div>
                  <div class="value">{{ row.Supplementary_Size || 'N/A' }}</div>
                </div>

                <div class="detail-section" v-if="row.PubMed_IDs">
                  <div class="label">PubMed</div>
                  <div class="value">
                    <a
                      v-for="id in row.PubMed_IDs.split(';')"
                      :key="id"
                      :href="`https://pubmed.ncbi.nlm.nih.gov/${id.trim()}`"
                      target="_blank"
                      class="text-blue-500 hover:underline mr-2"
                    >
                      {{ id.trim() }}
                    </a>
                  </div>
                </div>

                <div class="mt-4">
                  <el-button
                    type="primary"
                    :icon="Link"
                    @click="openGeoLink(row.GEO_Link)"
                  >
                    打开 GEO 页面
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="Accession" label="Accession" width="120" sortable>
        <template #default="{ row }">
          <a
            :href="row.GEO_Link"
            target="_blank"
            class="text-blue-500 hover:underline font-medium"
          >
            {{ row.Accession }}
          </a>
        </template>
      </el-table-column>

      <el-table-column prop="Title" label="Title" min-width="300">
        <template #default="{ row }">
          <div class="line-clamp-2">{{ row.Title }}</div>
        </template>
      </el-table-column>

      <el-table-column prop="Organism" label="Organism" width="130">
        <template #default="{ row }">
          <el-tag :type="row.Organism === 'Homo sapiens' ? 'primary' : 'success'" size="small">
            {{ row.Organism === 'Homo sapiens' ? 'Human' : 'Mouse' }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="Scope_Category" label="Aging Domain" width="150">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">
            {{ formatScope(row.Scope_Category) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="Data_Type" label="Data Type" width="180">
        <template #default="{ row }">
          <div class="flex flex-wrap gap-1">
            <el-tag
              v-for="type in (row.Data_Type || '').split(';').map(t => t.trim()).filter(Boolean)"
              :key="type"
              size="small"
              :style="{ backgroundColor: formatDataType(type) + '12', color: formatDataType(type), borderColor: formatDataType(type) + '30' }"
            >
              {{ type }}
            </el-tag>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="Sample_Count" label="Samples" width="100" sortable align="center">
        <template #default="{ row }">
          <span class="font-medium">{{ row.Sample_Count }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="Country" label="Country" width="100" />

      <el-table-column prop="Submission_Date" label="Date" width="110" sortable />
    </el-table>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

:deep(.el-table__expanded-cell) {
  padding: 0 !important;
  background-color: #f7f6f1;
}

:deep(.expanded-row) {
  background-color: #f2f5f1 !important;
}
</style>
