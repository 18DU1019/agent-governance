#!/usr/bin/env python3
"""desensitize_scan —— 脱敏验收的独立仪器（第二把尺子）。

为什么存在（根因，2026-10-04）：
    历史重写后曾自报"全历史 blob 终扫归零"，而 origin/master 仍含业务分区
    叶子名、私有脚本名、私有工具目录段等残留。根因是结构性的——清洗与验收
    共用同一套模式集：模式集没枚举到的形态，清洗漏改、验收也漏检，于是必然
    "自证归零"（口径律在机制层的复发）。本工具不复用任何"已知敏感字符串"清单，
    改按形态扫描 + 白名单反证（默认可疑、显式放行），与 denylist 清洗方向相反，
    故能补其漏。

与清洗仪器的正交性：
    清洗 = denylist：枚举已知敏感值 → 替换；缺什么漏什么。
    验收 = 本工具：形态匹配 + 白名单放行；默认可疑。
    两者失误方向相反，一方漏的由另一方补。

口径声明（公理 1 推论：完整性声明必带所扫集合口径）：
    覆盖形态类（见 _rules）：
      abs_path             盘符绝对路径
      home_dir             家目录段（类 Unix，且段名非占位符）
      partition_name       NN-中文 命名的分区目录
      placeholder_literal  占位符之后紧跟的字面路径段
      dot_private_dir      点开头、非白名单的私有目录段
      underscore_dir       下划线开头的私有目录段
      script_name          非白名单的脚本可执行名
      email                邮箱（example.com 放行）
      phone_cn             中国大陆手机号
      ipv4                 IPv4（环回/全零放行）
    已知不覆盖（残余面，如实登记）：单独出现、无路径上下文的中文私有专名——
    结构上与公开中文词汇不可分，须人工/模型通读兜底；本工具零命中不为其作证。
    扫描对象：仓根下文本文件（跳过 VCS 目录与二进制后缀），当前工作树层。
    故"通过"仅声明：上述形态类在**当前工作树文本层**零命中；不声明历史层、
    不声明未列形态、不声明非文本载体。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---- 白名单（显式放行的通用词；默认可疑是本工具的方向）--------------------
# 显式放行 = 口径（默认可疑是本工具的方向）：版本控制/编辑器/操作系统目录、
# 文件扩展名短 token、通用工具目录。放行项以外的点目录段一律视为可疑。
ALLOW_DOT_DIRS = {
    "git", "github", "vscode", "gitignore", "gitattributes",
    "obsidian", "ds_store", "pyc", "mypy_cache", "pytest_cache", "kb_archive",
    "md", "py", "yml", "yaml", "txt", "json", "toml", "cfg", "ini",
    "bat", "ps1", "sh", "exe", "html", "csv", "png", "jpg", "pdf", "lock",
    # workbuddy：宿主产品目录名，经 v0.1.5.2 裁定非 PII（产品名，其内真实
    # 用户名已随绝对路径规则洗除）；CHANGELOG 历史条目保留其字面。模板正文
    # 仍按占位符契约使用 <WB_HOME>（该处属"通用化"而非"保密"，两事分立）。
    "workbuddy",
}
ALLOW_SCRIPT_BASENAMES = {
    "sync_check.py", "sync_check_selftest.py", "desensitize_scan.py",
    "python.exe", "pip.exe", "git.exe",
}
ALLOW_EMAIL_DOMAINS = {"example.com"}
ALLOW_IPS = {"127.0.0.1", "0.0.0.0"}
# 占位符之后的路径段中，纯描述性的通用名词（非私有标识）显式放行
ALLOW_LITERAL_SEGMENTS = {"子目录"}
ALLOW_UNDERSCORE_DIRS = {"_backup"}

TEXT_SUFFIXES = {
    ".md", ".py", ".yml", ".yaml", ".txt", ".json", ".toml", ".cfg",
    ".ini", ".sh", ".bat", ".ps1",
}
TEXT_NAMES = {"LICENSE", "LICENSE-CC-BY-4.0", ".gitignore", ".gitattributes"}
SKIP_DIRS = {".git", "__pycache__", ".mypy_cache", ".pytest_cache"}

_NO_PLACEHOLDER = r"(?!<)"

_RULES: list[tuple[str, re.Pattern[str]]] = [
    # 盘符绝对路径；负向先行断言排除紧贴字母的冒号斜杠（URL 形态），并放行后随占位符者
    ("abs_path", re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/](?![\\/<])")),
    # 类 Unix 家目录段；段名为占位符（<...>）时不匹配、故放行
    ("home_dir", re.compile(r"(?<![\w/])[/\\](?:Users|home)[/\\][A-Za-z0-9_.-]+")),
    # NN-中文 分区目录名（如某两位编号 + 中文）
    ("partition_name", re.compile(r"(?<![\w-])\d{2}-[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9]*")),
    # 占位符之后紧跟的字面路径段（捕获 = 未被占位符化的私有名）
    ("placeholder_literal", re.compile(r"<[A-Za-z0-9_]+>[\\/]([\u4e00-\u9fff][^\\/\s`<>|]*)")),
    # 点开头、非白名单的私有目录段；要求前导为分隔符/空白/反引号或行首，避开扩展名
    ("dot_private_dir", re.compile(r"(?:^|(?<=[\s/\\`\"'（(]))\.([A-Za-z][A-Za-z0-9_-]{2,})(?![\w(])")),
    # 下划线开头的私有目录段（如某 Agent 记忆目录）
    ("underscore_dir", re.compile(r"(?<![\w/\\])(_[a-z][a-z0-9_]*)[/\\]")),
    # 非白名单脚本/可执行名（允许通配符）
    ("script_name", re.compile(r"(?<!\w)([A-Za-z_][A-Za-z0-9_*]*\.(?:py|bat|ps1|cmd|sh|exe))(?![\w])")),
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("phone_cn", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("ipv4", re.compile(r"(?<![vV\d.])\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?![\d.])")),
]


def _hit(label: str, match: re.Match[str]) -> bool:
    """按白名单裁定命中是否成立（True = 可疑，保留）。"""
    if label == "dot_private_dir":
        return match.group(1).lower() not in ALLOW_DOT_DIRS
    if label == "placeholder_literal":
        return match.group(1) not in ALLOW_LITERAL_SEGMENTS
    if label == "underscore_dir":
        return match.group(1) not in ALLOW_UNDERSCORE_DIRS
    if label == "script_name":
        return match.group(1).lower() not in {s.lower() for s in ALLOW_SCRIPT_BASENAMES}
    if label == "email":
        return match.group(0).split("@", 1)[1].lower() not in ALLOW_EMAIL_DOMAINS
    if label == "ipv4":
        return match.group(0) not in ALLOW_IPS
    return True


def scan_text(text: str) -> list[tuple[int, str, str]]:
    """对一段文本逐行扫描，返回 (行号, 形态类, 命中串) 列表。"""
    out: list[tuple[int, str, str]] = []
    for i, line in enumerate(text.splitlines(), 1):
        for label, pat in _RULES:
            for m in pat.finditer(line):
                if _hit(label, m):
                    out.append((i, label, m.group(0)))
    return out


def _iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in TEXT_SUFFIXES or p.name in TEXT_NAMES:
            yield p


def run(root: Path) -> int:
    total = 0
    for path in _iter_files(root):
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError as exc:  # 不可读是异常，显式报出，不静默跳过
            print(f"[UNREADABLE] {path}: {exc}")
            total += 1
            continue
        for lineno, label, frag in scan_text(text):
            print(f"{path.relative_to(root)}:{lineno}:{label}: {frag}")
            total += 1
    print("---")
    print(f"coverage: {'/'.join(lbl for lbl, _ in _RULES)}")
    print("residual: 单独出现、无路径上下文的中文私有专名（须人工/模型通读兜底）")
    print("scope: 当前工作树文本层；不含 git 历史层、非文本载体、未列形态")
    print(f"TOTAL {total}")
    return 1 if total else 0


# ---- 自测：证明仪器本身不假绿（构造串用拼接，避免自身被扫出）---------------
def selftest() -> int:
    # 所有样本用拼接构造，避免本文件源码被自身规则扫出（仪器须自证干净）
    drive = chr(67) + ":" + chr(92) + "Users" + chr(92) + "bob"
    part = "07-" + "\u91d1\u878d"
    ph_lit = "<YOUR_VAULT_PATH>/" + "\u91cf\u5316\u4ea4\u6613" + "/"
    dot = chr(46) + "myva" + "ult"            # 非白名单私有目录
    dot_wb = chr(46) + "work" + "bud" + "dy"  # 白名单放行项（宿主产品目录）
    scr = "grow" + "_moc" + chr(46) + "py"
    wild = "kb_tags" + "_bulk" + chr(42) + chr(46) + "py"
    bad = {
        "abs_path": [drive],
        "home_dir": [chr(47) + "Users" + chr(47) + "bob",
                     chr(47) + "home" + chr(47) + "alice"],
        "partition_name": [part],
        "placeholder_literal": [ph_lit],
        "dot_private_dir": ["path " + dot + " dir"],  # 非白名单私有目录应命中
        "script_name": [scr, wild],
        "email": ["a" + chr(64) + "qq" + chr(46) + "com"],
        "phone_cn": ["138" + "00138000"],
        "ipv4": ["10" + chr(46) + "1" + chr(46) + "2" + chr(46) + "3"],
    }
    good = [
        "C:" + "\\" + "<USER_HOME>" + " path placeholder",
        "<YOUR_VAULT_PATH>/preview/",
        "sync_check.py is allowlisted",
        "dev" + "@" + "example.com",
        "127.0.0.1:8765 local service",
        "-v0.1.5.2 version tag",
        "path " + dot_wb + " dir is allowlisted",  # 白名单项应放行
    ]
    failures = 0
    for label, samples in bad.items():
        for s in samples:
            labels = {lbl for _, lbl, _ in scan_text(s)}
            if label not in labels:
                print(f"SELFTEST FAIL 应命中未命中 [{label}] {s!r} got={labels}")
                failures += 1
    for s in good:
        hits = scan_text(s)
        if hits:
            print(f"SELFTEST FAIL 放行项被误报 {s!r} -> {hits}")
            failures += 1
    print("selftest " + ("OK" if not failures else f"FAIL({failures})"))
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="脱敏验收的独立形态扫描仪器")
    ap.add_argument("--root", default=None, help="扫描根目录，默认=仓根")
    ap.add_argument("--selftest", action="store_true", help="仅跑仪器自测")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    if not root.is_dir():
        print(f"扫描根不存在或不是目录: {root}")
        return 2
    if sys.version_info < (3, 12):
        print("需要 Python >= 3.12")
        return 2
    return run(root)


if __name__ == "__main__":
    sys.exit(main())