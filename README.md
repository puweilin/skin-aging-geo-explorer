# Skin Aging GEO Dataset Explorer

[![Daily update](https://github.com/puweilin/skin-aging-geo-explorer/actions/workflows/update-data.yml/badge.svg)](https://github.com/puweilin/skin-aging-geo-explorer/actions/workflows/update-data.yml)

面向皮肤老化研究的 GEO 数据策展与可视化项目。v2 同时提供
`Study Family` 和 `GEO Dataset` 两个层级，避免把同一论文下的
SuperSeries、SubSeries 或多组学 GSE 误计为多项独立研究。

生产相关性判断不调用大语言模型；AI 只为已经正式纳入且处于 active 状态的
数据集生成中文摘要。

## 当前数据

2026-09-01 使用 v2 宽检索回溯 6,341 条 GEO 索引记录，并与旧快照合并为
1,050 个唯一 GSE 后，重新策展得到：

- 209 个 active GEO Series；
- 165 个 Study Families；
- 150 个包含直接老化比较或干预证据的 primary datasets；
- 5,455 个 GSE 名义样本，尚未跨 GSE/GSM 去重；
- 0 个未决人工复核记录；
- 209 个中文 AI 辅助摘要。

完整范围、纳排标准和人工修正策略见
[`CURATION_PROTOCOL.md`](CURATION_PROTOCOL.md)，v2 字段定义见
[`docs/data-schema.md`](docs/data-schema.md)。

## v2 数据层

- `data/geo_data.json`：active GSE 生产数据；
- `data/study_families.json`：研究级聚合数据；
- `data/manual_curation_overrides.json`：稳定人工裁决；
- `data/relevance_review_queue.json`：待复核记录；
- `data/relevance_decision_log.json`：排除与修正证据；
- `data/search_results_raw_20260901.json`：历次完整快照合并后的 raw corpus；
- `reports/relevance_audit_20260901.*`：本次完整重策展审计；
- `tests/fixtures/relevance_gold_set.json`：120 条分层相关性回归集。

`public/data/` 是前端使用的原子同步镜像。

## 相关性与分层

1. Stage 1 要求同时出现皮肤对象与 aging、senescence、photoaging、
   rejuvenation 或明确年龄对照；
2. Stage 2 使用标题、摘要、样本标题和 Overall Design 验证实际测序对象；
3. 人工裁决可以修正历史误纳，但自动 daily update 不得静默删除既有记录；
4. 每个数据集标记为 `primary` 或 `supporting`；
5. 同时提供 aging context、组织区室、细胞类型、模型、比较设计、暴露、
   部位、性别和质量标记等多维字段。

## 运行完整历史检索

```bash
export NCBI_EMAIL="your-email@example.org"
export NCBI_API_KEY="your-optional-api-key"
python scripts/search_geo.py --full-history
```

默认 daily 模式检索最近 30 天：

```bash
export NCBI_EMAIL="your-email@example.org"
python scripts/search_geo.py
```

使用已保存的原始快照重新策展：

```bash
python scripts/audit_relevance.py \
  --input data/search_results_raw_20260901.json
```

## 测试与数据验证

```bash
python -m unittest discover -s tests -v
python scripts/validate_data.py
```

相关性测试包括 120 条 include/exclude 平衡回归集，并验证正式决策 precision
不低于 95%、recall 不低于 90%。

## 本地网页

```bash
npm install
npm run dev
```

生产构建：

```bash
npm run build
```

网页默认显示 Study Family 目录，可切换到 GSE 目录，并按老化情境、范围层级、
组学类型、物种、组织区室、模型系统和证据角色筛选。

## AI 摘要

```bash
export DEEPSEEK_API_KEY="your-api-key"
python scripts/generate_ai_summaries.py
```

AI 摘要步骤不得增删、重排 accession，也不允许重新判断相关性。只有
`Relevance_Final_Decision=include` 且 `Curation_Status=active` 的记录可处理。

## GitHub Actions

每日北京时间 00:00 自动执行：

1. 检索最近 30 天的新 GEO Series；
2. 应用两阶段规则与稳定人工裁决；
3. 重建 Dataset 和 Study Family 双层数据；
4. 为新纳入记录补充中文摘要；
5. 运行单元测试、数据一致性校验和前端构建；
6. 只在数据变化时提交生产 JSON。

仓库需要配置：

- `NCBI_EMAIL`；
- `NCBI_API_KEY`（可选）；
- `DEEPSEEK_API_KEY`。

密钥必须放在本地 `.env` 或 GitHub Actions Secrets，不得写入配置、日志或
Git 历史。
