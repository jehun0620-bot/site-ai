# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28-S1-12
Development Density Management Area
Municipal Gazette HWP3 Bounded Paragraph Text Extraction

Offline-only text extraction from the single persisted EARLIEST (2003) HWP 3.0 sample.

Pipeline
--------
- reuse the validated HWP3 raw-DEFLATE boundary from T-28-S1-11
- skip 7 language font-face tables and style records
- parse HWP3 paragraph-list structures with bounded recursive handling of nested
  table/picture/header/footer/footnote paragraph lists
- decode ordinary HWP3 hchar values (ASCII + commercial Johab Hangul; Python's
  built-in johab codec is used as a fallback for standard symbols/Hanja)
- search the recovered text for UQQ700 direct/related terms

No network, OCR, external converter, archive traversal, or legal/SITE promotion.
A no-match on this one 2003 issue remains UNKNOWN and is never UQQ700 FALSE.
"""
from __future__ import annotations

import json
import re
import struct
import zlib
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
T28S111 = OUT_DIR / "development_density_management_area_municipal_gazette_hwp3_compressed_stream_boundary_probe.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwp3_bounded_paragraph_text_extraction.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
DIRECT = ["개발밀도관리구역", "개발밀도 관리구역"]
RELATED = ["개발밀도", "밀도관리", "관리구역"]

PARA_SHAPE_SIZE = 187
LINE_INFO_SIZE = 14
INLINE_CHAR_SHAPE_SIZE = 31
STYLE_RECORD_SIZE = 20 + 31 + 187
MAX_RECURSION = 32
MAX_PARAGRAPHS = 200_000
MAX_CELL_COUNT = 20_000

CHO_MAP = [-1, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18] + [-1] * 11
JUNG_MAP = [-1, -1, -1, 0, 1, 2, 3, 4, -1, -1, 5, 6, 7, 8, 9, 10, -1, -1, 11, 12, 13, 14, 15, 16, -1, -1, 17, 18, 19, 20, -1, -1]
JONG_MAP = [-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, -1, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, -1, -1]

EXTRA_MAP = {
    0x0081: "“", 0x0082: "”", 0x301C: "━", 0x303D: "■", 0x3366: "□",
    0x3404: "․", 0x3441: "■", 0x3446: "→", 0x35E1: "─", 0x3479: "▷",
    0x347A: "▶", 0x2F67: "▸",
}

SIMPLE_CTRL = {
    9: (6, 3, "\t"),
    18: (6, 3, " "),
    19: (6, 3, " "),
    20: (6, 3, " "),
    21: (6, 3, " "),
    22: (22, 11, " "),
    23: (8, 4, " "),
    24: (4, 2, "-"),
    25: (4, 2, ""),
    26: (244, 122, " "),
    28: (62, 31, " "),
    30: (2, 1, " "),
    31: (2, 1, " "),
}


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def remaining(self) -> int:
        return len(self.data) - self.pos

    def eof(self) -> bool:
        return self.pos >= len(self.data)

    def ensure(self, n: int) -> None:
        if n < 0 or self.pos + n > len(self.data):
            raise ValueError(f"insufficient data need={n} remaining={self.remaining()} pos={self.pos}")

    def skip(self, n: int) -> None:
        self.ensure(n)
        self.pos += n

    def read_u8(self) -> int:
        self.ensure(1)
        v = self.data[self.pos]
        self.pos += 1
        return v

    def read_u16(self) -> int:
        self.ensure(2)
        v = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return v

    def read_u32(self) -> int:
        self.ensure(4)
        v = struct.unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return v

    def read_bytes(self, n: int) -> bytes:
        self.ensure(n)
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def decode_hchar(ch: int) -> str:
    if ch < 0x80:
        return chr(ch)
    if 0x3590 <= ch <= 0x3599:
        return chr(0x2160 + (ch - 0x3590))
    if 0x36E7 <= ch <= 0x36F0:
        return chr(0x2460 + (ch - 0x36E7))
    if 0x37C0 <= ch <= 0x37C5:
        return "한글과컴퓨터"[ch - 0x37C0]
    if ch in EXTRA_MAP:
        return EXTRA_MAP[ch]
    if ch >= 0x8000:
        cho = CHO_MAP[(ch >> 10) & 0x1F]
        jung = JUNG_MAP[(ch >> 5) & 0x1F]
        jong = JONG_MAP[ch & 0x1F]
        if cho >= 0 and jung >= 0 and jong >= 0:
            return chr(0xAC00 + cho * 588 + jung * 28 + jong)
        try:
            return ch.to_bytes(2, "big").decode("johab")
        except Exception:
            return ""
    return ""


def skip_fonts_styles(r: Reader) -> Dict[str, Any]:
    font_counts: List[int] = []
    for _ in range(7):
        n = r.read_u16()
        font_counts.append(n)
        r.skip(n * 40)
    n_styles = r.read_u16()
    r.skip(n_styles * STYLE_RECORD_SIZE)
    return {"font_counts": font_counts, "style_count": n_styles, "paragraph_list_offset": r.pos}


def parse_picture(r: Reader, ctx: Dict[str, Any], depth: int) -> None:
    info = r.read_bytes(348)
    n_ext = struct.unpack_from("<I", info, 0)[0]
    if n_ext > 100 * 1024 * 1024 or n_ext > r.remaining():
        raise ValueError(f"invalid picture extension length {n_ext}")
    if n_ext:
        r.skip(n_ext)
    parse_paragraph_list(r, ctx, depth + 1)


def parse_table(r: Reader, ctx: Dict[str, Any], depth: int) -> None:
    info = r.read_bytes(84)
    cell_count = struct.unpack_from("<H", info, 80)[0] or 1
    if cell_count > MAX_CELL_COUNT or cell_count * 27 > r.remaining():
        raise ValueError(f"invalid table cell_count={cell_count}")
    r.skip(cell_count * 27)
    for _ in range(cell_count):
        parse_paragraph_list(r, ctx, depth + 1)
    parse_paragraph_list(r, ctx, depth + 1)


def parse_char_stream(r: Reader, char_count: int, ctx: Dict[str, Any], depth: int) -> str:
    out: List[str] = []
    i = 0
    while i < char_count:
        ch = r.read_u16()
        i += 1
        if ch == 13:
            out.append("\n")
            continue
        if ch == 0:
            continue
        if ch >= 32:
            out.append(decode_hchar(ch))
            continue
        simple = SIMPLE_CTRL.get(ch)
        if simple:
            extra_bytes, extra_hchars, emit = simple
            r.skip(extra_bytes)
            i += extra_hchars
            if emit:
                out.append(emit)
            continue

        header_val1 = r.read_u32()
        _ch2 = r.read_u16()
        i += 3

        if ch == 10:
            parse_table(r, ctx, depth)
        elif ch == 11:
            parse_picture(r, ctx, depth)
        elif ch == 14:
            r.skip(84)
        elif ch == 15:
            r.skip(8)
            parse_paragraph_list(r, ctx, depth + 1)
        elif ch == 16:
            r.skip(10)
            parse_paragraph_list(r, ctx, depth + 1)
        elif ch == 17:
            r.skip(14)
            parse_paragraph_list(r, ctx, depth + 1)
        elif ch == 5:
            if 0 < header_val1 < 1_000_000:
                r.skip(header_val1)
        elif ch == 6:
            r.skip(34)
        elif ch == 7:
            r.skip(76)
        elif ch == 8:
            r.skip(88)
        elif ch == 29:
            if header_val1 < 1_000_000:
                r.skip(header_val1)
        else:
            ctx["unsupported_controls"].setdefault(str(ch), 0)
            ctx["unsupported_controls"][str(ch)] += 1

    return re.sub(r"[ \t]+", " ", "".join(out)).strip()


def parse_paragraph_list(r: Reader, ctx: Dict[str, Any], depth: int = 0) -> None:
    if depth > MAX_RECURSION:
        raise ValueError("HWP3 recursion safety limit exceeded")
    ctx["max_depth"] = max(ctx["max_depth"], depth)
    while not r.eof():
        if ctx["paragraph_headers"] >= MAX_PARAGRAPHS:
            raise ValueError("paragraph safety limit exceeded")
        start = r.pos
        follow_prev = r.read_u8()
        char_count = r.read_u16()
        ctx["paragraph_headers"] += 1
        if char_count == 0:
            r.skip(40)
            ctx["sentinels"] += 1
            return
        line_count = r.read_u16()
        if char_count > 60000 or line_count > 4096:
            raise ValueError(f"abnormal paragraph header char_count={char_count} line_count={line_count} at={start}")
        include_char_shape = r.read_u8()
        r.skip(1 + 4 + 1 + 31)
        if follow_prev == 0:
            r.skip(PARA_SHAPE_SIZE)
        r.skip(line_count * LINE_INFO_SIZE)
        if include_char_shape:
            for _ in range(char_count):
                flag = r.read_u8()
                if flag != 1:
                    r.skip(INLINE_CHAR_SHAPE_SIZE)
        text = parse_char_stream(r, char_count, ctx, depth)
        if text:
            ctx["paragraphs"].append(text)


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HWP3 BOUNDED PARAGRAPH TEXT EXTRACTION")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Network requests: 0")
    print("HWP3 sample count: 1")
    print("OCR: DISABLED")
    print("External converter: DISABLED")
    print("Bulk archive traversal: DISABLED")
    print()

    if not T28S111.exists():
        raise FileNotFoundError(T28S111)
    prior = json.loads(T28S111.read_text(encoding="utf-8"))
    if not prior.get("technical_success"):
        raise AssertionError("prior HWP3 compressed-stream validation not successful")
    path = Path(norm(prior.get("sample_path")))
    if not path.exists():
        raise FileNotFoundError(path)

    data = path.read_bytes()
    offset = int(prior.get("compressed_stream_offset") or 0)
    dec = zlib.decompressobj(-zlib.MAX_WBITS)
    body = dec.decompress(data[offset:]) + dec.flush()
    if not dec.eof:
        raise AssertionError("HWP3 raw deflate did not reach EOF")

    r = Reader(body)
    preamble = skip_fonts_styles(r)
    ctx: Dict[str, Any] = {
        "paragraphs": [],
        "paragraph_headers": 0,
        "sentinels": 0,
        "max_depth": 0,
        "unsupported_controls": {},
        "parse_error": "",
    }
    try:
        parse_paragraph_list(r, ctx, 0)
    except Exception as exc:
        ctx["parse_error"] = repr(exc)

    merged = "\n".join(ctx["paragraphs"])
    direct = {t: merged.count(t) for t in DIRECT}
    related = {t: merged.count(t) for t in RELATED}
    hangul = len(re.findall(r"[가-힣]", merged))
    text_chars = len(merged)
    meaningful = text_chars > 100 and hangul > 100 and len(ctx["paragraphs"]) > 0

    if meaningful and any(direct.values()):
        classification = "HWP3_TEXT_EXTRACTED_DIRECT_UQQ700_TERM_FOUND"
    elif meaningful and any(related.values()):
        classification = "HWP3_TEXT_EXTRACTED_RELATED_TERM_FOUND"
    elif meaningful:
        classification = "HWP3_TEXT_EXTRACTION_VALIDATED_NO_UQQ700_TERM_IN_SAMPLE"
    else:
        classification = "HWP3_TEXT_EXTRACTION_NOT_VALIDATED"

    output = {
        "step": "STEP 17-21-C-16-8-T-28-S1-12 Municipal Gazette HWP3 Bounded Paragraph Text Extraction",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "network_request_count": 0,
        "sample_path": str(path),
        "decompressed_body_bytes": len(body),
        "unused_trailing_bytes": len(dec.unused_data),
        "preamble": preamble,
        "parse": {
            "paragraph_headers": ctx["paragraph_headers"],
            "paragraph_count": len(ctx["paragraphs"]),
            "sentinel_count": ctx["sentinels"],
            "max_recursion_depth": ctx["max_depth"],
            "reader_consumed_bytes": r.pos,
            "reader_remaining_bytes": r.remaining(),
            "unsupported_controls": ctx["unsupported_controls"],
            "parse_error": ctx["parse_error"],
        },
        "text": {
            "chars": text_chars,
            "hangul_chars": hangul,
            "direct_matches": direct,
            "related_matches": related,
            "preview": merged[:2000],
        },
        "meaningful_text_recovered": meaningful,
        "classification": classification,
        "ocr_executed": False,
        "external_converter_executed": False,
        "bulk_archive_traversal_executed": False,
        "semantic_note": "One 2003 gazette sample only. No-match is not historical negative evidence and cannot produce UQQ700 FALSE.",
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
        "resolution": "MUNICIPAL_GAZETTE_HWP3_BOUNDED_PARAGRAPH_TEXT_EXTRACTION_COMPLETED",
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Sample:", path)
    print("Decompressed body bytes:", len(body))
    print("Unused trailing bytes:", len(dec.unused_data))
    print("Font counts:", preamble["font_counts"])
    print("Style count:", preamble["style_count"])
    print("Paragraph list offset:", preamble["paragraph_list_offset"])
    print("Paragraph headers:", ctx["paragraph_headers"])
    print("Paragraphs extracted:", len(ctx["paragraphs"]))
    print("Sentinels:", ctx["sentinels"])
    print("Max recursion depth:", ctx["max_depth"])
    print("Reader consumed/remaining:", r.pos, r.remaining())
    print("Unsupported controls:", ctx["unsupported_controls"])
    print("Parse error:", ctx["parse_error"])
    print("Text chars:", text_chars)
    print("Hangul chars:", hangul)
    print("Direct matches:", direct)
    print("Related matches:", related)
    print("Text preview:", repr(merged[:1200]))
    print("Classification:", classification)
    print("Resolution:", output["resolution"])
    print("Output:", OUT)

    unsafe = any([
        output["ocr_executed"], output["external_converter_executed"], output["bulk_archive_traversal_executed"],
        output["verified_positive"], output["runtime_registration_allowed"], output["site_positive_allowed"],
        output["site_negative_allowed"], output["final_positive_promotion_allowed"],
    ])
    vals = {
        "prior HWP3 boundary validation exists": T28S111.exists(),
        "sample exists": path.exists(),
        "network request count zero": output["network_request_count"] == 0,
        "raw deflate reaches EOF": dec.eof,
        "font/style preamble parsed": preamble["paragraph_list_offset"] > 0,
        "paragraph headers recovered": ctx["paragraph_headers"] > 0,
        "paragraph text recovered": len(ctx["paragraphs"]) > 0,
        "searchable Hangul text recovered": hangul > 100,
        "meaningful text threshold passed": meaningful,
        "OCR disabled": not output["ocr_executed"],
        "external converter disabled": not output["external_converter_executed"],
        "bulk archive traversal disabled": not output["bulk_archive_traversal_executed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("HWP3 bounded paragraph text extraction failed")


if __name__ == "__main__":
    main()
