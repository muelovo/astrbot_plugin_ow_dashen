"""Shared font loading utilities for all render modules."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("astrbot")


def _find_res_dir() -> Path:
    """Locate the overstats/res directory regardless of deployment layout."""
    here = Path(__file__).resolve()
    candidates = (
        here.parents[2] / "res",                    # overstats/src/modules -> overstats/res
        here.parents[3] / "overstats" / "res",      # plugin_root/overstats/res
        here.parents[2] / "overstats" / "res",
        here.parents[1] / "res",
        here.parents[4] / "overstats" / "res",
    )
    for candidate in candidates:
        if (candidate / "simhei.ttf").exists():
            return candidate
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    logger.warning(
        f"[font_utils] Could not locate res/simhei.ttf. "
        f"Tried: {[str(c) for c in candidates]}. "
        f"__file__={here}"
    )
    return candidates[0]


RES_DIR: Path = _find_res_dir()
RESOURCE_DIR: Path = RES_DIR
_SIMHEI_PATH: Path = RES_DIR / "simhei.ttf"
# Bump when font loading changes so render caches can be invalidated.
RENDER_FONT_CACHE_VERSION = 2


def contains_cjk(text: Any) -> bool:
    for char in str(text or ""):
        if (
            "\u3400" <= char <= "\u4dbf"
            or "\u4e00" <= char <= "\u9fff"
            or "\uf900" <= char <= "\ufaff"
        ):
            return True
    return False


def adjust_chinese_font_size(size: int) -> int:
    """Bump very small sizes so CJK glyphs remain legible in Pillow."""
    adjusted = int(size)
    if adjusted <= 11:
        adjusted += 1
    elif adjusted <= 14:
        adjusted += 2
    elif adjusted <= 18:
        adjusted += 1
    return adjusted


def load_chinese_font(size: int, *, bold: bool = False) -> Any:
    """Load a font that supports Chinese characters.

    Priority:
    1. Bundled simhei.ttf in res/  (works on any OS)
    2. Windows system fonts
    3. Pillow default (last resort, no Chinese support)
    """
    from PIL import ImageFont

    size = adjust_chinese_font_size(size)
    candidates = [
        _SIMHEI_PATH,
        Path("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            continue
    logger.warning(
        f"[font_utils] load_chinese_font({size}) failed all candidates: "
        f"{[str(p) for p in candidates]}. simhei exists={_SIMHEI_PATH.exists()}"
    )
    return ImageFont.load_default()


def load_font(name: str, size: int, *, fallback: Optional[str] = None) -> Any:
    """Load a bundled font by filename with optional fallback."""
    from PIL import ImageFont

    candidates: list[Path | str] = [RES_DIR / name]
    if fallback:
        candidates.append(RES_DIR / fallback)
    candidates.extend([
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ])
    for path in candidates:
        path_obj = Path(path)
        if path_obj.suffix and not path_obj.exists():
            continue
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            continue
    return ImageFont.load_default()


def load_resource_font(name: str, size: int, *, fallback: Optional[str] = None) -> Any:
    """Alias used by render modules for bundled decorative/Latin fonts."""
    return load_font(name, size, fallback=fallback)


def load_font_for_text(
    text: Any,
    size: int,
    *,
    bold: bool = False,
    latin_name: str = "bignoodletoooblique.ttf",
    latin_fallback: Optional[str] = "BigNoodleToo.ttf",
) -> Any:
    """Pick Chinese or Latin bundled font based on text content."""
    if contains_cjk(text):
        return load_chinese_font(size, bold=bold)
    return load_font(latin_name, size, fallback=latin_fallback)


def load_summary_style_fonts(scale: float = 1.0) -> dict[str, Any]:
    """Font set aligned with dashen_summary / dashen_profile Chinese rendering.

    All user-facing labels use Chinese-capable fonts (simhei / system fallback),
    matching the working summary and profile image commands.
    """
    factor = float(scale)

    def cn(size: int, *, bold: bool = False) -> Any:
        return load_chinese_font(max(1, int(round(size * factor))), bold=bold)

    return {
        "name": cn(44, bold=True),
        "title": cn(28, bold=True),
        "title_md": cn(22, bold=True),
        "section": cn(26, bold=True),
        "panel": cn(18, bold=True),
        "body": cn(18),
        "body_sm": cn(16),
        "body_md": cn(20, bold=True),
        "label": cn(15),
        "label_sm": cn(13, bold=True),
        "caption": cn(14),
        "caption_sm": cn(12),
        "caption_xs": cn(11),
        "axis": cn(12, bold=True),
        "micro": cn(10),
        "num": load_font("num.ttf", max(1, int(round(24 * factor))), fallback="GrotaRoundedExtraBold.otf"),
        "num_sm": load_font("num.ttf", max(1, int(round(18 * factor))), fallback="GrotaRoundedExtraBold.otf"),
    }
