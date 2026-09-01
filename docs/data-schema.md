# Skin Aging GEO v2 数据结构

## Dataset record

生产文件：`data/geo_data.json` 与 `public/data/geo_data.json`。

除 GEO 原始元数据外，v2 增加以下字段：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `Schema_Version` | string | 数据结构版本 |
| `Curation_Version` | string | 策展规则版本 |
| `Curation_Status` | string | `active` 或 `deprecated` |
| `Study_Family_ID` | string | 稳定的研究级标识 |
| `Study_Family_Title` | string | 去除组学后缀后的研究标题 |
| `Related_GSEs` | array | 同一 Study Family 中的 GSE |
| `Series_Role` | string | `standalone`、`superseries` 或 `subseries` |
| `Dataset_Role` | string | `primary` 或 `supporting` |
| `Evidence_Tier` | string | `core` 或 `extension` |
| `Aging_Contexts` | array | intrinsic、photoaging、senescence 等多标签 |
| `Biological_Processes` | array | ECM、屏障、免疫、修复等多标签 |
| `Tissue_Compartments` | array | whole skin、epidermis、dermis 等 |
| `Cell_Types` | array | 可从元数据支持的细胞类型 |
| `Model_Systems` | array | human/mouse in vivo、ex vivo、primary culture 等 |
| `Comparison_Designs` | array | young-old、senescent-control、treatment-rescue 等 |
| `Exposure_Types` | array | UV、sun exposure、smoking、pollution 等 |
| `Age_Groups` | array | 元数据中明确出现的年龄组标签 |
| `Sexes` | array | 元数据中明确出现的性别 |
| `Anatomical_Sites` | array | 元数据中明确出现的皮肤部位 |
| `Metadata_Completeness` | integer | 关键字段完整度百分比 |
| `Quality_Flags` | array | 缺失信息和解释限制 |

`Sample_Count` 是 GEO Series 的名义样本数。跨 GSE 或 Study Family 汇总时
不得称为去重后的生物样本数。

## Study Family record

生产文件：`data/study_families.json` 与
`public/data/study_families.json`。

| 字段 | 含义 |
| --- | --- |
| `Study_Family_ID` | 稳定研究标识 |
| `Title` | 研究级标题 |
| `Primary_Accession` | 代表性 GSE |
| `Related_GSEs` | 全部相关 GSE |
| `Dataset_Count` | GSE 数量 |
| `Primary_Dataset_Count` | 直接老化证据 GSE 数量 |
| `Nominal_Sample_Total` | 未进行 GSM 去重的名义样本总数 |
| `Sample_Count_Interpretation` | 固定提示样本数尚未跨 GSE 去重 |
| `Organisms` | 物种集合 |
| `Data_Types` | 组学类型集合 |
| `Aging_Contexts` | 老化情境集合 |
| `Scope_Categories` | 主题集合 |
| `Evidence_Tier` | core/extension |
| `PubMed_IDs` | 规范化 PMID 集合 |
| `Submission_Date` | 家族内最新提交日期 |

## 兼容字段

`Scope_Category` 和 `Relevance_*` 字段继续保留，以兼容旧看板和历史审计。
新代码优先使用 `Primary_Scope_Category`、`Aging_Contexts` 和
`Dataset_Role`。
