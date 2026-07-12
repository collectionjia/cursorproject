#!/usr/bin/env python3
"""Export a macOS build kit (patched pyc + scripts) for transfer to a Mac."""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KIT = ROOT / "macos_build_kit"
PYZ = ROOT / "AIAssistant-360.exe_extracted" / "PYZ.pyz_extracted"

PATCHED_FILES = [
    PYZ / "ui" / "main_window.pyc",
    PYZ / "ui" / "pages" / "cursor_page.pyc",
    PYZ / "ui" / "pages" / "kiro_page.pyc",
    PYZ / "ui" / "pages" / "windsurf_page.pyc",
    PYZ / "ui" / "pages" / "sub2api_platform_page.pyc",
]

SCRIPT_FILES = [
    ROOT / "build_macos.py",
    ROOT / "patch_no_renew_menu.py",
    ROOT / "pyinstxtractor.py",
    ROOT / ".github" / "workflows" / "build-macos.yml",
]

README = """AIAssistant-360 macOS 打包说明
================================

重要：macOS 版必须在 Mac 电脑上打包，Windows 无法直接生成可运行的 .app。

准备材料
--------
1. 一台 Mac（Apple 芯片或 Intel 均可）
2. Python 3.11：brew install python@3.11 或 pyenv
3. PyInstaller：python3.11 -m pip install pyinstaller
4. 官方原版 macOS 安装包（各架构一份）：
   - Apple 芯片 (arm64)：AIAssistant-360-arm64.app
   - Intel (x86_64)：AIAssistant-360-x86_64.app
   请从软件官网/后台下载对应版本。

打包步骤
--------
1. 把整个 macos_build_kit 文件夹拷到 Mac
2. 打开终端，进入该目录
3. 安装依赖：
   python3.11 -m pip install pyinstaller

4. Apple 芯片版：
   python3.11 build_macos.py --arch arm64 \\
       --input /path/to/AIAssistant-360-arm64.app \\
       --output AIAssistant-360-no-renew-arm64.app

5. Intel 版：
   python3.11 build_macos.py --arch x86_64 \\
       --input /path/to/AIAssistant-360-x86_64.app \\
       --output AIAssistant-360-no-renew-x86_64.app

输出
----
- AIAssistant-360-no-renew-arm64.app   （Apple M 系列）
- AIAssistant-360-no-renew-x86_64.app  （Intel Mac）

已包含的补丁（与 Windows 版一致）
--------------------------------
- 隐藏「充值续费」「使用教程」菜单
- 隐藏首页底部联系方式/网址
- 过滤 vaultbyte.top 相关文字
- 隐藏「前往购买」按钮
- 常见错误对照弹窗去除 vaultbyte 链接

若 Mac 提示“无法打开/已损坏”
---------------------------
xattr -dr com.apple.quarantine AIAssistant-360-no-renew-arm64.app

没有 Mac 电脑怎么办？
--------------------
无法在 Windows 上直接生成 macOS .app，必须使用“远程 Mac 环境”。
推荐方案（免费）：GitHub Actions 云端 Mac 打包

1. 把本项目推到 GitHub 私有/公开仓库
2. 准备两个原版 macOS 安装包的 zip 下载直链：
   - Apple 芯片版 (arm64)
   - Intel 版 (x86_64)，可选
3. 打开 GitHub → Actions → “Build macOS Patched App” → Run workflow
4. 填入 zip 下载地址，运行完成后在 Artifacts 下载打包结果

其他方案：
- 云 Mac 租用：MacinCloud、AWS EC2 Mac（按小时计费）
- 请有 Mac 的朋友帮忙，把 macos_build_kit.zip 拷过去运行 build_macos.py
"""


def main() -> int:
    if KIT.exists():
        shutil.rmtree(KIT)
    pyc_dir = KIT / "patched_pyc" / "ui" / "pages"
    pyc_dir.mkdir(parents=True, exist_ok=True)
    (KIT / "patched_pyc" / "ui").mkdir(parents=True, exist_ok=True)

    for src in PATCHED_FILES:
        if not src.exists():
            raise SystemExit(f"Missing patched file: {src}")
        if src.name == "main_window.pyc":
            dst = KIT / "patched_pyc" / "ui" / src.name
        else:
            dst = pyc_dir / src.name
        shutil.copy2(src, dst)

    for src in SCRIPT_FILES:
        shutil.copy2(src, KIT / src.name)

    (KIT / "README_MACOS.txt").write_text(README, encoding="utf-8")

    zip_path = ROOT / "AIAssistant-360-macos-build-kit.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in KIT.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(KIT.parent))

    print(f"Wrote {KIT}")
    print(f"Wrote {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
