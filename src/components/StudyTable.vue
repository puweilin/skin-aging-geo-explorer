<script setup>
import { ref, computed } from 'vue'
import { RefreshLeft, Search } from '@element-plus/icons-vue'

const props = defineProps({
  studies: { type: Array, default: () => [] },
  datasets: { type: Array, default: () => [] }
})

const searchText = ref('')
const selectedTier = ref('')
const selectedContext = ref('')
const selectedDataType = ref('')
const selectedOrganism = ref('')

const labels = {
  intrinsic_skin_aging: '内源性皮肤老化',
  photoaging: '光老化',
  cellular_senescence: '细胞衰老',
  rejuvenation_intervention: '年轻化干预',
  aged_skin_repair: '老化皮肤修复',
  skin_appendage_aging: '附属器老化',
  exposome_aging: '外暴露老化',
  premature_aging_model: '早老模型'
}
const formatLabel = value => labels[value] || value

const contexts = computed(() =>
  Array.from(new Set(props.studies.flatMap(s => s.Aging_Contexts || []))).sort()
)
const dataTypes = computed(() =>
  Array.from(new Set(props.studies.flatMap(s => s.Data_Types || []))).sort()
)
const organisms = computed(() =>
  Array.from(new Set(props.studies.flatMap(s => s.Organisms || []))).sort()
)
const datasetById = computed(() =>
  Object.fromEntries(props.datasets.map(dataset => [dataset.Accession, dataset]))
)

const filteredStudies = computed(() => props.studies.filter(study => {
  if (searchText.value) {
    const query = searchText.value.toLowerCase()
    const haystack = [
      study.Study_Family_ID,
      study.Title,
      ...(study.Related_GSEs || []),
      ...(study.PubMed_IDs || [])
    ].join(' ').toLowerCase()
    if (!haystack.includes(query)) return false
  }
  if (selectedTier.value && study.Evidence_Tier !== selectedTier.value) return false
  if (selectedContext.value && !(study.Aging_Contexts || []).includes(selectedContext.value)) return false
  if (selectedDataType.value && !(study.Data_Types || []).includes(selectedDataType.value)) return false
  if (selectedOrganism.value && !(study.Organisms || []).includes(selectedOrganism.value)) return false
  return true
}))

const relatedDatasets = study =>
  (study.Related_GSEs || []).map(id => datasetById.value[id]).filter(Boolean)

const clearFilters = () => {
  searchText.value = ''
  selectedTier.value = ''
  selectedContext.value = ''
  selectedDataType.value = ''
  selectedOrganism.value = ''
}
</script>

<template>
  <div class="data-table">
    <div class="filter-bar flex flex-wrap items-center gap-4">
      <el-input
        v-model="searchText"
        placeholder="研究标题、Study ID、GSE 或 PMID"
        :prefix-icon="Search"
        clearable
        class="w-64"
      />

      <el-select v-model="selectedTier" placeholder="范围层级" clearable class="w-36">
        <el-option label="Core" value="core" />
        <el-option label="Extension" value="extension" />
      </el-select>

      <el-select v-model="selectedContext" placeholder="老化情境" clearable class="w-44">
        <el-option v-for="value in contexts" :key="value" :label="formatLabel(value)" :value="value" />
      </el-select>

      <el-select v-model="selectedDataType" placeholder="组学类型" clearable class="w-44">
        <el-option v-for="value in dataTypes" :key="value" :label="value" :value="value" />
      </el-select>

      <el-select v-model="selectedOrganism" placeholder="物种" clearable class="w-44">
        <el-option v-for="value in organisms" :key="value" :label="value" :value="value" />
      </el-select>

      <el-button @click="clearFilters" :icon="RefreshLeft">重置</el-button>

      <div class="result-count ml-auto">
        <strong>{{ filteredStudies.length }}</strong>
        <span>/ {{ studies.length }} studies</span>
      </div>
    </div>

    <el-table :data="filteredStudies" stripe style="width: 100%">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="detail-panel mx-4">
            <div class="study-summary-grid">
              <div class="detail-section">
                <div class="label">老化情境</div>
                <div class="tag-stack">
                  <el-tag v-for="value in row.Aging_Contexts" :key="value" size="small">
                    {{ formatLabel(value) }}
                  </el-tag>
                </div>
              </div>
              <div class="detail-section">
                <div class="label">数据覆盖</div>
                <div class="value">
                  {{ row.Dataset_Count }} 个 GSE；{{ row.Primary_Dataset_Count }} 个 primary；
                  {{ row.Nominal_Sample_Total }} 个名义样本<br>
                  <span class="text-gray-500">{{ row.Sample_Count_Interpretation }}</span>
                </div>
              </div>
            </div>

            <div class="label mb-1">相关 GSE</div>
            <div class="study-related-list">
              <div v-for="dataset in relatedDatasets(row)" :key="dataset.Accession" class="study-related-item">
                <div>
                  <a :href="dataset.GEO_Link" target="_blank" class="text-blue-500 hover:underline font-medium">
                    {{ dataset.Accession }}
                  </a>
                  <span class="related-title">{{ dataset.Title }}</span>
                </div>
                <div class="tag-stack">
                  <el-tag size="small" :type="dataset.Dataset_Role === 'primary' ? 'success' : 'info'">
                    {{ dataset.Dataset_Role }}
                  </el-tag>
                  <el-tag size="small" effect="plain">{{ dataset.Data_Type }}</el-tag>
                  <span class="related-samples">N={{ dataset.Sample_Count }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="Study_Family_ID" label="Study ID" width="175" sortable>
        <template #default="{ row }">
          <span class="study-id">{{ row.Study_Family_ID }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="Title" label="Study Title" min-width="330">
        <template #default="{ row }"><div class="line-clamp-2">{{ row.Title }}</div></template>
      </el-table-column>
      <el-table-column prop="Evidence_Tier" label="Tier" width="95">
        <template #default="{ row }">
          <el-tag size="small" :type="row.Evidence_Tier === 'core' ? 'success' : 'warning'" effect="plain">
            {{ row.Evidence_Tier }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Organism" width="170">
        <template #default="{ row }">{{ row.Organisms.join(', ') }}</template>
      </el-table-column>
      <el-table-column label="Modalities" min-width="220">
        <template #default="{ row }">
          <div class="tag-stack">
            <el-tag v-for="type in row.Data_Types" :key="type" size="small" effect="plain">{{ type }}</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="Dataset_Count" label="GSE" width="80" sortable align="center" />
      <el-table-column prop="Primary_Dataset_Count" label="Primary" width="95" sortable align="center" />
      <el-table-column prop="Submission_Date" label="Latest" width="110" sortable />
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

.study-id {
  color: #315f50;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  font-weight: 600;
}
</style>
