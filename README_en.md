> English translation of README.md. The Chinese version is the source of truth; if they diverge, the Chinese version prevails.

# Agent Skill Governance Kit

A **lifecycle governance clause pack** for skill assets in multi-agent-endpoint environments: the demotion clock, the registration safeguards, and the bookkeeping discipline form the core, accompanied by a cross-endpoint canonical-source-tree mount consistency checker and ingest / re-review templates.

This repository addresses one concrete incident pattern: once the same skill set is loaded by multiple agent endpoints, copies drift, retirements lack grounds, and the bookkeeping behind those grounds becomes untrustworthy. The three artifact layers each target one class of incident: the clauses (lifecycle-clauses) govern when an asset retires and whether the evidence for retirement is credible, the checker (sync_check) guards mount-topology consistency, and the templates close the session-cleanup loop. The clauses all originate from repeated real-world production stumbles (the CHANGELOG records this repository's own build and errata history; the clause-to-incident mapping table lives in the original system's internal ledger and is not published with this repository, so no per-clause traceability is asserted here) — which is also where this pack differs from orchestration frameworks and distribution tools: those layers solve "how to organize and sync", this one solves "how to retire, and whether the case for retirement holds up".

## Directory Structure

```
agent-governance/
├── README.md / LICENSE / CHANGELOG.md
├── docs/
│   ├── paradigm.md            # Governance paradigm map: five layers + shared axioms + applicability boundary (read first)
│   └── proposals/             # Proposal drafts (pending/adjudicated, e.g. v0.1.5 borrowed clauses)
├── tools/
│   ├── sync_check.py          # Cross-endpoint mount consistency checker (read-only, pure stdlib, Python>=3.12)
│   └── sync_check_selftest.py # 16-case regression selftest for the checker (wired into CI)
├── governance/
│   ├── junction-discipline.md # Canonical-source + link-mount model, four disciplines, checker design rationale
│   ├── lifecycle-clauses.md   # Demotion clock / demand-authenticity gauges / registration safeguards / council governance / learning conversion, etc.
│   └── closure-workflow.md    # Four-step session-closure loop (summarize → distill → ingest decision → light re-review)
└── templates/
    ├── kb-ingest-gate/        # Knowledge-base ingest gate (anti-duplication, placement-rule linking, re-review closure)
    └── three-ruler-review/    # Three-ruler re-review + gap-filling + plan iteration template
```

## Quick Start

1. **Governance clauses (the core)**: Following [governance/lifecycle-clauses.md](governance/lifecycle-clauses.md), attach demotion clocks to your skill ledger, unify the call-counting standard, and implement the registration safeguards — this is the layer official version-pin / distribution-sync tools do not cover: when an asset should retire, and whether the bookkeeping of its retirement basis is trustworthy.

2. **Consistency checker (bundled)**: Point each agent endpoint's skills directory at your single canonical source tree via links, then:

   ```bash
   python tools/sync_check.py --source ./skills --mount-a <AGENT_HOME_A>/skills --mount-b <AGENT_HOME_B>/skills
   ```

   Environment variables `GOV_SKILL_SOURCE / GOV_MOUNT_A / GOV_MOUNT_B` are also supported (command-line arguments take precedence). The output includes shadowing detection (four-way verdict: byte-identical / line-ending-only difference / content divergence / SUSPENDED-unverifiable, where unreadable files never masquerade as a positive match), link-side read-integrity checks (unreadable files behind a link, or links with no verifiable files, are likewise reported), dangling links, same-endpoint duplicate-mount detection, and a mount distribution report; misconfigured arguments (both endpoints on the same path / an endpoint equal to the source) exit with code 2. Requires Python >= 3.12; recognizes both Windows junctions and Unix symlinks. For design rationale, prohibitions, and the negative-vector coverage list, see [governance/junction-discipline.md](governance/junction-discipline.md).

   **Selection boundary**: if your scenario is "installing skills from outside and tracking versions", the official `gh skill` (version pin/provenance) fits better; this checker targets the **self-built canonical source tree, multi-endpoint mount** scenario — official tools do not handle consistency for this topology.

3. **Templates**: the two SKILL.md files under `templates/` use the generic agent skill format (frontmatter + body router); replace the placeholders and wire them into your own agent skill directory.

## Placeholder Reference

The `<...>` variables in templates and documents mean the following; replace them with your own paths:

| Placeholder | Meaning |
|---|---|
| `<YOUR_VAULT_PATH>` | Root directory of your knowledge base (e.g. an Obsidian vault) |
| `<YOUR_SCRIPTS_DIR>` | Directory for tool scripts (the original system's `脚本/`) |
| `<YOUR_WORKBENCH>` | Workbench directory (root for preview sites and temporary artifacts) |
| `<YOUR_AI_HUB>` | Directory name of the AI-mechanism / verification-report partition in your knowledge base |
| `<AGENT_HOME_A>` / `<AGENT_HOME_B>` | The two mount-endpoint directories in the Quick Start example (A/B are generic names) |
| `<AGENT_HOME_TRAE>` / `<AGENT_HOME_WB>` | Mount-endpoint configuration home directories named after specific endpoints in template bodies (synonymous with A/B; concrete endpoint names kept as narrative anchors) |
| `<USER_HOME>` | User home directory (`~`) |
| `<WB_HOME>` | One agent endpoint's working-data directory (archive location for historical sessions) |
| `<PRIVATE_SYSTEM>` | The private code repository associated with the original system (example context; replace with your own project name) |
| `<YOUR_INDUSTRY>` | Industry profile in the template examples; replace with your actual one |
| `<YOUR_DOMAIN>` / `<YOUR_DOMAIN2>` / `<YOUR_DOMAIN3>` | Business partition names in the knowledge-base placement table examples; replace with your actual partitions |
| `<YOUR_NOTES_DIR>` / `<YOUR_METHOD_DIR>` | Notes-area / methodology-area directory names (path example for the connection health-check sheet) |

Identifiers such as `AI-16` and `AI-1x` appearing in the templates are **example placeholders for the original system's specification document numbers** (whose bodies are not published with this repository); the placement rules must be replaced with your own standard documents. Until replaced, the relevant paragraphs serve as structural reference only and carry no authoritative force.

## Design Stance

- One canonical source tree; endpoints only mount links. A copy-based setup will drift.
- Mounts are discovered automatically; no hard-coded list is maintained.
- Cross-endpoint comparison normalizes line endings before hashing; "byte-identical" and "content-identical" are reported separately.
- Bookkeeping discipline comes before data correction; never backfill without sufficient evidence.
- An expired clock only produces a default proposal; it never acts on its own.

## License

- Code (`tools/`): [MIT](LICENSE)
- Documentation and templates (`governance/`, `templates/`): CC-BY-4.0 (full text in [LICENSE-CC-BY-4.0](LICENSE-CC-BY-4.0))

## Status

v0.1.5.2 — distilled from production, desensitized via placeholderization (after six rounds of independent review, including live negative-case probes and public-surface forensics); v0.1.5 absorbed externally benchmarked clauses (SUSPENDED semantics / negative-consistency vectors / pre-execution re-check), v0.1.5.1 fixed three checker defects found by adversarial review: silent missed detection in the link branch (V1), nested links inside the canonical tree missed (V2), missing argument-precondition validation (V4), v0.1.5.2 fixed the CI lint substring false-green, added regression cases for the negative-vector checklist (case11-14), and completed template desensitization. Issues and PRs are welcome, but read the three documents under governance/ before proposing changes.
