# Changelog

## v0.1.0 — 2026-09-29

首版。从生产环境（双 Agent 端 + 20 项 skill 正本树）提炼的治理层资产，经三轮脱敏清洗与三轮独立审查。

### Added
- `docs/paradigm.md`：治理范式图谱——五层范式（摄入/裁决/发布/生命周期/跨会话）+ 五条共享公理 + 适用边界裁剪规则（阅读入口）。
- `tools/sync_check.py`：跨端挂载一致性校验器（自动发现挂载、遮蔽检测、链接名一致性、挂载分布报表；env + argparse 配置，纯 stdlib，只读；要求 Python >= 3.12）。
- `governance/junction-discipline.md`：正本+链接挂载模型、四条纪律、校验器设计依据（含行尾归一化与 reparse point 判定两坑）、变更门禁。
- `governance/lifecycle-clauses.md`：降档时钟 / 需求真伪检具（记账口径）/ 登记三防 / 合议治理（盲写先行+关键数字同轮复核）/ 学习转化纪律 / 信源纪律 / 反题义务。
- `governance/closure-workflow.md`：会话收尾四步闭环（未完成汇总→记忆蒸馏→入库判定→轻复检）+ 仪式化空转反题警示。
- `templates/kb-ingest-gate/`、`templates/three-ruler-review/`：入库闸门与三标尺复检两个 SKILL.md 模板（占位符化，接入前替换 `<...>` 变量，含义见 README 对照表）。
- `LICENSE`（代码 MIT / 文档 CC-BY-4.0 双照）、`README.md`。

### 脱敏与审查记录
- 三轮清洗：绝对路径/家目录/私有系统名/业务专名全量占位符化；机器盘符叙述泛化；环境变量前缀中性化（GOV_）。
- 保留项（经裁定）：公开产品名（TRAE/WorkBuddy）作为实测教训载体；完整日期时间线（无个人指向）。
- 发布前三轮独立盲审；终审修复：链接目标改严格父子判定（封堵同名旁支前缀绕过）、声明 Python>=3.12 并识别 Unix symlink、挂载参数去产品名（--mount-a/b）、README 增占位符对照表与 AI-1x 悬空编号声明。

### Known Gaps（P2 backlog）
- 模板内脚本引用（`<YOUR_SCRIPTS_DIR>/...`）为占位示例，未提供等价开源实现；按需自研。
- lint/CI 脚本化、多语言 README 未提供。
- staging→生产毕业回灌机制属原体系内部事务，不随本仓库发布。
