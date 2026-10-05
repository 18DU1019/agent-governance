---
name: agent-governance
description: "Skill-asset lifecycle governance kit. Use when governing skill assets across multiple agent ends: mount topology consistency checks (junction/symlink), copy-drift audits, skill retirement decisions (sunset clocks), ingest/closure/review workflows, or desensitization acceptance scans. Triggers: skill 治理、正本挂载、多端挂载、sync_check、副本漂移、退役时钟、登记三防、入库闸门模板、三标尺复检模板、收尾闭环、脱敏复扫。"
---

# Agent Skill Governance Kit（agent-governance）

本 skill 是本仓的路由入口。治理对象：skill 资产的生命周期——本 kit 管"资产何时该退役、退役依据是否可信"，不管"怎么组织与同步"（版本 pin / 分发同步用官方工具，场景对照见 README 选型边界）。

## 资产地图（路径均相对本插件根）

- `governance/lifecycle-clauses.md` —— 条款本体：降档时钟 / 需求真伪检具 / 登记三防 / 合议治理 / 执行前复扫（条款 9）/ 仪器正交（条款 10），附"条款自证"表。先读。
- `governance/junction-discipline.md` —— 正本+链接挂载模型、四条纪律、校验器设计依据、负例覆盖面清单。
- `governance/closure-workflow.md` —— 会话收尾四步闭环（汇总→蒸馏→入库判定→轻复检）。
- `docs/paradigm.md` —— 治理范式图谱：五层范式 + 共享公理 + 适用边界。
- `tools/sync_check.py` —— 跨端挂载一致性校验器（只读，纯 stdlib，Python>=3.12，识别 Windows junction 与 Unix symlink）。
- `tools/desensitize_scan.py` —— 独立脱敏验收仪器（形态扫描 + 白名单反证）。
- `tools/sync_check_selftest.py` —— 校验器二十二用例回归自测。
- `templates/` —— 两个通用技能模板（kb-ingest-gate / three-ruler-review），内含 `<...>` 占位符，替换后接入自家技能目录；本插件不复制其副本，模板目录即正本。

## 常用动作

1. **挂载体检**：`python <本插件根>/tools/sync_check.py --source ./skills --mount-a <AGENT_HOME_A>/skills --mount-b <AGENT_HOME_B>/skills`。退出码 0=PASS，1=FAIL/SUSPENDED，2=参数错误。支持环境变量 `GOV_SKILL_SOURCE / GOV_MOUNT_A / GOV_MOUNT_B`。
2. **回归自测**：`python tools/sync_check_selftest.py`（应 22/22 PASS）。
3. **发布前复扫**：`python tools/desensitize_scan.py --root <仓库根>`。条款 9 要求执行前复扫；条款 10 要求清洗与验收不得共用同一把尺。
4. **退役裁定**：按 lifecycle-clauses 的降档时钟产默认案；时钟到期只提案，不自动动手。
5. **收尾闭环**：按 closure-workflow 四步执行。

## 硬边界

- 条款源自真实生产环境反复踩坑；条款↔具体事故的逐条映射表属原体系内部台账，未随本仓库发布，不断言可逐条回溯（可核验的替代面=条款自证表）。
- 校验器针对**自建正本、多端挂载**拓扑；"从外部安装 skill 并跟踪版本"场景用官方工具（如 `gh skill`）。
- 遮蔽判定四档：字节一致 / 仅行尾差异 / 内容分叉 / SUSPENDED（不可读不冒充一致结论）。
