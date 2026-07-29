# Skin Aging GEO 完整历史回溯审计

- 审计日期：2026-07-29
- GEO Series 原始检索结果：476
- 第一阶段候选：275
- 自动规则：include 162 / review 3 / exclude 311
- 最终整理：include 163 / review 0 / exclude 313
- 正式生产数据：163
- 未决复核队列：0
- 第一阶段候选排除日志：112

## 主题分层

- `intrinsic_skin_aging`：51
- `photoaging`：37
- `cellular_senescence`：30
- `aged_skin_repair`：18
- `skin_appendage_aging`：15
- `rejuvenation_intervention`：12

## 数据类型

- `bulk RNA-seq`：53
- `scRNA-seq`：33
- `expression microarray`：33
- `DNA methylation`：18
- `miRNA/ncRNA profiling`：17
- `ChIP/CUT&RUN`：6
- `ATAC-seq`：2
- `spatial transcriptomics`：1

## 物种

- `Homo sapiens`：86
- `Mus musculus`：75
- `Homo sapiens; synthetic construct`：1
- `synthetic construct; Homo sapiens`：1

## 证据裁决

- GSE211839 → **exclude**：实验终点是 HFDPC 毛发生长，anti-aging 仅为材料属性描述，未设置皮肤或毛囊老化模型。
- GSE141950 → **exclude**：实验仅研究 Hutchinson-Gilford progeria syndrome 患者成纤维细胞，主问题是系统性早老疾病而非皮肤老化。
- GSE151601 → **include**：Skin-Specific DNA methylation age predictor 的细胞传代验证子集，直接用于皮肤生物年龄测量。
- GSE151603 → **include**：Skin-Specific DNA methylation age predictor 的 senotherapeutic 干预验证子集，直接服务于皮肤老化研究。

## 生产安全

- 相关性判断不调用外部 AI。
- Daily update 只追加规则确认的 include，不删除既有 accession。
- review 不进入生产数据；exclude 留在可追溯日志中。
- 原始检索快照与最终审计结果分开保存，可随时重跑。
