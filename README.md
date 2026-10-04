# Agent Skill Governance Kit

[English](README_en.md)（译本，以中文版为正本）

多 Agent 端环境下 skill 资产的**生命周期治理条款包**：以降档时钟/登记三防/记账口径为本体，附跨端正本挂载一致性校验器与入库/复检模板。

本仓库解决一个具体事故形态：同一套 skill 被多端加载后，副本漂移、退役无据、记账失真。三层产物各对一类事故：条款（lifecycle-clauses）管资产何时退役与退役依据是否可信，校验器（sync_check）管挂载拓扑一致性，模板管收尾闭环。每条条款可回溯到一次真实生产事故（见 CHANGELOG），非纸面设计——这也是它区别于编排框架与分发工具的地方：那两层解决"怎么组织与同步"，本仓解决"怎么退场、退场依据是否可信"。

## 目录结构

```
agent-governance/
├── README.md / LICENSE / CHANGELOG.md
├── docs/
│   └── paradigm.md            # 治理范式图谱：五层范式 + 共享公理 + 适用边界（建议先读）
├── tools/
│   ├── sync_check.py          # 跨端挂载一致性校验器（只读，纯 stdlib，Python>=3.12）
│   └── sync_check_selftest.py # 校验器六用例回归自测（CI 已接线，本地随时可跑）
├── governance/
│   ├── junction-discipline.md # 正本+链接挂载模型与四条纪律、校验器设计依据
│   ├── lifecycle-clauses.md   # 降档时钟/需求真伪检具/登记三防/合议治理/学习转化等条款
│   └── closure-workflow.md    # 会话收尾四步闭环（汇总→蒸馏→入库判定→轻复检）
└── templates/
    ├── kb-ingest-gate/        # 知识库入库闸门（防复制品、按落位规则接链、复检闭环）
    └── three-ruler-review/    # 三标尺复检+联网查漏+方案迭代模板
```

## 快速开始

1. **治理条款（本体）**：按 [governance/lifecycle-clauses.md](governance/lifecycle-clauses.md) 给你的 skill 台账挂降档时钟、统一调用计数口径、落实登记三防——这是版本 pin / 分发同步类官方工具不覆盖的层：资产何时该退役、退役依据记账是否可信。

2. **一致性校验器（随附）**：把各 Agent 端的 skills 目录以链接方式指向你的唯一正本目录，然后：

   ```bash
   python tools/sync_check.py --source ./skills --mount-a <AGENT_HOME_A>/skills --mount-b <AGENT_HOME_B>/skills
   ```

   亦支持环境变量 `GOV_SKILL_SOURCE / GOV_MOUNT_A / GOV_MOUNT_B`（命令行优先）。输出含遮蔽检测（字节一致/仅行尾差异/内容分叉/**SUSPENDED 无法检查**四档判定——不可读文件不冒充一致结论）、悬空链接与挂载分布报表。要求 Python >= 3.12；同时识别 Windows junction 与 Unix symlink。设计依据、禁忌与负例覆盖面清单见 [governance/junction-discipline.md](governance/junction-discipline.md)。

   **选型边界**：若你的场景是"从外部安装 skill 并跟踪版本"，官方 `gh skill`（版本 pin/provenance）更合适；本校验器针对**自建正本、多端挂载**场景——官方工具不管这种拓扑的一致性。

3. **模板**：`templates/` 内两个 SKILL.md 为通用 Agent 技能格式（frontmatter + 正文路由器），替换占位符后接入你自己的 agent 技能目录。

## 占位符对照表

模板与文档中的 `<...>` 变量含义如下，替换为自家路径即可：

| 占位符 | 含义 |
|---|---|
| `<YOUR_VAULT_PATH>` | 你的知识库（如 Obsidian vault）根目录 |
| `<YOUR_SCRIPTS_DIR>` | 工具脚本存放目录（原体系的 `脚本/`） |
| `<YOUR_WORKBENCH>` | 运行台/工作台目录（预览站点、临时产物根） |
| `<YOUR_AI_HUB>` | 知识库内 AI 机制/检验报告分区的目录名 |
| `<AGENT_HOME_A>` / `<AGENT_HOME_B>` | 快速开始示例中的两个挂载端目录（A/B 为通用名） |
| `<AGENT_HOME_TRAE>` / `<AGENT_HOME_WB>` | 模板正文中按端名直呼的挂载端配置主目录（与 A/B 同义，保留具体端名作叙事锚点） |
| `<USER_HOME>` | 用户主目录（`~`） |
| `<WB_HOME>` | 某 Agent 端的工作数据目录（历史会话归档位） |
| `<PRIVATE_SYSTEM>` | 原体系关联的私有代码库（示例语境，替换为你自己的项目名） |
| `<YOUR_INDUSTRY>` | 模板示例中的行业画像，按实际替换 |
| `<YOUR_DOMAIN>` / `<YOUR_DOMAIN2>` | 知识库落位表示例中的业务分区名，替换为你的实际分区 |

模板内出现的 `AI-16`、`AI-1x` 等编号是**原体系规范文档编号的示例占位**（其正文未随本仓库发布），落位规则需替换为你自己的标准文档；未替换前，相关段落仅作结构参考，不具权威效力。

## 设计立场

- 正本唯一，多端只挂链接；副本制必漂移。
- 自动发现挂载，不维护硬编码名单。
- 跨端比对先归一化行尾再哈希；"字节一致"与"内容一致"分开报告。
- 记账口径先于数据修正；凭证不足不补数。
- 时钟到期只产默认案，不自动动手。

## 许可

- 代码（`tools/`）：[MIT](LICENSE)
- 文档与模板（`governance/`、`templates/`）：CC-BY-4.0（全文见 [LICENSE-CC-BY-4.0](LICENSE-CC-BY-4.0)）

## 状态

v0.1 —— 从生产环境提炼的首版，占位符化脱敏（经三轮独立审查）；issue 与 PR 欢迎，但请先读 governance/ 三文再提改动方案。
