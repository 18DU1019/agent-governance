# Agent Skill Governance Kit

多 Agent 端环境下 skill 资产的**治理工具箱**：跨端正本挂载一致性校验 + 生命周期条款 + 入库/复检模板。

主流 Agent 框架解决"怎么编排 skill"，本仓库解决其后的两个空白层：**skill 资产何时退役（生命周期）**、**退役依据的记账是否可信（一致性）**。两者都源自真实生产体系的事故教训，而非纸面设计。

## 目录结构

```
agent-governance/
├── README.md / LICENSE / CHANGELOG.md
├── docs/
│   └── paradigm.md            # 治理范式图谱：五层范式 + 共享公理 + 适用边界（建议先读）
├── tools/
│   └── sync_check.py          # 跨端挂载一致性校验器（只读，纯 stdlib，Python>=3.12）
├── governance/
│   ├── junction-discipline.md # 正本+链接挂载模型与四条纪律、校验器设计依据
│   ├── lifecycle-clauses.md   # 降档时钟/需求真伪检具/登记三防/合议治理/学习转化等条款
│   └── closure-workflow.md    # 会话收尾四步闭环（汇总→蒸馏→入库判定→轻复检）
└── templates/
    ├── kb-ingest-gate/        # 知识库入库闸门（防复制品、按落位规则接链、复检闭环）
    └── three-ruler-review/    # 三标尺复检+联网查漏+方案迭代模板
```

## 快速开始

1. **校验器**：把各 Agent 端的 skills 目录以链接方式指向你的唯一正本目录，然后：

   ```bash
   python tools/sync_check.py --source ./skills --mount-a <AGENT_HOME_A>/skills --mount-b <AGENT_HOME_B>/skills
   ```

   亦支持环境变量 `GOV_SKILL_SOURCE / GOV_MOUNT_A / GOV_MOUNT_B`（命令行优先）。输出含遮蔽检测、链接名一致性与挂载分布报表。设计依据与禁忌见 [governance/junction-discipline.md](governance/junction-discipline.md)。

   **平台说明**：要求 Python >= 3.12；同时识别 Windows junction 与 Unix symlink 两种挂载形态。

2. **治理条款**：按 [governance/lifecycle-clauses.md](governance/lifecycle-clauses.md) 给你的 skill 台账挂降档时钟、统一调用计数口径。

3. **模板**：`templates/` 内两个 SKILL.md 为通用 Agent 技能格式（frontmatter + 正文路由器），替换占位符后接入你自己的 agent 技能目录。

## 占位符对照表

模板与文档中的 `<...>` 变量含义如下，替换为自家路径即可：

| 占位符 | 含义 |
|---|---|
| `<YOUR_VAULT_PATH>` | 你的知识库（如 Obsidian vault）根目录 |
| `<YOUR_SCRIPTS_DIR>` | 工具脚本存放目录（原体系的 `脚本/`） |
| `<YOUR_WORKBENCH>` | 运行台/工作台目录（预览站点、临时产物根） |
| `<YOUR_WORKSPACE>` | 工作区根目录 |
| `<AGENT_HOME_TRAE>` / `<AGENT_HOME_WB>` | 各 Agent 端的配置主目录（挂载端所在） |
| `<USER_HOME>` | 用户主目录（`~`） |
| `<WB_HOME>` | 某 Agent 端的工作数据目录（历史会话归档位） |
| `<PRIVATE_SYSTEM>` | 原体系关联的私有代码库（示例语境，替换为你自己的项目名） |
| `<YOUR_CITY>` / `<YOUR_INDUSTRY>` | 模板示例中的地域/行业画像，按实际替换 |
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
- 文档与模板（`governance/`、`templates/`）：CC-BY-4.0

## 状态

v0.1 —— 从生产环境提炼的首版，占位符化脱敏（经三轮独立审查）；issue 与 PR 欢迎，但请先读 governance/ 三文再提改动方案。
