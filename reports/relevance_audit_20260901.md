# Skin Aging GEO 完整历史回溯审计

- 审计日期：2026-09-01
- GEO Series 原始检索结果：1050
- 第一阶段候选：472
- 自动规则：include 217 / review 3 / exclude 830
- 最终整理：include 209 / review 0 / exclude 841
- 正式生产数据：209
- 独立 Study Families：165
- 未决复核队列：0
- 第一阶段候选排除日志：263

## 主题分层

- `intrinsic_skin_aging`：120
- `cellular_senescence`：42
- `photoaging`：17
- `skin_appendage_aging`：14
- `aged_skin_repair`：10
- `rejuvenation_intervention`：6

## 数据类型

- `bulk RNA-seq`：69
- `expression microarray`：38
- `scRNA-seq`：35
- `DNA methylation`：26
- `miRNA/ncRNA profiling`：23
- `ChIP/CUT&RUN`：8
- `scATAC-seq`：3
- `microbiome`：2
- `ATAC-seq`：2
- `Expression profiling by RT-PCR`：2
- `spatial transcriptomics`：1

## 物种

- `Homo sapiens`：109
- `Mus musculus`：94
- `synthetic construct; Homo sapiens`：4
- `Homo sapiens; synthetic construct`：1
- `Mus musculus; Danio rerio`：1

## 证据裁决

- GSE327760 → **exclude**：研究未使用 aged、senescent 或 photoaged 模型；skin rejuvenation 只是射频微针后的修复性表述。
- GSE267066 → **exclude**：仅比较不同族群的健康皮肤，年龄为供者描述而非研究变量，没有皮肤老化对照。
- GSE264103 → **exclude**：实际 RNA-seq 对象为 articular chondrocytes，皮肤老化仅用于构建处理条件，不是被测组织或细胞。
- GSE255684 → **exclude**：研究主问题是 aged donor 脑膜与皮肤成纤维细胞的组织差异，没有年龄对照，主要服务于 CNS 研究。
- GSE164780 → **exclude**：实际研究对象为口腔角质形成细胞，且该子系列不是皮肤组学数据。
- GSE211839 → **exclude**：实验终点是 HFDPC 毛发生长，anti-aging 仅为材料属性描述，未设置皮肤或毛囊老化模型。
- GSE141950 → **exclude**：实验仅研究 Hutchinson-Gilford progeria syndrome 患者成纤维细胞，主问题是系统性早老疾病而非皮肤老化。
- GSE155371 → **exclude**：实际研究对象为口腔角质形成细胞，属于口腔上皮衰老而非皮肤老化。
- GSE164781 → **exclude**：研究主题为口腔角质形成细胞衰老，缺少皮肤组织或皮肤来源细胞证据。
- GSE151601 → **include**：Skin-Specific DNA methylation age predictor 的细胞传代验证子集，直接用于皮肤生物年龄测量。
- GSE151603 → **include**：Skin-Specific DNA methylation age predictor 的 senotherapeutic 干预验证子集，直接服务于皮肤老化研究。
- GSE90643 → **exclude**：主要研究光动力治疗后的 actinic keratosis 与 field cancerization，rejuvenation 为疾病治疗后的次级表达特征。
- GSE100409 → **exclude**：仅比较 5 月龄与 1 岁供者的两个幼年来源成纤维细胞样本，元数据明确称两者均为 young，不构成皮肤老化对照。
- GSE93657 → **exclude**：研究对象为 ENPP1 相关 Cole disease 色素异常，aged-matched control 仅用于匹配，不研究皮肤老化。
- GSE62648 → **exclude**：实验使用 9 周龄小鼠并比较胶原水解物与对照，1 周子系列没有 aged/young 对照，不是皮肤老化组学设计。
- GSE62649 → **exclude**：实验从 9 周龄小鼠开始并比较胶原水解物与对照，12 周子系列仍缺少老年动物或明确衰老模型。
- GSE45513 → **exclude**：比较同龄小鼠的斑秃患病与未患病皮肤，研究变量是 alopecia areata 而非老化。
- GSE21648 → **exclude**：主要比较口腔黏膜与皮肤成纤维细胞的创伤反应，未设置 young-old 或细胞衰老对照。

## 生产安全

- 相关性判断不调用外部 AI。
- Daily update 只追加规则确认的 include，不删除既有 accession。
- review 不进入生产数据；exclude 留在可追溯日志中。
- 原始检索快照与最终审计结果分开保存，可随时重跑。
