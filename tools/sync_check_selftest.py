# -*- coding: utf-8 -*-
"""sync_check 回归自测（六用例，纯 stdlib，与校验器同目录自定位，无环境依赖）。

覆盖 v0.1.5 修复项与既有判定的回归防护：
  case1  链接双挂正例 PASS（Windows 用 junction，其余平台用 symlink）
  case2  实体副本遮蔽必 FAIL 并报"字节一致"判定
  case2b tree_hash 不可读计数（monkeypatch 模拟权限故障，不碰真实 ACL）
  case2c 主流程 SUSPENDED 分支（不可读不冒充一致，退出码仍 FAIL）
  case3  长度前缀消歧（交换内容/跨边界构造均不得同哈希）
  case4  悬空链接必 FAIL（CI 负例语义的本地等效）

用法: python tools/sync_check_selftest.py   （退出码 0=六用例全过）
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
        # junction/symlink 先断再删，防 rmtree 穿透删正本（纪律 2 的自食其例）
        for base in (self.root / "ma", self.root / "mb"):
            for x in base.iterdir():
                if x.is_symlink() or (IS_WIN and x.is_junction()):
                    x.rmdir()
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
    check("case4 悬空链接必 FAIL", r.returncode == 1 and "悬空链接" in r.stdout, r.stdout)

fails = 0
for name, ok, detail in results:
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        fails += 1
        print("   detail:", detail)
print(f"\nTOTAL={len(results)} FAILS={fails}")
sys.exit(1 if fails else 0)
