# Skin Aging GEO Dataset Explorer

[![Daily update](https://github.com/puweilin/skin-aging-geo-explorer/actions/workflows/update-data.yml/badge.svg)](https://github.com/puweilin/skin-aging-geo-explorer/actions/workflows/update-data.yml)

这是从 AGA / Hair Follicle GEO 项目复用而来的独立数据策展框架，主题改为
`skin aging`。生产数据的相关性判断不调用大语言模型；AI 只为已经正式
纳入的数据集生成中文摘要。

## 纳入范围

- 人类和小鼠的皮肤、表皮、真皮及主要皮肤细胞；
- 内源性 / 年龄相关皮肤老化；
- 光老化和明确以 photoaging 为终点的慢性 UV 模型；
- 皮肤来源细胞的复制性或应激诱导衰老；
- 老化皮肤的修复、屏障、免疫、附属器变化和抗衰干预；
- 转录组、单细胞、空间组学、表观遗传及其他 GEO Series 数据。

## 两阶段规则

1. 高召回阶段：记录必须同时存在皮肤对象词和 aging / senescence /
   photoaging / rejuvenation 等老化词。
2. 主题验证阶段：使用标题、摘要和 Overall Design 验证皮肤样本、
   年龄/衰老对照及主研究问题。

只有 `include` 会写入 `data/geo_data.json`；`review` 进入
`data/relevance_review_queue.json`；`exclude` 写入决定日志。Daily update
只追加，不删除已有 accession。

截至 2026-07-29 的完整历史回溯共检索到 476 个 GEO Series，最终整理出
163 个正式数据集，未决复核为 0。完整原始快照和逐条审计证据保存在
`data/search_results_raw_20260729.json` 与 `reports/`。

## 运行

```bash
export NCBI_EMAIL="your-email@example.org"
python scripts/search_geo.py --full-history
python -m unittest discover -s tests -v
```

默认 daily 模式检索最近 30 天：

```bash
python scripts/search_geo.py
```

## 本地浏览

```bash
npm install
npm run dev
```

生产构建：

```bash
npm run build
```

## AI 摘要

```bash
export DEEPSEEK_API_KEY="your-api-key"
python scripts/generate_ai_summaries.py
```

摘要脚本默认使用 `deepseek-v4-flash` 非思考模式，只处理
`Relevance_Final_Decision == "include"` 且尚无摘要的记录。它不会调用或
修改相关性规则，也不得增删或重排 accession；每批结果会原子同步到
`data/geo_data.json` 和 `public/data/geo_data.json`。

## GitHub Actions

`.github/workflows/update-data.yml` 每天北京时间 00:00 自动执行：

1. 检索 GEO 最近 30 天的新记录；
2. 使用两阶段规则追加 `include`，把 `review` 与 `exclude` 分流；
3. 只为新纳入且缺少摘要的数据集调用 DeepSeek；
4. 运行安全测试和前端生产构建；
5. 仅在数据变化时由 `github-actions[bot]` 提交回 `main`。

仓库需要配置以下 Actions Secrets：

- `NCBI_EMAIL`
- `NCBI_API_KEY`（可选，但建议配置）
- `DEEPSEEK_API_KEY`

密钥不会写入数据文件、日志或 Git 历史。
