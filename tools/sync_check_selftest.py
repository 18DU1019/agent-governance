# -*- coding: utf-8 -*-
"""sync_check 回归自测（二十一用例，纯 stdlib，与校验器同目录自定位，无环境依赖）。

覆盖 v0.1.5 / v0.1.5.1 / v0.1.5.2 修复项与既有判定的回归防护：
  case1   链接双挂正例 PASS（Windows 用 junction，其余平台用 symlink）
  case2   实体副本遮蔽必 FAIL 并报"字节一致"判定
  case2b  tree_hash 不可读计数（monkeypatch 模拟权限故障，不碰真实 ACL）
  case2c  主流程 SUSPENDED 分支（不可读不冒充一致，退出码仍 FAIL）
  case3   长度前缀消歧（交换内容/跨边界构造均不得同哈希）
  case4   悬空链接必 FAIL（CI 负例语义的本地等效）
  case5   链接侧不可读必 SUSPENDED（V1 回归：SUSPENDED 不再只活在遮蔽分支）
  case6   正本项内嵌套链接必 FAIL（V2 回归：纪律1 递归承载）
  case7   同路径双端必退出码 2（V4 回归：参数前提校验）
  case8   挂载端=正本必退出码 2（V4 回归）
  case9   链接无可校验文件必 FAIL（V3 回归：空正本项不冒充一致）
  case10  同端重复挂载必 FAIL（多挂检出，分布报表不虚增）
  case11  链接指向正本树外（旁支同名目录）必 FAIL（负例清单补漏·realpath 父子判定）
  case12  链接指向的正本项已消失（指向 hub 内非顶层目录）必 FAIL（负例清单补漏·masters 集判定）
  case13  链接名与正本目录名不一致必 FAIL（负例清单补漏·名比对独立断言）
  case14  挂载端目录不存在必 FAIL（负例清单补漏·exists 判定）
  case15  挂载端孤立实体目录必 FAIL（N8-1 回归：退役残留形态，白名单原则）
  case15b _前缀辅助目录豁免不误报（孤立目录判定的逃生通道）
  case16  正本内文件级链接必 FAIL（N8-2 回归：纪律1"任何链接"含文件级）
  case17  空字符串路径参数必退出码 2（N8-3 回归：env 空串不静默变 cwd）
  case18  不可读子目录必 SUSPENDED（N9-1 回归：目录级权限故障不静默跳过冒充判定）

用法: python tools/sync_check_selftest.py   （退出码 0=二十一用例全过）
CI 已接线（.github/workflows/ci.yml）；本地随时可跑，只写系统临时目录。
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOL = Path(__file__).resolve().parent / "sync_check.py"
IS_WIN = os.name == "nt"


def load_sc():
    spec = importlib.util.spec_from_file_location("sc", str(TOOL))
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    return sc


def make_link(link: Path, target: Path):
    """跨平台建目录链接：Windows 走 mklink /J（无需管理员），其余走 symlink。"""
    if IS_WIN:
        subprocess.run(f'mklink /J "{link}" "{target}"', shell=True,
                       capture_output=True, check=True)
    else:
        link.symlink_to(target)


class Fixture:
    """每用例独立临时树：hub/skillA 正本 + ma/mb 两端挂载目录。"""

    def __enter__(self):
        self.root = Path(tempfile.mkdtemp(prefix="gov_selftest_"))
        (self.root / "hub" / "skillA").mkdir(parents=True)
        (self.root / "ma").mkdir()
        (self.root / "mb").mkdir()
        (self.root / "hub" / "skillA" / "SKILL.md").write_text("x\n", encoding="utf-8")
        return self

    def __exit__(self, *exc):
        # junction/symlink 先断再删，防 rmtree 穿透删正本（纪律 2 的自食其例）。
        # 平台分叉：Windows junction/目录 symlink 须 rmdir（unlink 报权限/目录错），
        # Unix symlink 指向目录时须 unlink（os.rmdir 对 symlink 抛 NotADirectoryError）。
        for base in (self.root / "ma", self.root / "mb"):
            for x in base.iterdir():
                if IS_WIN and (x.is_junction() or x.is_symlink()):
                    x.rmdir()
                elif x.is_symlink():
                    x.unlink()
        shutil.rmtree(self.root, ignore_errors=True)
        return False

    def run_check(self):
        return subprocess.run(
            [sys.executable, str(TOOL),
             "--source", str(self.root / "hub"),
             "--mount-a", str(self.root / "ma"),
             "--mount-b", str(self.root / "mb")],
            capture_output=True, text=True)


results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), str(detail)[:300]))


# case1 正例：两端链接均指向正本
with Fixture() as f:
    make_link(f.root / "ma" / "skillA", f.root / "hub" / "skillA")
    make_link(f.root / "mb" / "skillA", f.root / "hub" / "skillA")
    r = f.run_check()
    check("case1 链接双挂 PASS", r.returncode == 0 and r.stdout.startswith("PASS"), r.stdout)

# case2 遮蔽：实体副本与正本同名 -> FAIL，内容判定报"字节一致"
with Fixture() as f:
    shutil.copytree(f.root / "hub" / "skillA", f.root / "ma" / "skillA")
    r = f.run_check()
    check("case2 遮蔽字节一致仍 FAIL 报出",
          r.returncode == 1 and "字节一致" in r.stdout, r.stdout)

# case2b tree_hash 不可读计数 bad=1
with Fixture() as f:
    sc = load_sc()
    shutil.copytree(f.root / "hub" / "skillA", f.root / "ma" / "skillA")
    orig = Path.read_bytes

    def fake(self):
        if self.name == "SKILL.md":
            raise OSError("simulated deny")
        return orig(self)

    Path.read_bytes = fake
    try:
        _, _, n, bad = sc.tree_hash(f.root / "ma" / "skillA")
    finally:
        Path.read_bytes = orig
    check("case2b tree_hash 不可读计数 bad=1", bad == 1 and n == 1, (bad, n))

# case2c 主流程 SUSPENDED 分支（副本侧不可读；退出码仍 1）
with Fixture() as f:
    sc = load_sc()
    shutil.copytree(f.root / "hub" / "skillA", f.root / "ma" / "skillA")
    orig = Path.read_bytes
    deny_prefix = str(f.root / "ma" / "skillA")

    def fake(self):
        if str(self).startswith(deny_prefix) and self.name == "SKILL.md":
            raise OSError("deny")
        return orig(self)

    Path.read_bytes = fake
    try:
        import io
        buf = io.StringIO()
        real_out = sys.stdout
        sys.stdout = buf
        try:
            code = sc.main(["--source", str(f.root / "hub"),
                            "--mount-a", str(f.root / "ma"),
                            "--mount-b", str(f.root / "mb")])
        finally:
            sys.stdout = real_out
    finally:
        Path.read_bytes = orig
    check("case2c 主流程 SUSPENDED 分支（FAIL 退出码=1 且报 SUSPENDED）",
          code == 1 and "SUSPENDED" in buf.getvalue(), buf.getvalue())

# case3 长度前缀消歧：交换内容两树哈希必不同；跨界构造必不同
sc = load_sc()
t1 = Path(tempfile.mkdtemp(prefix="gov_c3a_"))
t2 = Path(tempfile.mkdtemp(prefix="gov_c3b_"))
t3 = Path(tempfile.mkdtemp(prefix="gov_c3c_"))
(t1 / "f1").write_bytes(b"AA")
(t1 / "f2").write_bytes(b"BB")
(t2 / "f1").write_bytes(b"BB")
(t2 / "f2").write_bytes(b"AA")
h1, h2 = sc.tree_hash(t1), sc.tree_hash(t2)
(t3 / "f1").write_bytes(b"A\x00B")
h3 = sc.tree_hash(t3)
check("case3 长度前缀消歧（交换/跨界均不同哈希）",
      h1[0] != h2[0] and h3[0] not in (h1[0], h2[0]),
      (h1[0][:8], h2[0][:8], h3[0][:8]))
for t in (t1, t2, t3):
    shutil.rmtree(t, ignore_errors=True)

# case4 悬空链接必 FAIL（一端合法链接 + 一端指向不存在目标）
with Fixture() as f:
    make_link(f.root / "ma" / "skillA", f.root / "hub" / "skillA")
    make_link(f.root / "mb" / "gone", f.root / "hub" / "gone")
    r = f.run_check()
    check("case4 悬空链接必 FAIL", r.returncode == 1 and "链接目标不可用" in r.stdout, r.stdout)

# case5 V1 回归：透过链接存在不可读文件 -> SUSPENDED（不冒充一致，退出码 1）。
# monkeypatch read_bytes 模拟权限故障，不碰真实 ACL。
with Fixture() as f:
    sc = load_sc()
    make_link(f.root / "ma" / "skillA", f.root / "hub" / "skillA")
    make_link(f.root / "mb" / "skillA", f.root / "hub" / "skillA")
    orig = Path.read_bytes

    def fake(self):
        if self.name == "SKILL.md":
            raise OSError("deny")
        return orig(self)

    Path.read_bytes = fake
    try:
        import io
        buf = io.StringIO()
        real_out = sys.stdout
        sys.stdout = buf
        try:
            code = sc.main(["--source", str(f.root / "hub"),
                            "--mount-a", str(f.root / "ma"),
                            "--mount-b", str(f.root / "mb")])
        finally:
            sys.stdout = real_out
    finally:
        Path.read_bytes = orig
    check("case5 链接侧不可读必 SUSPENDED（V1 回归）",
          code == 1 and "SUSPENDED" in buf.getvalue(), buf.getvalue())

# case6 V2 回归：正本项内部嵌套链接必 FAIL（纪律1"任何链接"递归承载）
with Fixture() as f:
    (f.root / "hub" / "inner_target").mkdir()
    make_link(f.root / "hub" / "skillA" / "nested_link", f.root / "hub" / "inner_target")
    r = f.run_check()
    check("case6 正本内嵌套链接必 FAIL（V2 回归）",
          r.returncode == 1 and "正本污染" in r.stdout and "nested_link" in r.stdout, r.stdout)

# case7 V4 回归：--mount-a 与 --mount-b 同路径 -> 退出码 2（参数前提不满足）
with Fixture() as f:
    r = subprocess.run(
        [sys.executable, str(TOOL),
         "--source", str(f.root / "hub"),
         "--mount-a", str(f.root / "ma"),
         "--mount-b", str(f.root / "ma")],
        capture_output=True, text=True)
    check("case7 同路径双端必退出 2（V4 回归）",
          r.returncode == 2 and "参数前提" in (r.stdout + r.stderr), r.stdout + r.stderr)

# case8 V4 回归：--mount-a 传正本自身 -> 退出码 2
with Fixture() as f:
    r = subprocess.run(
        [sys.executable, str(TOOL),
         "--source", str(f.root / "hub"),
         "--mount-a", str(f.root / "hub"),
         "--mount-b", str(f.root / "mb")],
        capture_output=True, text=True)
    check("case8 挂载端=正本必退出 2（V4 回归）",
          r.returncode == 2 and "参数前提" in (r.stdout + r.stderr), r.stdout + r.stderr)

# case9 V3 回归：透过链接无可校验文件（正本项为空）-> FAIL 不冒充一致
with Fixture() as f:
    (f.root / "hub" / "skillEmpty").mkdir()
    make_link(f.root / "ma" / "skillEmpty", f.root / "hub" / "skillEmpty")
    make_link(f.root / "mb" / "skillEmpty", f.root / "hub" / "skillEmpty")
    r = f.run_check()
    check("case9 链接无可校验文件必 FAIL（V3 回归）",
          r.returncode == 1 and "无可校验文件" in r.stdout, r.stdout)

# case10 同端重复挂载同一正本 -> FAIL（多挂检出）
with Fixture() as f:
    make_link(f.root / "ma" / "skillA", f.root / "hub" / "skillA")
    (f.root / "hub" / "skillA2").mkdir()
    make_link(f.root / "mb" / "skillA2", f.root / "hub" / "skillA2")
    # 同端 ma 再建一个链接指向 skillA（目录名不同但目标同名——按目标名 mname 归并）
    make_link(f.root / "ma" / "skillA_dup", f.root / "hub" / "skillA")
    r = f.run_check()
    check("case10 同端重复挂载必 FAIL（多挂检出）",
          r.returncode == 1 and "重复挂载" in r.stdout, r.stdout)

# case11 负例清单补漏：链接指向正本树外的同名旁支目录 -> FAIL（realpath 父子判定）
with Fixture() as f:
    side = f.root / "outside" / "skillA"
    side.mkdir(parents=True)
    (side / "SKILL.md").write_text("y\n", encoding="utf-8")
    make_link(f.root / "ma" / "skillA", side)
    make_link(f.root / "mb" / "skillA", f.root / "hub" / "skillA")
    r = f.run_check()
    check("case11 链接指向非正本（树外旁支）必 FAIL",
          r.returncode == 1 and "链接指向非正本" in r.stdout, r.stdout)

# case12 负例清单补漏：链接指向 hub 内非顶层目录（= 正本项集里没有它）-> FAIL
with Fixture() as f:
    sub = f.root / "hub" / "sub" / "skillC"
    sub.mkdir(parents=True)
    (sub / "SKILL.md").write_text("z\n", encoding="utf-8")
    make_link(f.root / "ma" / "skillC", sub)
    make_link(f.root / "mb" / "skillA", f.root / "hub" / "skillA")
    r = f.run_check()
    check("case12 指向的正本项不存在必 FAIL（含 hub 内非顶层目标）",
          r.returncode == 1 and "指向的正本项不存在" in r.stdout, r.stdout)

# case13 负例清单补漏：链接名与正本目录名不一致 -> FAIL（独立断言，不再靠 case10 顺带）
with Fixture() as f:
    make_link(f.root / "ma" / "skillB_link", f.root / "hub" / "skillA")
    make_link(f.root / "mb" / "skillA", f.root / "hub" / "skillA")
    r = f.run_check()
    check("case13 链接名与正本目录名不一致必 FAIL",
          r.returncode == 1 and "链接名与正本目录名不一致" in r.stdout, r.stdout)

# case14 负例清单补漏：挂载端目录不存在 -> FAIL（exists 判定，报"目录不存在"）
with Fixture() as f:
    r = subprocess.run(
        [sys.executable, str(TOOL),
         "--source", str(f.root / "hub"),
         "--mount-a", str(f.root / "ma"),
         "--mount-b", str(f.root / "mb" / "nope")],
        capture_output=True, text=True)
    check("case14 挂载端目录不存在必 FAIL",
          r.returncode == 1 and "目录不存在" in r.stdout, r.stdout)

# case15 第八轮 N8-1 回归：挂载端孤立实体目录（名不在正本）-> FAIL 报"孤立实体目录"
with Fixture() as f:
    (f.root / "ma" / "oldskill").mkdir()
    (f.root / "ma" / "oldskill" / "SKILL.md").write_text("ghost\n", encoding="utf-8")
    make_link(f.root / "ma" / "skillA", f.root / "hub" / "skillA")
    make_link(f.root / "mb" / "skillA", f.root / "hub" / "skillA")
    r = f.run_check()
    check("case15 挂载端孤立实体目录必 FAIL（N8-1 退役残留回归）",
          r.returncode == 1 and "孤立实体目录" in r.stdout, r.stdout)

# case15b 逃生通道：_ 前缀辅助目录豁免，不得误报
with Fixture() as f:
    (f.root / "ma" / "_archive").mkdir()
    (f.root / "ma" / "_archive" / "note.md").write_text("n\n", encoding="utf-8")
    make_link(f.root / "ma" / "skillA", f.root / "hub" / "skillA")
    make_link(f.root / "mb" / "skillA", f.root / "hub" / "skillA")
    r = f.run_check()
    check("case15b _前缀辅助目录豁免不误报（逃生通道）",
          r.returncode == 0 and "孤立实体目录" not in r.stdout, r.stdout)

# case16 第八轮 N8-2 回归：正本内文件级链接 -> FAIL（纪律1"任何链接"含文件级）。
# Windows 文件级 symlink 需权限：创建失败则跳过（junction 不支持文件级，用 symlink）。
with Fixture() as f:
    ext_file = f.root / "shared.md"
    ext_file.write_text("secret-external\n", encoding="utf-8")
    link_fp = f.root / "hub" / "skillA" / "ref.md"
    try:
        link_fp.symlink_to(ext_file)
        made = True
    except OSError:
        made = False
    if made:
        make_link(f.root / "ma" / "skillA", f.root / "hub" / "skillA")
        make_link(f.root / "mb" / "skillA", f.root / "hub" / "skillA")
        r = f.run_check()
        check("case16 正本内文件级链接必 FAIL（N8-2 纪律1文件级承载）",
              r.returncode == 1 and "文件级链接" in r.stdout, r.stdout)
    else:
        check("case16 SKIP（本机无文件级 symlink 权限，CI Linux 覆盖）", True, "skip")

# case17 第八轮 N8-3 回归：路径参数为空字符串 -> 退出码 2（不静默变 cwd 拿假绿）
with Fixture() as f:
    r = subprocess.run(
        [sys.executable, str(TOOL),
         "--source", str(f.root / "hub"),
         "--mount-a", "",
         "--mount-b", str(f.root / "mb")],
        capture_output=True, text=True)
    check("case17 空字符串路径必退出 2（N8-3 参数前提）",
          r.returncode == 2 and "空字符串" in (r.stdout + r.stderr), r.stdout + r.stderr)

# case18 第九轮 N9-1 回归：不可读**子目录**（目录级权限故障）不得静默跳过——
# 旧实现 rglob 对不可读目录零计数，判定基于残缺文件集冒充"字节一致/内容分叉"；
# os.walk onerror 把目录级不可读计入 bad，判定必须转 SUSPENDED。
with Fixture() as f:
    sc = load_sc()
    (f.root / "hub" / "skillA" / "secret").mkdir()
    (f.root / "hub" / "skillA" / "secret" / "a.txt").write_text("AAA\n", encoding="utf-8")
    shutil.copytree(f.root / "hub" / "skillA", f.root / "ma" / "skillA")
    (f.root / "ma" / "skillA" / "secret" / "a.txt").write_text("BBBB\n", encoding="utf-8")
    real_scandir = os.scandir

    def fake_scandir(path, *a, **k):
        if str(path).replace("\\", "/").endswith("/skillA/secret"):
            raise PermissionError("simulated deny")
        return real_scandir(path, *a, **k)

    os.scandir = fake_scandir
    try:
        import io
        buf = io.StringIO()
        real_out = sys.stdout
        sys.stdout = buf
        try:
            code = sc.main(["--source", str(f.root / "hub"),
                            "--mount-a", str(f.root / "ma"),
                            "--mount-b", str(f.root / "mb")])
        finally:
            sys.stdout = real_out
    finally:
        os.scandir = real_scandir
    check("case18 不可读子目录必 SUSPENDED 不冒充判定（N9-1 回归）",
          code == 1 and "SUSPENDED" in buf.getvalue() and "内容分叉" not in buf.getvalue(),
          buf.getvalue())

fails = 0
for name, ok, detail in results:
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        fails += 1
        print("   detail:", detail)
print(f"\nTOTAL={len(results)} FAILS={fails}")
sys.exit(1 if fails else 0)
