# -*- coding: utf-8 -*-
"""sync_check.py — 跨 Agent skill 正本挂载一致性校验器（只读，纯 stdlib）

要求 Python >= 3.12（唯一版本敏感点：Path.is_junction；其余 API 均为 3.4 级基础件）。

路径配置（环境变量 + 命令行覆盖，命令行优先）:
  正本 source 目录:  GOV_SKILL_SOURCE / --source    默认 ./skills
  挂载端 A:          GOV_MOUNT_A      / --mount-a   默认 ../agent-a/skills
  挂载端 B:          GOV_MOUNT_B      / --mount-b   默认 ../agent-b/skills

设计依据见 governance/junction-discipline.md 第三节：
  1. 自动发现挂载，不维护硬编码名单（名单制无法发现漏挂/多挂）。
  2. 遮蔽检测：某端存在与正本同名的实体目录即报警，并判定内容相同/分叉。
  3. 链接名一致性：链接名与正本目录名不符时报错。
  4. 挂载分布报表（信息项，不判 FAIL）。

挂载形态同时识别 Windows junction 与 Unix symlink。
注意：一致性判定不透过链接比哈希——链接读到的就是正本，同义反复无检测力；
整树哈希只用于遮蔽项（实体副本）的内容判定。

检查项:
  1. 正本目录内不得出现链接（纪律1：防循环扫描）
  2. 两端链接：目标须落在正本目录内（严格父子路径判定，防旁支前缀绕过），
     且链接名与正本目录名一致
  3. 两端实体目录：与正本同名者判 FAIL（遮蔽），附内容相同/分叉判定

用法: python sync_check.py [--source DIR] [--mount-a DIR] [--mount-b DIR]
      (退出码 0=全部通过, 1=存在异常, 2=运行环境不满足)
"""
import argparse
import hashlib
import os
import sys
from pathlib import Path

if sys.version_info < (3, 12):
    print("ERROR: sync_check.py requires Python >= 3.12 (Path.is_junction)")
    sys.exit(2)

DEFAULT_SOURCE = os.environ.get("GOV_SKILL_SOURCE", "./skills")
DEFAULT_MOUNT_A = os.environ.get("GOV_MOUNT_A", "../agent-a/skills")
DEFAULT_MOUNT_B = os.environ.get("GOV_MOUNT_B", "../agent-b/skills")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="跨 Agent skill 正本挂载一致性校验")
    ap.add_argument("--source", default=DEFAULT_SOURCE,
                    help="正本 skills 目录 (env: GOV_SKILL_SOURCE)")
    ap.add_argument("--mount-a", default=DEFAULT_MOUNT_A,
                    help="挂载端 A 的 skills 目录 (env: GOV_MOUNT_A)")
    ap.add_argument("--mount-b", default=DEFAULT_MOUNT_B,
                    help="挂载端 B 的 skills 目录 (env: GOV_MOUNT_B)")
    return ap.parse_args(argv)

IGNORE_NAMES = {"_skillhub_meta.json", ".DS_Store"}
IGNORE_PARTS = {"__pycache__"}


def is_link(p: Path) -> bool:
    """junction（Windows）或 symlink（跨平台）均视为链接挂载。"""
    try:
        return p.is_junction() or p.is_symlink()
    except OSError:
        return False


def tree_hash(p: Path):
    """整棵子树哈希，返回 (原始字节摘要, 行尾归一化摘要, 文件数)。排除安装元数据与缓存。

    双档摘要：跨工具链的 CRLF/LF 差异会制造"字节不同、内容相同"的伪分叉，
    只有原始档与归一档分开比对，才能区分真分叉与行尾噪声。
    """
    raw = hashlib.sha256()
    norm = hashlib.sha256()
    n = 0
    for f in sorted(p.rglob("*")):
        if not f.is_file():
            continue
        if f.name in IGNORE_NAMES or f.suffix == ".pyc":
            continue
        if any(part in IGNORE_PARTS for part in f.relative_to(p).parts):
            continue
        rel = f.relative_to(p).as_posix().encode("utf-8")
        try:
            data = f.read_bytes()
        except OSError:
            data = b"<unreadable>"
        raw.update(rel); raw.update(b"\0"); raw.update(data); raw.update(b"\0")
        ndata = data.replace(b"\r\n", b"\n")
        norm.update(rel); norm.update(b"\0"); norm.update(ndata); norm.update(b"\0")
        n += 1
    return (raw.hexdigest() if n else None), (norm.hexdigest() if n else None), n


def main(argv=None) -> int:
    args = parse_args(argv)
    HUB = Path(args.source)
    ENDS = {
        "A": Path(args.mount_a),
        "B": Path(args.mount_b),
    }

    if not HUB.is_dir():
        print("FAIL")
        print(f" - 正本目录不存在或不是目录: {HUB}")
        return 1

    problems = []
    hub_real = Path(os.path.realpath(HUB))

    try:
        hub_items = [d for d in sorted(HUB.iterdir()) if d.is_dir()]
    except OSError as e:
        print("FAIL")
        print(f" - 正本目录不可读: {HUB} ({e})")
        return 1

    # 1. 正本内不得有链接
    for d in hub_items:
        if is_link(d):
            problems.append(f"[正本污染] {d.name} 是链接, 正本内禁止")

    masters = {d.name: d for d in hub_items if not is_link(d)}
    mh = {name: tree_hash(p) for name, p in masters.items()}

    # 2 + 3. 两端逐项检查
    mounted = {name: [] for name in masters}
    for end, base in ENDS.items():
        if not base.exists():
            problems.append(f"[{end}] 目录不存在: {base}")
            continue
        try:
            entries = sorted(base.iterdir())
        except OSError as e:
            problems.append(f"[{end}] 目录不可读: {base} ({e})")
            continue
        for x in entries:
            if is_link(x):
                if not x.is_dir():
                    problems.append(f"[{end}] {x.name}: 悬空链接 (目标不存在)")
                    continue
                tgt = Path(os.path.realpath(x))
                # 严格父子判定：tgt 必须等于正本或在正本目录树内。
                # 禁止用 startswith 字符串前缀——可被同名旁支目录绕过。
                if not (tgt == hub_real or hub_real in tgt.parents):
                    problems.append(f"[{end}] {x.name}: 链接指向非正本 ({tgt})")
                    continue
                mname = tgt.name
                if mname not in masters:
                    problems.append(f"[{end}] {x.name}: 指向的正本项不存在 ({mname})")
                    continue
                if x.name != mname:
                    problems.append(f"[{end}] {x.name}: 链接名与正本目录名不一致 ({mname})")
                if tree_hash(x)[2] == 0 and mh[mname][2] > 0:
                    problems.append(f"[{end}] {x.name}: 透过链接读不到任何文件 (静默失败)")
                    continue
                mounted[mname].append(end)
            elif x.is_dir():
                if x.name in masters:
                    r, nm, _ = tree_hash(x)
                    mr, mn, _ = mh[x.name]
                    if r == mr:
                        verdict = "字节一致 (可安全改链接)"
                    elif nm == mn:
                        verdict = "内容一致仅行尾差异 (可安全改链接)"
                    else:
                        verdict = "内容分叉 (需裁定)"
                    problems.append(
                        f"[{end}] {x.name}: 实体副本遮蔽正本同名项, {verdict}")

    if problems:
        print("FAIL")
        for p in problems:
            print(" -", p)
        print()
        print(f"正本 {len(masters)} 项, 异常 {len(problems)} 条")
        return 1

    full = [n for n in mounted if len(mounted[n]) == 2]
    single = [(n, mounted[n][0]) for n in sorted(mounted) if len(mounted[n]) == 1]
    ghost = [n for n in sorted(mounted) if not mounted[n]]

    print(f"PASS: 正本 {len(masters)} 项; 两端链接均指向正本且链接名一致")
    print(f"挂载分布: 两端皆挂 {len(full)} 项 / 单端挂载 {len(single)} 项 / 未被任何端挂载 {len(ghost)} 项")
    for name, end in single:
        print(f"  - 单端挂载: {name} 仅 {end}")
    for name in ghost:
        print(f"  - 未挂载: {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
