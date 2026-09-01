# Skin Aging GEO 策展协议

版本：2.0（2026-09-01）

## 目标

本项目整理与皮肤老化直接相关的 GEO Series，并同时提供两个层级：

1. `Study Family`：一项科学研究或同一论文下的一组相关 GSE；
2. `GEO Dataset`：具体的 GSE、组学类型和实验设计。

生产相关性判断使用可解释规则与人工裁决。大语言模型只为已经正式纳入的
记录生成中文摘要，不参与纳入、排除或排序。

## 范围分层

### Core

- 内源性或时间性皮肤老化，包括 young/old 对照和年龄连续梯度；
- 光老化，包括明确的 photoaging、慢性 UVA/UVB 和日晒/避光部位对照；
- 皮肤来源细胞的复制性或应激诱导衰老；
- 老化相关的屏障、免疫、ECM、色素、创伤修复和干细胞变化；
- 具有 aged、senescent 或 photoaged 模型及适当对照的年轻化干预。

### Extension

- 明确以年龄为终点的毛囊、皮脂腺、真皮脂肪等附属器老化；
- 以皮肤表型或皮肤生物年龄为直接终点的系统性早老模型；
- 污染、吸烟、糖化等外源暴露，但必须明确研究皮肤老化表型。

### Exclude

- 只有急性 UV 损伤、没有 photoaging 或衰老设计；
- 年龄仅为统计协变量的皮肤疾病、肿瘤或其他器官研究；
- 皮肤成纤维细胞仅作为 iPSC、诊断材料或其他组织模型的细胞来源；
- 胚胎皮肤发育，或单纯新生儿/成人差异而不研究老化；
- 没有老化模型的泛化 `anti-aging` 材料或营销性研究；
- 普通 AGA、毛周期或毛发生长研究，除非年龄依赖性老化是直接终点。

## 两阶段判断

### Stage 1：高召回候选

标题、摘要、Overall Design 或样本标题中必须同时出现：

- 皮肤对象证据；
- aging、senescence、photoaging、rejuvenation 或明确年龄对照证据。

### Stage 2：研究对象验证

依次检查：

1. 实际测序样本是否为皮肤组织或皮肤来源细胞；
2. 是否存在年龄、衰老、光老化或干预对照；
3. 皮肤老化是否为主要科学问题，而非背景描述；
4. Overall Design 是否与标题或摘要矛盾；
5. 数据集是直接老化证据 `primary`，还是同一研究中的机制支持数据
   `supporting`。

只有 `include` 且 `Curation_Status=active` 的记录进入生产数据。
`review` 进入复核队列；`exclude` 和 `deprecated` 保留逐条证据。

## Study Family 规则

以下证据按优先级将 GSE 归为同一研究：

1. 共享规范化 PubMed ID；
2. GEO `Series_relation` 明确声明 SuperSeries/SubSeries；
3. 去除组学后缀后的标题完全一致。

Study Family 只用于组织和去重展示，不改变单个 GSE 的相关性结论。
样本数仍标为 `nominal`，除非完成 GSM 级样本身份核对；不得把多个
SubSeries 的样本数简单解释为独立生物样本数。

## 人工裁决与版本化修正

稳定人工裁决保存在 `data/manual_curation_overrides.json`。自动更新可以：

- 追加规则确认的 include；
- 根据显式人工裁决将历史误纳记录移出 active corpus；
- 保留原始快照、排除原因、裁决来源和 schema/curation 版本。

自动规则不得静默删除既有 active accession。

全量重构时以历次原始检索快照的并集作为候选底座；同一 accession 的新快照仅以
非空字段更新旧元数据，避免检索策略变化或 GEO 临时缺字段造成历史记录丢失。

## 最低质量要求

- accession、标题、物种、数据类型、样本数和 GEO 链接必须存在；
- 正式记录必须有可解释纳入原因、范围分层和数据集角色；
- PubMed ID 必须规范化为纯数字；
- 同一 accession 不得重复；
- `data/` 与 `public/data/` 必须原子同步；
- 单元测试、数据一致性测试和生产构建必须通过。
