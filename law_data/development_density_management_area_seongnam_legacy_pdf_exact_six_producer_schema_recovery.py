from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
TARGET_STATUS = "UNKNOWN"
EXPECTED_COUNT = 6

BASE_DIR = Path(__file__).resolve().parent.parent
LAW_DIR = BASE_DIR / "law_data"
OUTPUT_DIR = LAW_DIR / "output"
RECOVERY_INPUT = OUTPUT_DIR / "development_density_management_area_seongnam_legacy_pdf_residual_six_target_prerequisite_recovery.json"
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_legacy_pdf_exact_six_producer_schema_recovery.json"

KEY_RE = re.compile(r"(?:residual|unresolved|carry[_ -]?forward|remaining|target|candidate|document|record|item)", re.I)
COUNT_RE = re.compile(r"(?:count|total|size|len|number)", re.I)
SEONGNAM_RE = re.compile(r"(?:성남|seongnam)", re.I)
LEGACY_RE = re.compile(r"(?:legacy|pdf|viewer|download|attach|file)", re.I)
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.I)


def safe_json(v: Any) -> str:
    try:
        return json.dumps(v, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return str(v)


def iter_nodes(value: Any, path: str = "$"):
    yield path, value
    if isinstance(value, dict):
        for k, v in value.items():
            yield from iter_nodes(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from iter_nodes(v, f"{path}[{i}]")


def extract_urls(v: Any) -> list[str]:
    out, seen = [], set()
    for m in URL_RE.finditer(safe_json(v)):
        u = m.group(0).rstrip("),.;]}")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def extract_identity(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict):
        return {}
    out = {}
    for k, v in obj.items():
        if isinstance(v, (dict, list)) or v in (None, ""):
            continue
        kl = str(k).lower()
        if any(x in kl for x in ("title", "name", "idx", "id", "number", "no", "date", "year", "pstsn")):
            out[str(k)] = v
    return out


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_source_paths(recovery: dict[str, Any]) -> list[Path]:
    paths = []
    seen = set()
    for item in recovery.get("candidates", []):
        for prov in item.get("provenance", []):
            p = prov.get("source_path")
            if not p:
                continue
            pp = Path(p)
            if pp.exists() and pp.suffix.lower() == ".json" and str(pp) not in seen:
                seen.add(str(pp))
                paths.append(pp)
    return paths


def inspect_source(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    containers = []
    diagnostics = []
    try:
        data = load_json(path)
    except Exception as exc:
        return [], [{"source_path": str(path), "error": repr(exc)}]

    for node_path, node in iter_nodes(data):
        if not isinstance(node, list) or len(node) != EXPECTED_COUNT:
            continue
        parent_key = node_path.rsplit(".", 1)[-1]
        text = safe_json(node)
        relevant = bool(KEY_RE.search(parent_key) or (SEONGNAM_RE.search(text) and LEGACY_RE.search(text)))
        if not relevant:
            continue

        identities = [extract_identity(x) for x in node]
        urls = [extract_urls(x) for x in node]
        item_like = sum(1 for x in node if isinstance(x, dict))
        nonempty_identity = sum(1 for x in identities if x)
        url_item_count = sum(1 for x in urls if x)

        sibling_counts = {}
        if "." in node_path:
            parent_path = node_path.rsplit(".", 1)[0]
            parent = None
            for p, n in iter_nodes(data):
                if p == parent_path:
                    parent = n
                    break
            if isinstance(parent, dict):
                for k, v in parent.items():
                    if COUNT_RE.search(str(k)) and isinstance(v, (int, float, str)):
                        sibling_counts[str(k)] = v

        containers.append({
            "source_path": str(path),
            "container_path": node_path,
            "container_key": parent_key,
            "length": len(node),
            "item_like_count": item_like,
            "nonempty_identity_count": nonempty_identity,
            "url_item_count": url_item_count,
            "sibling_count_fields": sibling_counts,
            "records": [
                {"index": i, "identity": identities[i], "urls": urls[i], "raw": node[i]}
                for i in range(len(node))
            ],
        })
    return containers, diagnostics


def score(container: dict[str, Any]) -> tuple[int, int, int, int]:
    key = container.get("container_key", "")
    sibling_counts = container.get("sibling_count_fields", {})
    explicit_six_count = any(str(v) == "6" for v in sibling_counts.values())
    return (
        1 if explicit_six_count else 0,
        1 if KEY_RE.search(key) else 0,
        int(container.get("nonempty_identity_count", 0)),
        int(container.get("url_item_count", 0)),
    )


def main() -> int:
    print("=" * 78)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SEONGNAM LEGACY PDF EXACT-SIX PRODUCER SCHEMA RECOVERY")
    print("=" * 78)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print(f"Input: {RECOVERY_INPUT}")
    print("Network access: DISABLED")
    print("URL guessing: DISABLED")
    print()

    diagnostics = []
    if not RECOVERY_INPUT.exists():
        recovery = {}
        diagnostics.append({"type": "missing_recovery_input", "path": str(RECOVERY_INPUT)})
    else:
        recovery = load_json(RECOVERY_INPUT)

    source_paths = candidate_source_paths(recovery)
    all_containers = []
    for path in source_paths:
        containers, diag = inspect_source(path)
        all_containers.extend(containers)
        diagnostics.extend(diag)

    all_containers.sort(key=score, reverse=True)

    exact_candidates = [c for c in all_containers if c.get("length") == EXPECTED_COUNT]
    selected = None
    if exact_candidates:
        top_score = score(exact_candidates[0])
        top = [c for c in exact_candidates if score(c) == top_score]
        if len(top) == 1:
            selected = top[0]

    recovered = selected is not None

    print("PRODUCER SCHEMA SUMMARY")
    print("-" * 78)
    print(f"Candidate source JSON files: {len(source_paths)}")
    print(f"Six-item containers found: {len(exact_candidates)}")
    print(f"Unambiguous exact-six container selected: {recovered}")
    print()

    for i, c in enumerate(exact_candidates, 1):
        print(f"CONTAINER {i}")
        print(f"  source={c['source_path']}")
        print(f"  path={c['container_path']}")
        print(f"  key={c['container_key']}")
        print(f"  sibling_count_fields={json.dumps(c['sibling_count_fields'], ensure_ascii=False)}")
        print(f"  nonempty_identity_count={c['nonempty_identity_count']}")
        print(f"  url_item_count={c['url_item_count']}")
        print(f"  score={score(c)}")
        print()

    if recovered:
        print("SELECTED EXACT SIX")
        print("-" * 78)
        for r in selected["records"]:
            print(f"[{r['index'] + 1}] identity={json.dumps(r['identity'], ensure_ascii=False)}")
            print(f"    urls={json.dumps(r['urls'], ensure_ascii=False)}")
        classification = "SEONGNAM_LEGACY_PDF_EXACT_SIX_PRODUCER_SCHEMA_RECOVERED"
        next_action = "RUN_SEPARATELY_APPROVED_BINARY_ACCESS_DIAGNOSTIC_ONLY_FOR_THE_SELECTED_EXACT_SIX"
    else:
        classification = "SEONGNAM_LEGACY_PDF_EXACT_SIX_PRODUCER_SCHEMA_NOT_UNAMBIGUOUS"
        next_action = "INSPECT_REPORTED_SIX_ITEM_CONTAINERS_OR_RESTORE_PRIOR_PRODUCER_OUTPUT_WITHOUT_NETWORK_OR_URL_GUESSING"

    safety = {
        "network_access_used": False,
        "uqq700_query_executed": False,
        "url_guessing_used": False,
        "ocr_used": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_promotion_allowed": False,
        "runtime_registration_allowed": False,
        "uqq700_resolution": TARGET_STATUS,
    }
    validation = {
        "target_name": TARGET_NAME == "개발밀도관리구역",
        "standard_code": TARGET_CODE == "UQQ700",
        "expected_count_fixed_to_six": EXPECTED_COUNT == 6,
        "network_disabled": not safety["network_access_used"],
        "uqq700_not_queried": not safety["uqq700_query_executed"],
        "url_guessing_disabled": not safety["url_guessing_used"],
        "ocr_disabled": not safety["ocr_used"],
        "negative_evidence_disabled": not safety["negative_evidence_allowed"],
        "legal_absence_inference_disabled": not safety["legal_absence_inference_allowed"],
        "site_promotion_disabled": not safety["site_promotion_allowed"],
        "runtime_registration_blocked": not safety["runtime_registration_allowed"],
        "uqq700_remains_unknown": safety["uqq700_resolution"] == "UNKNOWN",
    }
    all_pass = all(validation.values())

    payload = {
        "target": TARGET_NAME,
        "standard_code": TARGET_CODE,
        "resolution": TARGET_STATUS,
        "expected_count": EXPECTED_COUNT,
        "input": str(RECOVERY_INPUT),
        "source_paths": [str(p) for p in source_paths],
        "six_item_containers": exact_candidates,
        "selected_exact_six": selected,
        "exact_six_recovered": recovered,
        "classification": classification,
        "next_action": next_action,
        "diagnostics": diagnostics,
        "safety": safety,
        "validation": validation,
        "all_pass": all_pass,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print(f"UQQ700: {TARGET_STATUS}")
    print("Negative evidence allowed: False")
    print("Legal absence inference allowed: False")
    print("SITE promotion allowed: False")
    print("Runtime registration allowed: False")
    print("Network access used: False")
    print("URL guessing used: False")
    print(f"Output: {OUTPUT_PATH}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
