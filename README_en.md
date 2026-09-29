> English translation of README.md. The Chinese version is the source of truth; if they diverge, the Chinese version prevails.

# Agent Skill Governance Kit

A **lifecycle governance clause pack** for skill assets in multi-agent-endpoint environments: the demotion clock, the registration safeguards, and the bookkeeping discipline form the core, accompanied by a cross-endpoint canonical-source-tree mount consistency checker and ingest / re-review templates.

Mainstream frameworks solve "how to orchestrate skills", and official tools (gh skill, Anthropic organization sync) already cover "distribution and version consistency"; this repository builds the layer official tools have no incentive to build — **when a skill asset retires (clauses)** and **whether the bookkeeping behind a retirement decision is trustworthy (bookkeeping discipline and registration safeguards)**. Platforms will not decide asset retirement on the user's behalf; that is exactly the ecological niche of the clause layer. Every clause comes from a real production-incident lesson, not from paper design.

## Directory Structure

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

## Quick Start

1. **Governance clauses (the core)**: Following [governance/lifecycle-clauses.md](governance/lifecycle-clauses.md), attach demotion clocks to your skill ledger, unify the call-counting standard, and implement the registration safeguards — this is the layer official version-pin / distribution-sync tools do not cover: when an asset should retire, and whether the bookkeeping of its retirement basis is trustworthy.

2. **Consistency checker (bundled)**: Point each agent endpoint's skills directory at your single canonical source tree via links, then:

   ```bash
   python tools/sync_check.py --source ./skills --mount-a <AGENT_HOME_A>/skills --mount-b <AGENT_HOME_B>/skills
   ```

   Environment variables `GOV_SKILL_SOURCE / GOV_MOUNT_A / GOV_MOUNT_B` are also supported (command-line arguments take precedence). The output includes shadowing detection (three-tier verdict: byte-identical / line-ending-only difference / content divergence), dangling links, and a mount distribution report. Requires Python >= 3.12; recognizes both Windows junctions and Unix symlinks. For design rationale and prohibitions, see [governance/junction-discipline.md](governance/junction-discipline.md).

   **Selection boundary**: if your scenario is "installing skills from outside and tracking versions", the official `gh skill` (version pin/provenance) fits better; this checker targets the **self-built canonical source tree, multi-endpoint mount** scenario — official tools do not handle consistency for this topology.

3. **Templates**: the two SKILL.md files under `templates/` use the generic agent skill format (frontmatter + body router); replace the placeholders and wire them into your own agent skill directory.

## Placeholder Reference

The `<...>` variables in templates and documents mean the following; replace them with your own paths:

| Placeholder | Meaning |
|---|---|
| `<YOUR_VAULT_PATH>` | Root directory of your knowledge base (e.g. an Obsidian vault) |
| `<YOUR_SCRIPTS_DIR>` | Directory for tool scripts (the original system's `脚本/`) |
| `<YOUR_WORKBENCH>` | Workbench directory (root for preview sites and temporary artifacts) |
| `<AGENT_HOME_A>` / `<AGENT_HOME_B>` | The two mount-endpoint directories in the Quick Start example (A/B are generic names) |
| `<AGENT_HOME_TRAE>` / `<AGENT_HOME_WB>` | Mount-endpoint configuration home directories named after specific endpoints in template bodies (synonymous with A/B; concrete endpoint names kept as narrative anchors) |
| `<USER_HOME>` | User home directory (`~`) |
| `<WB_HOME>` | One agent endpoint's working-data directory (archive location for historical sessions) |
| `<PRIVATE_SYSTEM>` | The private code repository associated with the original system (example context; replace with your own project name) |
| `<YOUR_INDUSTRY>` | Industry profile in the template examples; replace with your actual one |
| `<YOUR_DOMAIN>` / `<YOUR_DOMAIN2>` | Business partition names in the knowledge-base placement table examples; replace with your actual partitions |

Identifiers such as `AI-16` and `AI-1x` appearing in the templates are **example placeholders for the original system's specification document numbers** (whose bodies are not published with this repository); the placement rules must be replaced with your own standard documents. Until replaced, the relevant paragraphs serve as structural reference only and carry no authoritative force.

## Design Stance

- One canonical source tree; endpoints only mount links. A copy-based setup will drift.
- Mounts are discovered automatically; no hard-coded list is maintained.
- Cross-endpoint comparison normalizes line endings before hashing; "byte-identical" and "content-identical" are reported separately.
- Bookkeeping discipline comes before data correction; never backfill without sufficient evidence.
- An expired clock only produces a default proposal; it never acts on its own.

## License

- Code (`tools/`): [MIT](LICENSE)
- Documentation and templates (`governance/`, `templates/`): CC-BY-4.0

## Status

v0.1 — the first edition distilled from production, desensitized via placeholderization (after three rounds of independent review); issues and PRs are welcome, but read the three documents under governance/ before proposing changes.
