<script setup>
import { ref, computed } from 'vue'
import { Link, RefreshLeft, Search } from '@element-plus/icons-vue'

const props = defineProps({
  data: { type: Array, default: () => [] }
})

const searchText = ref('')
const selectedOrganism = ref('')
const selectedDataType = ref('')
const selectedContext = ref('')
const selectedTissue = ref('')
const selectedModel = ref('')
const selectedRole = ref('')

const uniqueScalar = key => computed(() =>
  Array.from(new Set(props.data.map(d => d[key]).filter(Boolean))).sort()
)
const uniqueArray = key => computed(() =>
  Array.from(new Set(props.data.flatMap(d => d[key] || []).filter(Boolean))).sort()
)

const organisms = uniqueScalar('Organism')
const dataTypes = uniqueScalar('Data_Type')
const contexts = uniqueArray('Aging_Contexts')
const tissues = uniqueArray('Tissue_Compartments')
const models = uniqueArray('Model_Systems')

const labels = {
  intrinsic_skin_aging: '内源性皮肤老化',
  photoaging: '光老化',
  cellular_senescence: '细胞衰老',
  rejuvenation_intervention: '年轻化干预',
  aged_skin_repair: '老化皮肤修复',
  skin_appendage_aging: '附属器老化',
  exposome_aging: '外暴露老化',
  premature_aging_model: '早老模型',
  epidermis: '表皮',
  dermis: '真皮',
  whole_skin: '全层皮肤',
  skin_appendage: '皮肤附属器',
  dermal_adipose: '真皮脂肪',
  human_tissue_in_vivo: '人皮肤/活检',
  mouse_in_vivo: '小鼠体内',
  primary_cell_culture: '原代细胞',
  ex_vivo_skin: '离体皮肤',
  skin_model_3d: '3D 皮肤模型',
  cell_line: '细胞系',
  model_unspecified: '模型未细分'
}

const formatLabel = value => labels[value] || value || 'N/A'

const filteredData = computed(() => props.data.filter(item => {
  if (searchText.value) {
    const query = searchText.value.toLowerCase()
    const haystack = [
      item.Accession,
      item.Title,
      item.Summary,
      item.AI_Summary_CN,
      item.Study_Family_ID,
      item.Study_Family_Title
    ].join(' ').toLowerCase()
    if (!haystack.includes(query)) return false
  }
  if (selectedOrganism.value && item.Organism !== selectedOrganism.value) return false
  if (selectedDataType.value && item.Data_Type !== selectedDataType.value) return false
  if (selectedContext.value && !(item.Aging_Contexts || []).includes(selectedContext.value)) return false
  if (selectedTissue.value && !(item.Tissue_Compartments || []).includes(selectedTissue.value)) return false
  if (selectedModel.value && !(item.Model_Systems || []).includes(selectedModel.value)) return false
  if (selectedRole.value && item.Dataset_Role !== selectedRole.value) return false
  return true
}))

const clearFilters = () => {
  searchText.value = ''
  selectedOrganism.value = ''
  selectedDataType.value = ''
  selectedContext.value = ''
  selectedTissue.value = ''
  selectedModel.value = ''
  selectedRole.value = ''
}

const dataTypeColor = type => ({
  'bulk RNA-seq': '#315f50',
  'scRNA-seq': '#6e887a',
  'spatial transcriptomics': '#a8754e',
  'DNA methylation': '#8d6f69',
  'scATAC-seq': '#596978',
  'single-cell multiome': '#4c6878',
  'ATAC-seq': '#596978',
  'ChIP/CUT&RUN': '#7e655f',
  'expression microarray': '#8c7654',
  'miRNA/ncRNA profiling': '#826f8d'
}[type] || '#747f76')

const organismLabel = organism => {
  if (organism === 'Homo sapiens') return 'Human'
  if (organism === 'Mus musculus') return 'Mouse'
  return organism || 'Unknown'
}

const openGeoLink = url => window.open(url, '_blank', 'noopener,noreferrer')
</script>

<template>
  <div class="data-table">
    <div class="filter-bar flex flex-wrap items-center gap-4">
      <el-input
        v-model="searchText"
        placeholder="标题、摘要、GSE 或 Study ID"
        :prefix-icon="Search"
        clearable
        class="w-64"
      />

      <el-select v-model="selectedOrganism" placeholder="物种" clearable class="w-36">
        <el-option v-for="value in organisms" :key="value" :label="organismLabel(value)" :value="value" />
      </el-select>

      <el-select v-model="selectedDataType" placeholder="组学类型" clearable class="w-44">
        <el-option v-for="value in dataTypes" :key="value" :label="value" :value="value" />
      </el-select>

      <el-select v-model="selectedContext" placeholder="老化情境" clearable class="w-44">
        <el-option v-for="value in contexts" :key="value" :label="formatLabel(value)" :value="value" />
      </el-select>

      <el-select v-model="selectedTissue" placeholder="组织区室" clearable class="w-44">
        <el-option v-for="value in tissues" :key="value" :label="formatLabel(value)" :value="value" />
      </el-select>

      <el-select v-model="selectedModel" placeholder="模型系统" clearable class="w-44">
        <el-option v-for="value in models" :key="value" :label="formatLabel(value)" :value="value" />
      </el-select>

      <el-select v-model="selectedRole" placeholder="证据角色" clearable class="w-36">
        <el-option label="Primary" value="primary" />
        <el-option label="Supporting" value="supporting" />
      </el-select>

      <el-button @click="clearFilters" :icon="RefreshLeft">重置</el-button>

      <div class="result-count ml-auto">
        <strong>{{ filteredData.length }}</strong>
        <span>/ {{ data.length }} GSE</span>
      </div>
    </div>

    <el-table :data="filteredData" stripe style="width: 100%">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="detail-panel mx-4">
            <div class="detail-grid">
              <div>
                <div class="ai-summary-card mb-4">
                  <div class="label">策展结论</div>
                  <div class="content">{{ row.Relevance_Final_Reason || row.Relevance_Reason }}</div>
                </div>

                <div v-if="row.AI_Summary_CN" class="ai-summary-card mb-4">
                  <div class="label"><el-icon><MagicStick /></el-icon> AI 辅助摘要</div>
                  <div class="content">{{ row.AI_Summary_CN }}</div>
                </div>

                <div class="detail-section">
                  <div class="label">Summary</div>
                  <div class="value">{{ row.Summary || 'N/A' }}</div>
                </div>
                <div class="detail-section">
                  <div class="label">Overall Design</div>
                  <div class="value">{{ row.Overall_Design || 'N/A' }}</div>
                </div>
              </div>

              <div>
                <div class="detail-section">
                  <div class="label">Study Family</div>
                  <div class="value">
                    <strong>{{ row.Study_Family_ID }}</strong><br>
                    {{ row.Study_Family_Title }}<br>
                    Related: {{ (row.Related_GSEs || []).join(', ') }}
                  </div>
                </div>

                <div class="detail-section">
                  <div class="label">多维标签</div>
                  <div class="tag-stack">
                    <el-tag v-for="value in row.Aging_Contexts || []" :key="`aging-${value}`" size="small">
                      {{ formatLabel(value) }}
                    </el-tag>
                    <el-tag v-for="value in row.Tissue_Compartments || []" :key="`tissue-${value}`" size="small" effect="plain">
                      {{ formatLabel(value) }}
                    </el-tag>
                    <el-tag v-for="value in row.Model_Systems || []" :key="`model-${value}`" size="small" type="info" effect="plain">
                      {{ formatLabel(value) }}
                    </el-tag>
                  </div>
                </div>

                <div class="detail-section">
                  <div class="label">分组 / 暴露 / 部位</div>
                  <div class="value">
                    Comparison: {{ (row.Comparison_Designs || []).join(', ') || 'N/A' }}<br>
                    Exposure: {{ (row.Exposure_Types || []).join(', ') || 'N/A' }}<br>
                    Site: {{ (row.Anatomical_Sites || []).join(', ') || 'N/A' }}<br>
                    Sex: {{ (row.Sexes || []).join(', ') || 'N/A' }}
                  </div>
                </div>

                <div class="detail-section">
                  <div class="label">元数据与质量</div>
                  <div class="value">
                    Completeness: {{ row.Metadata_Completeness }}%<br>
                    Flags: {{ (row.Quality_Flags || []).join(', ') || 'None' }}<br>
                    Platform: {{ row.Platform || 'N/A' }}<br>
                    Lab: {{ row.Lab || 'N/A' }} @ {{ row.Institute || 'N/A' }}
                  </div>
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
                    >{{ id.trim() }}</a>
                  </div>
                </div>

                <el-button type="primary" :icon="Link" @click="openGeoLink(row.GEO_Link)">
                  打开 GEO 页面
                </el-button>
              </div>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="Accession" label="Accession" width="120" sortable>
        <template #default="{ row }">
          <a :href="row.GEO_Link" target="_blank" class="text-blue-500 hover:underline font-medium">
            {{ row.Accession }}
          </a>
        </template>
      </el-table-column>

      <el-table-column prop="Title" label="Title" min-width="310">
        <template #default="{ row }"><div class="line-clamp-2">{{ row.Title }}</div></template>
      </el-table-column>

      <el-table-column prop="Dataset_Role" label="Evidence" width="110">
        <template #default="{ row }">
          <el-tag :type="row.Dataset_Role === 'primary' ? 'success' : 'info'" size="small">
            {{ row.Dataset_Role }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="Evidence_Tier" label="Tier" width="90">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.Evidence_Tier }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="Organism" label="Organism" width="160">
        <template #default="{ row }">{{ organismLabel(row.Organism) }}</template>
      </el-table-column>

      <el-table-column prop="Data_Type" label="Data Type" width="190">
        <template #default="{ row }">
          <el-tag
            size="small"
            :style="{ backgroundColor: dataTypeColor(row.Data_Type) + '12', color: dataTypeColor(row.Data_Type), borderColor: dataTypeColor(row.Data_Type) + '30' }"
          >{{ row.Data_Type }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="Sample_Count" label="Nominal N" width="110" sortable align="center" />
      <el-table-column prop="Metadata_Completeness" label="Metadata" width="105" sortable>
        <template #default="{ row }">{{ row.Metadata_Completeness }}%</template>
      </el-table-column>
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
</style>
