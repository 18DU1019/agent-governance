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
注意：链接侧不比对内容哈希摘要——链接读到的就是正本，同义反复无检测力；
链接侧只做读取完整性判定（不可读计数 / 可校验文件数），内容比对仅用于遮蔽项（实体副本）。

检查项:
  1. 正本目录树内（含子目录）不得出现任何链接（纪律1：防循环扫描；rglob 递归判定）
  2. 两端链接：目标须落在正本目录内（严格父子路径判定，防旁支前缀绕过），
     且链接名与正本目录名一致；透过链接存在不可读文件时判 SUSPENDED，
     链接侧无可校验文件时判 FAIL（不冒充一致结论）
  3. 两端实体目录：与正本同名者判 FAIL（遮蔽），附内容相同/分叉判定
  4. 参数前提：--mount-a / --mount-b / --source 两两不同（resolve 后比较），
     配错即退出码 2（防止同路径双端拿到假绿）

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
    """整棵子树哈希，返回 (原始字节摘要, 行尾归一化摘要, 文件数, 不可读文件数)。排除安装元数据与缓存。

    双档摘要：跨工具链的 CRLF/LF 差异会制造"字节不同、内容相同"的伪分叉，
    只有原始档与归一档分开比对，才能区分真分叉与行尾噪声。
    不可读计数（v0.1.5 借件 SUSPENDED 语义）：占位符哈希不再参与"一致"判定——
    任一侧存在不可读文件时，内容判定输出 SUSPENDED（无法检查），不冒充字节一致/内容一致。
    """
    raw = hashlib.sha256()
    norm = hashlib.sha256()
    n = 0
    bad = 0
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
            bad += 1
        ndata = data.replace(b"\r\n", b"\n")
        # 长度前缀消歧（v0.1.5 C3）：纯 \0 分隔在 data 含 \0 时可跨文件边界构造碰撞，
        # 改 len 前缀使 rel/data 边界唯一可解析。哈希值与旧版不兼容属正常——
        # 校验器每次全量自产比对，无跨版本持久化摘要。
        raw.update(len(rel).to_bytes(8, "big")); raw.update(rel)
        raw.update(len(data).to_bytes(8, "big")); raw.update(data)
        norm.update(len(rel).to_bytes(8, "big")); norm.update(rel)
        norm.update(len(ndata).to_bytes(8, "big")); norm.update(ndata)
        n += 1
    return (raw.hexdigest() if n else None), (norm.hexdigest() if n else None), n, bad


def main(argv=None) -> int:
    args = parse_args(argv)
    HUB = Path(args.source)
    ENDS = {
        "A": Path(args.mount_a),
        "B": Path(args.mount_b),
    }

    # 参数前提：空字符串路径（env 设为空串的常见配错）不猜——Path("") 会静默变 cwd。
    for flag, val in (("--source", args.source), ("--mount-a", args.mount_a),
                      ("--mount-b", args.mount_b)):
        if val == "":
            print("ERROR: 参数前提不满足（运行环境不满足）")
            print(f" - {flag} 为空字符串（环境变量被设为空？请 unset 或给显式路径）")
            return 2

    # 参数前提校验（v0.1.5.1）：同路径双端 / 挂载端=正本 均属配错，
    # 不校验会让用户拿到假绿或误导性"遮蔽"报告。resolve 后比较，不要求路径存在。
    try:
        rp = {name: p.resolve() for name, p in {"SOURCE": HUB, **ENDS}.items()}
    except OSError as e:
        print("ERROR: 路径解析失败（运行环境不满足）")
        print(f" - {e}")
        return 2
    seen = {}
    for name, p in rp.items():
        if p in seen:
            print("ERROR: 参数前提不满足（运行环境不满足）")
            print(f" - {name} 与 {seen[p]} 指向同一路径: {p}")
            return 2
        seen[p] = name

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

    # 1. 正本树内（含任意深度子目录）不得有链接（纪律1"任何链接"的机械承载）。
    #    用 os.walk(followlinks=False) 而非 Path.rglob——rglob 在部分 Python 版本
    #    会跟随链接进入目录树，触发本条纪律要防的循环扫描。
    try:
        for dirpath, dirnames, filenames in os.walk(HUB):
            for name in list(dirnames):
                d = Path(dirpath) / name
                if is_link(d):
                    problems.append(f"[正本污染] {d.relative_to(HUB).as_posix()} 是链接, 正本内禁止")
                    dirnames.remove(name)  # 不再深入链接子树
            # 文件级链接同样禁止（纪律1"任何链接"含文件级）：tree_hash 的 rglob
            # 会透过文件级链接读树外内容计入正本哈希，"正本自包含"假设随之破裂。
            for name in filenames:
                fp = Path(dirpath) / name
                if is_link(fp):
                    problems.append(
                        f"[正本污染] {fp.relative_to(HUB).as_posix()} 是文件级链接, 正本内禁止")
    except OSError as e:
        problems.append(f"[正本污染] 扫描中断: {e}")

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
            link_mode = is_link(x)
            if link_mode:
                try:
                    is_dir_target = x.is_dir()
                except OSError as e:
                    problems.append(f"[{end}] {x.name}: 链接状态不可判定 ({e})")
                    continue
                if not is_dir_target:
                    problems.append(
                        f"[{end}] {x.name}: 链接目标不可用（不存在或不是目录，"
                        "挂载项须为目录链接）")
                    continue
                try:
                    tgt = Path(os.path.realpath(x))
                except OSError as e:
                    problems.append(f"[{end}] {x.name}: 链接目标解析失败 ({e})")
                    continue
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
                # 读取完整性判定（v0.1.5.1 修复 V1）：透过链接读正本，
                # 不可读文件必须显式报出——SUSPENDED 不得只活在遮蔽分支里。
                # 旧版以 "链接侧 n==0 而正本 n>0" 作静默失败判据，该条件对合法链接恒 False
                # （链接读的就是正本同一批文件），属死代码；改为直接消费 bad 计数与 n 计数。
                _, _, n_x, bad_x = tree_hash(x)
                if bad_x > 0:
                    problems.append(
                        f"[{end}] {x.name}: SUSPENDED 透过链接存在不可读文件 ({bad_x} 个)，"
                        "无法校验内容，需修复读取权限后复检")
                    continue
                if n_x == 0:
                    problems.append(
                        f"[{end}] {x.name}: 透过链接无可校验文件 "
                        "(正本项为空或内容全被忽略项，一致性结论无依据)")
                    continue
                if end in mounted[mname]:
                    problems.append(
                        f"[{end}] {x.name}: 同一端重复挂载同一正本 (多挂，违反自动发现唯一性)")
                else:
                    mounted[mname].append(end)
            else:
                try:
                    is_plain_dir = x.is_dir()
                except OSError as e:
                    problems.append(f"[{end}] {x.name}: 条目状态不可判定 ({e})")
                    continue
                if is_plain_dir and x.name not in masters:
                    # 孤立实体目录（第八轮 N8-1）：名不在正本、又是实体目录——
                    # 典型形态为正本退役后挂载端的实体复制残留，loader 照样加载僵尸 skill。
                    # 白名单原则：正本=封闭世界，skills 根下未登记实体目录即异常。
                    # 逃生通道：以 _ / . 开头的目录豁免（约定为非资产辅助目录）。
                    if not (x.name.startswith("_") or x.name.startswith(".")):
                        problems.append(
                            f"[{end}] {x.name}: 孤立实体目录（不在正本，疑似退役残留或未登记资产；"
                            "非资产辅助目录请以 _ 或 . 前缀命名豁免）")
                elif is_plain_dir and x.name in masters:
                    r, nm, n_x, bad_x = tree_hash(x)
                    mr, mn, n_m, bad_m = mh[x.name]
                    if bad_x > 0 or bad_m > 0:
                        verdict = (f"SUSPENDED 无法检查 (不可读文件: 副本 {bad_x} / 正本 {bad_m}，"
                                   "占位符不参与一致判定，需修复读取权限后复检)")
                    elif n_x == 0 or n_m == 0:
                        verdict = (f"无可校验文件 (副本 {n_x} / 正本 {n_m}，"
                                   "空项或内容全被忽略项，一致性结论无依据)")
                    elif r == mr:
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
