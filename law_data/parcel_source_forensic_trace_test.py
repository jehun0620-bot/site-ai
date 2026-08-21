# -*- coding: utf-8 -*-

"""
STEP 17-21-C-11-2C-2C
Parcel Source Forensic Trace

목표
======================================================================
C-9 당시 Parcel Polygon을 실제로 읽었던 원본 경로나 처리 흔적을 역추적한다.

검색 대상
======================================================================
1. 프로젝트 내 Python / MD / TXT / JSON source
2. Git commit history
3. PowerShell PSReadLine history
4. 알려진 과거 geometry 값
5. geopandas / read_file / MapPlan 관련 코드

주의
======================================================================
.env 및 인증정보 파일은 읽지 않는다.
검색 결과는 context 일부만 저장한다.
"""

from __future__ import annotations

import json
import os
import subprocess

from pathlib import Path
from typing import Any, Dict, List


# ============================================================
# PATH
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "parcel_source_forensic_trace.json"
)


# ============================================================
# SEARCH TERMS
# ============================================================

SEARCH_TERMS = [

    # dataset
    "LP_PA_CBND_BUBUN",
    "PA_CBND_BUBUN",
    "CBND",

    # processing
    "MapPlan",
    "geopandas",
    "gpd.read_file",
    "read_file(",

    # historic known geometry evidence
    "120945.65223377591",
    "962201.02522",
    "1943722.58159",
    "962711.06096",
    "1944220.16506",

    # site
    "1168010300100120000",

    # common spatial formats
    ".shp",
    ".gpkg",
    ".geojson",
]


TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ps1",
    ".bat",
    ".cmd",
}


SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
}


SKIP_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
}


# ============================================================
# util
# ============================================================

def save_json(
    data: Dict[str, Any],
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


def is_skipped_path(
    path: Path,
) -> bool:

    if (
        path.name
        in SKIP_FILES
    ):
        return True

    return any(
        part
        in SKIP_DIRS
        for part
        in path.parts
    )


def safe_read_text(
    path: Path,
) -> str:

    for encoding in (
        "utf-8",
        "utf-8-sig",
        "cp949",
    ):

        try:

            return path.read_text(
                encoding=encoding,
                errors="strict",
            )

        except (
            UnicodeDecodeError,
            OSError,
        ):

            continue

    return ""


def context_preview(
    text: str,
    position: int,
    term: str,
    radius: int = 180,
) -> str:

    start = max(
        0,
        position - radius,
    )

    end = min(
        len(text),
        position
        + len(term)
        + radius,
    )

    return (
        text[
            start:end
        ]
        .replace(
            "\r",
            " ",
        )
        .replace(
            "\n",
            " ",
        )
    )


# ============================================================
# 1. PROJECT SOURCE SCAN
# ============================================================

def scan_project_sources() -> List[
    Dict[str, Any]
]:

    hits = []

    for path in BASE_DIR.rglob(
        "*"
    ):

        if not path.is_file():
            continue

        if is_skipped_path(
            path
        ):
            continue

        if (
            path.suffix.lower()
            not in TEXT_SUFFIXES
        ):
            continue

        text = safe_read_text(
            path
        )

        if not text:
            continue

        lower_text = (
            text.lower()
        )

        for term in SEARCH_TERMS:

            position = (
                lower_text.find(
                    term.lower()
                )
            )

            if position < 0:
                continue

            hits.append(
                {
                    "source": (
                        "PROJECT_SOURCE"
                    ),

                    "path": (
                        str(
                            path
                        )
                    ),

                    "relative_path": (
                        str(
                            path.relative_to(
                                BASE_DIR
                            )
                        )
                    ),

                    "term": (
                        term
                    ),

                    "preview": (
                        context_preview(
                            text,
                            position,
                            term,
                        )
                    ),
                }
            )

    return hits


# ============================================================
# 2. GIT HISTORY
# ============================================================

def run_git(
    args: List[str],
) -> str:

    try:

        result = subprocess.run(
            [
                "git",
                *args,
            ],
            cwd=BASE_DIR,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )

        if (
            result.returncode
            != 0
        ):

            return ""

        return (
            result.stdout
        )

    except (
        subprocess.TimeoutExpired,
        OSError,
    ):

        return ""


def scan_git_history() -> List[
    Dict[str, Any]
]:

    hits = []

    # --------------------------------------------------------
    # Git -S pickaxe search
    # --------------------------------------------------------

    git_terms = [
        "LP_PA_CBND_BUBUN",
        "MapPlan",
        "120945.65223377591",
        "962201.02522",
        "gpd.read_file",
    ]

    for term in git_terms:

        output = run_git(
            [
                "log",
                "--all",
                "--oneline",
                "-S",
                term,
                "--",
                "*.py",
                "*.md",
                "*.json",
            ]
        )

        if not output.strip():
            continue

        hits.append(
            {
                "source": (
                    "GIT_HISTORY"
                ),

                "term": (
                    term
                ),

                "matches": (
                    output.strip().splitlines()[
                        :30
                    ]
                ),
            }
        )

    # --------------------------------------------------------
    # Git grep current tracked files
    # --------------------------------------------------------

    for term in git_terms:

        output = run_git(
            [
                "grep",
                "-n",
                "-I",
                term,
            ]
        )

        if not output.strip():
            continue

        hits.append(
            {
                "source": (
                    "GIT_GREP"
                ),

                "term": (
                    term
                ),

                "matches": (
                    output.strip().splitlines()[
                        :50
                    ]
                ),
            }
        )

    return hits


# ============================================================
# 3. POWERSHELL HISTORY
# ============================================================

def possible_powershell_history_paths() -> List[
    Path
]:

    appdata = os.getenv(
        "APPDATA"
    )

    candidates = []

    if appdata:

        candidates.append(
            Path(
                appdata
            )
            / "Microsoft"
            / "Windows"
            / "PowerShell"
            / "PSReadLine"
            / "ConsoleHost_history.txt"
        )

    userprofile = os.getenv(
        "USERPROFILE"
    )

    if userprofile:

        candidates.append(
            Path(
                userprofile
            )
            / "AppData"
            / "Roaming"
            / "Microsoft"
            / "Windows"
            / "PowerShell"
            / "PSReadLine"
            / "ConsoleHost_history.txt"
        )

    # dedup
    unique = []

    seen = set()

    for path in candidates:

        key = str(
            path
        ).lower()

        if key in seen:
            continue

        seen.add(
            key
        )

        unique.append(
            path
        )

    return unique


def scan_powershell_history() -> Dict[
    str,
    Any
]:

    histories = []

    interesting_terms = [
        "LP_PA_CBND",
        "CBND",
        "MapPlan",
        "geopandas",
        "read_file",
        ".shp",
        ".zip",
        "1168010300100120000",
    ]

    for path in (
        possible_powershell_history_paths()
    ):

        if not path.exists():

            histories.append(
                {
                    "path": (
                        str(
                            path
                        )
                    ),

                    "exists": (
                        False
                    ),
                }
            )

            continue

        text = safe_read_text(
            path
        )

        lines = (
            text.splitlines()
        )

        matches = []

        for index, line in enumerate(
            lines,
            start=1,
        ):

            if not any(
                term.lower()
                in line.lower()
                for term
                in interesting_terms
            ):

                continue

            # 환경변수 set 명령 등은 출력하지 않는다.
            if (
                "api_key"
                in line.lower()
                or "service_key"
                in line.lower()
                or "secret"
                in line.lower()
                or "token"
                in line.lower()
            ):

                continue

            matches.append(
                {
                    "line": (
                        index
                    ),

                    "text": (
                        line
                    ),
                }
            )

        histories.append(
            {
                "path": (
                    str(
                        path
                    )
                ),

                "exists": (
                    True
                ),

                "match_count": (
                    len(
                        matches
                    )
                ),

                "matches": (
                    matches[
                        -100:
                    ]
                ),
            }
        )

    return {
        "histories": (
            histories
        ),
    }


# ============================================================
# ranking
# ============================================================

def rank_source_hits(
    hits: List[
        Dict[str, Any]
    ],
) -> List[
    Dict[str, Any]
]:

    ranked = []

    for item in hits:

        term = (
            item.get(
                "term",
                "",
            )
        )

        preview = (
            item.get(
                "preview",
                "",
            )
        )

        score = 0

        if (
            term
            == "LP_PA_CBND_BUBUN"
        ):

            score += 100

        if (
            "read_file"
            in preview
        ):

            score += 50

        if (
            ".shp"
            in preview.lower()
        ):

            score += 40

        if (
            ".zip"
            in preview.lower()
        ):

            score += 20

        if (
            "MapPlan"
            in preview
        ):

            score += 20

        if (
            "120945.65223377591"
            in preview
        ):

            score += 30

        ranked.append(
            {
                **item,
                "score": (
                    score
                ),
            }
        )

    return sorted(
        ranked,
        key=lambda item: (
            item[
                "score"
            ]
        ),
        reverse=True,
    )


# ============================================================
# main
# ============================================================

def main() -> int:

    project_hits = (
        scan_project_sources()
    )

    git_hits = (
        scan_git_history()
    )

    powershell = (
        scan_powershell_history()
    )

    ranked_project_hits = (
        rank_source_hits(
            project_hits
        )
    )

    powershell_match_count = sum(
        item.get(
            "match_count",
            0,
        )
        for item
        in powershell[
            "histories"
        ]
    )

    resolution = (
        "TRACE_EVIDENCE_FOUND"
        if (
            ranked_project_hits
            or git_hits
            or powershell_match_count
            > 0
        )
        else "NO_TRACE_EVIDENCE"
    )

    output = {
        "step": (
            "STEP 17-21-C-11-2C-2C "
            "Parcel source forensic trace"
        ),

        "summary": {
            "project_source_hits": (
                len(
                    project_hits
                )
            ),

            "git_history_hits": (
                len(
                    git_hits
                )
            ),

            "powershell_matches": (
                powershell_match_count
            ),
        },

        "ranked_project_source_hits": (
            ranked_project_hits
        ),

        "git_history": (
            git_hits
        ),

        "powershell_history": (
            powershell
        ),

        "resolution": (
            resolution
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "Project source hits:",
        len(
            project_hits
        ),
    )

    print(
        "Git history hits:",
        len(
            git_hits
        ),
    )

    print(
        "PowerShell matches:",
        powershell_match_count,
    )

    print()

    print(
        "=== TOP PROJECT SOURCE HITS ==="
    )

    if not ranked_project_hits:

        print(
            "NONE"
        )

    for item in (
        ranked_project_hits[
            :20
        ]
    ):

        print(
            f"- score={item['score']} "
            f"| {item['relative_path']} "
            f"| term={item['term']}"
        )

        print(
            "  ",
            item[
                "preview"
            ][
                :350
            ],
        )

    print()

    print(
        "=== GIT HISTORY ==="
    )

    if not git_hits:

        print(
            "NONE"
        )

    for item in git_hits:

        print(
            "-",
            item[
                "source"
            ],
            "|",
            item[
                "term"
            ],
        )

        for match in (
            item[
                "matches"
            ][
                :10
            ]
        ):

            print(
                "   ",
                match,
            )

    print()

    print(
        "=== POWERSHELL HISTORY ==="
    )

    for history in (
        powershell[
            "histories"
        ]
    ):

        if not history.get(
            "exists"
        ):

            print(
                "- history not found:",
                history[
                    "path"
                ],
            )

            continue

        print(
            "-",
            history[
                "path"
            ],
            "| matches=",
            history[
                "match_count"
            ],
        )

        for match in (
            history.get(
                "matches",
                [],
            )[
                -30:
            ]
        ):

            print(
                f"   [{match['line']}] "
                f"{match['text']}"
            )

    print()

    print(
        "resolution:",
        resolution,
    )

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )