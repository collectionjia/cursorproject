#!/usr/bin/env python3
"""Patch AIAssistant-360 to hide renew/recharge and tutorial sidebar menus."""
from __future__ import annotations

import marshal
import shutil
import struct
import types
import zlib
from pathlib import Path

from PyInstaller.archive.readers import CArchiveReader
from PyInstaller.archive.writers import CArchiveWriter, ZlibArchiveWriter
from PyInstaller.loader.pyimod01_archive import PYZ_ITEM_NSPKG, PYZ_ITEM_PKG, ZlibArchiveReader

ROOT = Path(__file__).resolve().parent
EXE = ROOT / "AIAssistant-360.exe"
OUT_EXE = ROOT / "AIAssistant-360-no-renew.exe"
EXTRACTED = ROOT / "AIAssistant-360.exe_extracted"
PYZ_PYC = EXTRACTED / "PYZ.pyz_extracted"
MAIN_WINDOW = PYZ_PYC / "ui" / "main_window.pyc"
CURSOR_PAGE = PYZ_PYC / "ui" / "pages" / "cursor_page.pyc"
KIRO_PAGE = PYZ_PYC / "ui" / "pages" / "kiro_page.pyc"
WINDSURF_PAGE = PYZ_PYC / "ui" / "pages" / "windsurf_page.pyc"
SUB2API_PAGE = PYZ_PYC / "ui" / "pages" / "sub2api_platform_page.pyc"
PYC_HEADER = b"\xa7\r\r\n" + b"\0" * 12

PATCHED_PAGE_MODULES: dict[str, Path] = {}


def configure_bundle(exe: Path, out: Path, extracted: Path) -> None:
    """Point patch/repack helpers at a specific PyInstaller bundle."""
    global EXE, OUT_EXE, EXTRACTED, PYZ_PYC, MAIN_WINDOW, CURSOR_PAGE, KIRO_PAGE
    global WINDSURF_PAGE, SUB2API_PAGE, PATCHED_PAGE_MODULES

    EXE = exe
    OUT_EXE = out
    EXTRACTED = extracted
    PYZ_PYC = EXTRACTED / "PYZ.pyz_extracted"
    MAIN_WINDOW = PYZ_PYC / "ui" / "main_window.pyc"
    CURSOR_PAGE = PYZ_PYC / "ui" / "pages" / "cursor_page.pyc"
    KIRO_PAGE = PYZ_PYC / "ui" / "pages" / "kiro_page.pyc"
    WINDSURF_PAGE = PYZ_PYC / "ui" / "pages" / "windsurf_page.pyc"
    SUB2API_PAGE = PYZ_PYC / "ui" / "pages" / "sub2api_platform_page.pyc"
    PATCHED_PAGE_MODULES = {
        "ui.pages.cursor_page": CURSOR_PAGE,
        "ui.pages.kiro_page": KIRO_PAGE,
        "ui.pages.windsurf_page": WINDSURF_PAGE,
        "ui.pages.sub2api_platform_page": SUB2API_PAGE,
    }


configure_bundle(EXE, OUT_EXE, EXTRACTED)

EMPTY_STATE_SRC = '''
def _build_empty_state(self):
    empty = QWidget()
    empty.setStyleSheet("background: #f4f6f9;")
    vbox = QVBoxLayout(empty)
    vbox.setContentsMargins(0, 0, 0, 0)
    vbox.setSpacing(0)
    vbox.addStretch(2)

    center = QVBoxLayout()
    center.setAlignment(Qt.AlignmentFlag.AlignCenter)
    center.setSpacing(0)

    icon_bg = QFrame()
    icon_bg.setFixedSize(80, 80)
    icon_bg.setStyleSheet("{icon_bg_style}")
    icon_inner = QVBoxLayout(icon_bg)
    icon_inner.setContentsMargins(0, 0, 0, 0)
    icon_lbl = platform_icon_label("{platform}", 42)
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_inner.addWidget(icon_lbl)
    icon_wrap = QHBoxLayout()
    icon_wrap.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_wrap.addWidget(icon_bg)
    center.addLayout(icon_wrap)
    center.addSpacing(20)

    title_lbl = QLabel("{title}")
    title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_lbl.setStyleSheet("font-size: 20px; font-weight: 800; color: #1e293b;background: transparent; border: none;")
    center.addWidget(title_lbl)
    center.addSpacing(8)

    desc_lbl = QLabel("{desc}")
    desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc_lbl.setWordWrap(True)
    desc_lbl.setStyleSheet("font-size: 13px; color: #94a3b8; background: transparent;border: none; padding: 0 60px;")
    center.addWidget(desc_lbl)
    center.addSpacing(24)

    btn_row = QHBoxLayout()
    btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
    btn_row.setSpacing(14)

    activate_btn = QPushButton("前往首页激活")
    activate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    activate_btn.setFixedHeight(44)
    activate_btn.setStyleSheet("{activate_style}")
    activate_btn.clicked.connect(lambda _=None: self.navigate_to.emit("首页"))
    btn_row.addWidget(activate_btn)

    center.addLayout(btn_row)
    vbox.addLayout(center)
    vbox.addStretch(3)
    self._page_stack.addWidget(empty)
'''

SUB2API_EMPTY_STATE_SRC = '''
def _build_empty_state(self):
    empty = QWidget()
    empty.setStyleSheet("background: #f4f6f9;")
    vbox = QVBoxLayout(empty)
    vbox.setContentsMargins(0, 0, 0, 0)
    vbox.setSpacing(0)
    vbox.addStretch(2)

    center = QVBoxLayout()
    center.setAlignment(Qt.AlignmentFlag.AlignCenter)
    center.setSpacing(0)

    cfg = self._cfg
    icon_bg = QFrame()
    icon_bg.setFixedSize(80, 80)
    icon_bg.setStyleSheet(
        "background: " + cfg["bg"] + "; border: 2px solid " + cfg["accent"] + "20; border-radius: 40px;"
    )
    icon_inner = QVBoxLayout(icon_bg)
    icon_inner.setContentsMargins(0, 0, 0, 0)
    icon_lbl = platform_icon_label(self.tool_name, 42)
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_inner.addWidget(icon_lbl)
    icon_wrap = QHBoxLayout()
    icon_wrap.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_wrap.addWidget(icon_bg)
    center.addLayout(icon_wrap)
    center.addSpacing(20)

    title_lbl = QLabel("暂未开通 " + self.tool_name)
    title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_lbl.setStyleSheet("font-size: 20px; font-weight: 800; color: #1e293b;background: transparent; border: none;")
    center.addWidget(title_lbl)
    center.addSpacing(8)

    desc_lbl = QLabel("激活包含 " + self.tool_name + " 权限的激活码后，即可使用密钥管理和配置功能")
    desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    desc_lbl.setWordWrap(True)
    desc_lbl.setStyleSheet("font-size: 13px; color: #94a3b8; background: transparent;border: none; padding: 0 60px;")
    center.addWidget(desc_lbl)
    center.addSpacing(24)

    btn_row = QHBoxLayout()
    btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
    btn_row.setSpacing(14)

    activate_btn = QPushButton("前往首页激活")
    activate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    activate_btn.setFixedHeight(44)
    activate_btn.setStyleSheet(
        "QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,  stop:0 #4f46e5, stop:1 #6366f1);"
        "  color: white; border: none; border-radius: 14px;  padding: 0 32px; font-size: 14px; font-weight: 700; }"
        "QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,  stop:0 #4338ca, stop:1 #4f46e5); }"
    )
    activate_btn.clicked.connect(lambda _=None: self.navigate_to.emit("首页"))
    btn_row.addWidget(activate_btn)

    center.addLayout(btn_row)
    vbox.addLayout(center)
    vbox.addStretch(3)
    self._stack.addWidget(empty)
'''

SET_GUIDE_SRC = '''
def set_guide(self, text):
    """Show or hide the usage guide section."""
    if text:
        text = "\\n".join(ln for ln in text.splitlines() if "vaultbyte.top" not in ln)
        if text.strip():
            self._guide_label.setText(text)
            self._guide_panel.setVisible(True)
            return
    self._guide_panel.setVisible(False)
'''

BG_LOAD_ERROR_FAQ_SRC = '''
def _bg_load_error_faq(self):
    def _clean(text):
        if not isinstance(text, str):
            return text
        return "\\n".join(ln for ln in text.splitlines() if "vaultbyte.top" not in ln)

    try:
        raw = self.api.get_error_faq(8)
        cleaned = []
        for it in raw or []:
            if not isinstance(it, dict):
                cleaned.append(it)
                continue
            d = dict(it)
            for key in ("q", "question", "a", "answer"):
                if key in d:
                    d[key] = _clean(d[key])
            cleaned.append(d)
        self._faq_items = cleaned
    except Exception:
        self._faq_items = []
    QMetaObject.invokeMethod(
        self,
        "_show_error_faq_dialog",
        Qt.ConnectionType.QueuedConnection,
    )
'''


def load_code(path: Path) -> types.CodeType:
    data = path.read_bytes()
    if len(data) <= 16:
        raise EOFError(f"empty pyc: {path}")
    return marshal.loads(data[16:])


def save_code(path: Path, code: types.CodeType) -> None:
    path.write_bytes(PYC_HEADER + marshal.dumps(code))


def replace_nested_code(root: types.CodeType, name: str, replacer) -> types.CodeType:
    changed = False
    new_consts = []
    for const in root.co_consts:
        if isinstance(const, types.CodeType):
            if const.co_name == name:
                new_consts.append(replacer(const))
                changed = True
            else:
                patched = replace_nested_code(const, name, replacer)
                new_consts.append(patched)
                changed = changed or patched is not const
        else:
            new_consts.append(const)
    return root.replace(co_consts=tuple(new_consts)) if changed else root


def patch_is_menu_enabled(fn: types.CodeType) -> types.CodeType:
    code = bytearray(fn.co_code)
    renew_needle = bytes(
        [0x7C, 0x00, 0x6A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x53, 0x00]
    )
    tutorial_needle = bytes(
        [0x7C, 0x00, 0x6A, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x53, 0x00]
    )
    false_return = bytes([0x64, 0x04, 0x09, 0x00, 0x09, 0x00, 0x09, 0x00, 0x09, 0x00, 0x09, 0x00, 0x53, 0x00])

    if renew_needle in code:
        idx = code.find(renew_needle)
        code[idx : idx + len(renew_needle)] = false_return
    elif false_return not in code:
        raise RuntimeError("renew menu patch pattern not found")

    if tutorial_needle in code:
        idx = code.find(tutorial_needle)
        code[idx : idx + len(tutorial_needle)] = false_return
    elif code.count(false_return) < 2:
        raise RuntimeError("tutorial menu patch pattern not found")

    return fn.replace(co_code=bytes(code))


def pad_load_const(const_index: int, size: int) -> bytes:
    if size < 2 or (size - 2) % 2 != 0:
        raise ValueError(f"invalid padded LOAD_CONST size: {size}")
    return bytes([0x64, const_index]) + bytes([0x09, 0x00]) * ((size - 2) // 2)


def patch_copyable_notice_label_init(fn: types.CodeType) -> types.CodeType:
    consts = list(fn.co_consts)
    if "" not in consts:
        empty_idx = len(consts)
        consts.append("")
    else:
        empty_idx = consts.index("")

    code = bytearray(fn.co_code)
    needle = bytes([0x7C, 0x01, 0x7C, 0x02, 0xA6, 0x02])
    repl = bytes([0x64, empty_idx, 0x7C, 0x02, 0xA6, 0x02])
    idx = code.find(needle)
    if idx < 0:
        if repl in code:
            return fn
        raise RuntimeError("_CopyableNoticeLabel.__init__ patch pattern not found")
    code[idx : idx + len(needle)] = repl
    return fn.replace(co_consts=tuple(consts), co_code=bytes(code))


def patch_copyable_notice_label(cls: types.CodeType) -> types.CodeType:
    return replace_nested_code(cls, "__init__", patch_copyable_notice_label_init)


def patch_build_main_app(fn: types.CodeType) -> types.CodeType:
    code = bytearray(fn.co_code)

    cache_needle = bytes(
        [
            0x7C,
            0x01,
            0xA0,
            0x02,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x64,
            0x08,
            0x64,
            0x09,
            0xA6,
            0x02,
            0x00,
            0x00,
            0xAB,
            0x02,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x89,
            0x00,
        ]
    )
    cache_repl = pad_load_const(9, 42) + bytes([0x89, 0x00])
    if cache_needle in code:
        idx = code.find(cache_needle)
        code[idx : idx + len(cache_needle)] = cache_repl
    elif pad_load_const(9, 42) not in code:
        raise RuntimeError("_build_main_app bottom_notice cache patch not found")

    label_needle = bytes([0x89, 0x00, 0x6A, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    label_repl = pad_load_const(9, 12)
    if label_needle in code:
        idx = code.find(label_needle)
        code[idx : idx + len(label_needle)] = label_repl

    visible_needle = bytes(
        [
            0x74,
            0xD5,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x89,
            0x00,
            0x6A,
            0x09,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0xA6,
            0x01,
            0x00,
            0x00,
            0xAB,
            0x01,
            0x00,
            0x00,
        ]
    )
    visible_repl = pad_load_const(21, 30)
    if visible_needle in code:
        idx = code.find(visible_needle)
        code[idx : idx + len(visible_needle)] = visible_repl

    return fn.replace(co_code=bytes(code))


def patch_apply_menu_refresh(fn: types.CodeType) -> types.CodeType:
    code = bytearray(fn.co_code)
    pending_store = bytes([0x7C, 0x0D, 0x7C, 0x00, 0x5F, 0x18])
    pending_store_patched = bytes([0x64, 0x11, 0x7C, 0x00, 0x5F, 0x18])
    if pending_store in code:
        idx = code.find(pending_store)
        code[idx : idx + len(pending_store)] = pending_store_patched
    elif pending_store_patched not in code:
        raise RuntimeError("_apply_menu_refresh bottom_notice store patch not found")

    visible_needle = bytes(
        [
            0x74,
            0x2F,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x7C,
            0x00,
            0x6A,
            0x18,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0x00,
            0xA6,
            0x01,
            0x00,
            0x00,
            0xAB,
            0x01,
            0x00,
            0x00,
        ]
    )
    visible_repl = pad_load_const(17, 30)
    if visible_needle in code:
        idx = code.find(visible_needle)
        code[idx : idx + len(visible_needle)] = visible_repl

    return fn.replace(co_code=bytes(code))


def patch_set_guide(code: types.CodeType) -> types.CodeType:
    for const in code.co_consts:
        if isinstance(const, types.CodeType) and const.co_name == "set_guide":
            if "vaultbyte.top" in const.co_consts:
                return code
    new_fn = compile(SET_GUIDE_SRC, "<patch>", "exec").co_consts[0]
    return replace_nested_code(code, "set_guide", lambda _: new_fn)


def extract_empty_state_config(fn: types.CodeType) -> dict[str, str]:
    strings = [c for c in fn.co_consts if isinstance(c, str)]
    platform = next(c for c in strings if c in ("Cursor", "Kiro", "Windsurf"))
    title = next(c for c in strings if c.startswith("暂未开通"))
    desc = next(c for c in strings if "激活" in c and "权限" in c and len(c) > 20)
    icon_bg_style = next(c for c in strings if "border-radius: 40px" in c)
    activate_style = next(
        c
        for c in strings
        if "qlineargradient" in c
        and ("4f46e5" in c or ("0891b2" in c and "stop:0" in c))
    )
    return {
        "platform": platform,
        "title": title,
        "desc": desc,
        "icon_bg_style": icon_bg_style,
        "activate_style": activate_style,
    }


def compile_empty_state_no_buy(fn: types.CodeType, *, sub2api: bool = False) -> types.CodeType:
    if sub2api:
        return compile(SUB2API_EMPTY_STATE_SRC, "<patch>", "exec").co_consts[0]
    cfg = extract_empty_state_config(fn)
    src = EMPTY_STATE_SRC.format(**cfg)
    return compile(src, "<patch>", "exec").co_consts[0]


def find_nested_func(root: types.CodeType, name: str) -> types.CodeType | None:
    for const in root.co_consts:
        if isinstance(const, types.CodeType):
            if const.co_name == name:
                return const
            found = find_nested_func(const, name)
            if found:
                return found
    return None


def patch_build_empty_state_no_buy(code: types.CodeType, *, sub2api: bool = False) -> types.CodeType:
    old_fn = find_nested_func(code, "_build_empty_state")
    if old_fn is None:
        return code
    if "前往购买" not in old_fn.co_consts:
        return code
    new_fn = compile_empty_state_no_buy(old_fn, sub2api=sub2api)
    return replace_nested_code(code, "_build_empty_state", lambda _: new_fn)


def patch_bg_load_error_faq(code: types.CodeType) -> types.CodeType:
    for const in code.co_consts:
        if isinstance(const, types.CodeType) and const.co_name == "_bg_load_error_faq":
            for nested in const.co_consts:
                if isinstance(nested, types.CodeType) and nested.co_name == "_clean":
                    return code
    new_fn = compile(BG_LOAD_ERROR_FAQ_SRC, "<patch>", "exec").co_consts[0]
    return replace_nested_code(code, "_bg_load_error_faq", lambda _: new_fn)


def patch_cursor_page_module(code: types.CodeType) -> types.CodeType:
    code = patch_set_guide(code)
    code = patch_bg_load_error_faq(code)
    return patch_build_empty_state_no_buy(code)


def patch_platform_page_module(code: types.CodeType, *, sub2api: bool = False) -> types.CodeType:
    return patch_build_empty_state_no_buy(code, sub2api=sub2api)


def patch_main_window_module(code: types.CodeType) -> types.CodeType:
    changed = False
    new_consts = []
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            if const.co_name == "_CopyableNoticeLabel":
                patched = patch_copyable_notice_label(const)
            elif const.co_name == "MainWindow":
                patched = replace_nested_code(
                    replace_nested_code(
                        replace_nested_code(const, "_is_menu_enabled", patch_is_menu_enabled),
                        "_build_main_app",
                        patch_build_main_app,
                    ),
                    "_apply_menu_refresh",
                    patch_apply_menu_refresh,
                )
            else:
                patched = const
            new_consts.append(patched)
            changed = changed or patched is not const
        else:
            new_consts.append(const)
    return code.replace(co_consts=tuple(new_consts)) if changed else code


def patch_pyc_files() -> None:
    mw = patch_main_window_module(load_code(MAIN_WINDOW))
    save_code(MAIN_WINDOW, mw)
    print(f"Patched {MAIN_WINDOW}")

    cp = patch_cursor_page_module(load_code(CURSOR_PAGE))
    save_code(CURSOR_PAGE, cp)
    print(f"Patched {CURSOR_PAGE}")

    kp = patch_platform_page_module(load_code(KIRO_PAGE))
    save_code(KIRO_PAGE, kp)
    print(f"Patched {KIRO_PAGE}")

    wp = patch_platform_page_module(load_code(WINDSURF_PAGE))
    save_code(WINDSURF_PAGE, wp)
    print(f"Patched {WINDSURF_PAGE}")

    sp = patch_platform_page_module(load_code(SUB2API_PAGE), sub2api=True)
    save_code(SUB2API_PAGE, sp)
    print(f"Patched {SUB2API_PAGE}")


def pyc_name_to_path(name: str, is_pkg: bool) -> Path:
    parts = name.split(".")
    if is_pkg:
        return PYZ_PYC.joinpath(*parts, "__init__.pyc")
    return PYZ_PYC.joinpath(*parts[:-1], f"{parts[-1]}.pyc")


def rebuild_pyz(pyz_path: Path) -> None:
    arch = ZlibArchiveReader(str(pyz_path))
    code_dict = {}
    logic_toc = []
    for name, entry in arch.toc.items():
        typecode = entry[0]
        if typecode == PYZ_ITEM_NSPKG:
            logic_toc.append((name, "-", "PYMODULE"))
            continue
        if name == "ui.main_window":
            code_dict[name] = load_code(MAIN_WINDOW)
        elif name in PATCHED_PAGE_MODULES:
            code_dict[name] = load_code(PATCHED_PAGE_MODULES[name])
        else:
            code_dict[name] = arch.extract(name)
        pathname = "__init__.py" if typecode == PYZ_ITEM_PKG else f"{name.rsplit('.', 1)[-1]}.py"
        logic_toc.append((name, pathname, "PYMODULE"))
    ZlibArchiveWriter(str(pyz_path), logic_toc, code_dict=code_dict)


class RawCArchiveWriter(CArchiveWriter):
    """Write archive entries as raw bytes without re-processing scripts/modules."""

    def _write_entry(self, fp, entry):
        dest_name, src_name, compress, typecode = entry
        return self._write_file(fp, src_name, dest_name, typecode, compress=compress)


def get_carchive_info(filepath: Path) -> tuple[int, str]:
    cookie_size = 24 + 64
    size = filepath.stat().st_size
    with filepath.open("rb") as fp:
        fp.seek(size - cookie_size)
        _, lengthofpackage, _, _, _, pylibname = struct.unpack("!8siiii64s", fp.read(cookie_size))
    return size - lengthofpackage, pylibname.rstrip(b"\x00").decode("ascii")


def repack_exe() -> None:
    if OUT_EXE.exists():
        OUT_EXE.unlink()
    shutil.copy2(EXE, OUT_EXE)

    arch = CArchiveReader(str(EXE))
    work = EXTRACTED / "_repack_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    entries = []
    for name, (_, data_length, uncompressed_length, compression_flag, typecode) in arch.toc.items():
        out = work / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(arch.extract(name))
        if name.endswith(".pyz") and typecode in ("z", "Z"):
            rebuild_pyz(out)
        entries.append((name, str(out), bool(compression_flag), typecode))

    offset, pylib_name = get_carchive_info(OUT_EXE)
    pkg = work / "PKG-patched"
    RawCArchiveWriter(str(pkg), entries, pylib_name=pylib_name)
    with OUT_EXE.open("r+b") as outf:
        outf.seek(offset)
        outf.write(pkg.read_bytes())
        outf.truncate()
    print(f"Wrote {OUT_EXE}")


def build_patched_bundle(exe: Path, out: Path, extracted: Path) -> None:
    configure_bundle(exe, out, extracted)
    patch_pyc_files()
    repack_exe()


def main() -> int:
    if not EXE.exists():
        print(f"Missing {EXE}")
        return 1
    if not MAIN_WINDOW.exists():
        print(f"Missing {MAIN_WINDOW}")
        return 1
    for path in (CURSOR_PAGE, KIRO_PAGE, WINDSURF_PAGE, SUB2API_PAGE):
        if not path.exists():
            print(f"Missing {path}")
            return 1
    build_patched_bundle(EXE, OUT_EXE, EXTRACTED)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
