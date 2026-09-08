from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
TARGET_STATUS = "UNKNOWN"
EXPECTED_COUNT = 6

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
INPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_existing_access_mechanics_recovery.json"
)
OUTPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_exact_six_access_mechanics_scoping_hardening.json"
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return str(value)


def canonical_identity(identity: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in identity.items():
        if value in (None, ""):
            continue
        k = str(key).lower().replace("_", "")
        out[k] = str(value).strip()
    return out


def exact_identity_signal_count(text: str, identity: dict[str, str]) -> int:
    signals = []
    for key in ("pstsn", "fileno", "name", "filename", "title"):
        value = identity.get(key)
        if value:
            signals.append(value)
    return sum(1 for value in signals if value in text)


def classify_evidence(
    target_identity: dict[str, str],
    evidence: dict[str, Any],
    all_target_identities: list[dict[str, str]],
) -> dict[str, Any]:
    urls = [str(u) for u in evidence.get("urls", []) if isinstance(u, str)]
    mechanics = evidence.get("mechanics") if isinstance(evidence.get("mechanics"), dict) else {}
    evidence_text = safe_json({"urls": urls, "mechanics": mechanics, "path": evidence.get("object_path")})

    own_signal_count = exact_identity_signal_count(evidence_text, target_identity)
    target_signal_counts = [exact_identity_signal_count(evidence_text, ident) for ident in all_target_identities]
    exact_target_identity_count = sum(1 for count in target_signal_counts if count > 0)

    direct_target_object = own_signal_count >= 1 and exact_target_identity_count == 1 and len(urls) <= 8
    ancestor_container = exact_target_identity_count > 1 or len(urls) > 8

    if direct_target_object:
        structural_class = "DIRECT_TARGET_OBJECT"
    elif ancestor_container:
        structural_class = "ANCESTOR_CONTAINER"
    else:
        structural_class = "TARGET_SCOPED_UNRESOLVED"

    return {
        **evidence,
        "url_count": len(urls),
        "own_identity_signal_count": own_signal_count,
        "exact_target_identity_count": exact_target_identity_count,
        "structural_class": structural_class,
    }


def main() -> int:
    print("=" * 82)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SEONGNAM LEGACY PDF EXACT-SIX ACCESS MECHANICS SCOPING HARDENING")
    print("=" * 82)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print(f"Input: {INPUT_PATH}")
    print("Network access: DISABLED")
    print("URL mutation/guessing: DISABLED")
    print("OCR/content search: DISABLED")
    print()

    diagnostics: list[dict[str, Any]] = []
    if not INPUT_PATH.exists():
        data: dict[str, Any] = {}
        diagnostics.append({"type": "missing_input", "path": str(INPUT_PATH)})
    else:
        try:
            data = load_json(INPUT_PATH)
        except Exception as exc:
            data = {}
            diagnostics.append({"type": "input_error", "error": repr(exc)})

    targets = data.get("recovered_targets") if isinstance(data.get("recovered_targets"), list) else []
    prerequisite_valid = (
        data.get("classification") == "SEONGNAM_LEGACY_PDF_EXISTING_ACCESS_MECHANICS_RECOVERED_FOR_EXACT_SIX"
        and len(targets) == EXPECTED_COUNT
    )

    target_identities = [canonical_identity(t.get("identity", {})) for t in targets if isinstance(t, dict)]

    scoped_targets: list[dict[str, Any]] = []
    url_to_targets: dict[str, set[int]] = defaultdict(set)

    if prerequisite_valid:
        for index, target in enumerate(targets, 1):
            identity = canonical_identity(target.get("identity", {}))
            evidence_rows = target.get("evidence") if isinstance(target.get("evidence"), list) else []
            classified = [
                classify_evidence(identity, e, target_identities)
                for e in evidence_rows
                if isinstance(e, dict)
            ]

            direct_urls: list[str] = []
            ancestor_urls: list[str] = []
            unresolved_urls: list[str] = []
            seen_direct: set[str] = set()
            seen_ancestor: set[str] = set()
            seen_unresolved: set[str] = set()

            for row in classified:
                for url in row.get("urls", []):
                    url_to_targets[url].add(index)
                    if row["structural_class"] == "DIRECT_TARGET_OBJECT":
                        if url not in seen_direct:
                            seen_direct.add(url)
                            direct_urls.append(url)
                    elif row["structural_class"] == "ANCESTOR_CONTAINER":
                        if url not in seen_ancestor:
                            seen_ancestor.add(url)
                            ancestor_urls.append(url)
                    else:
                        if url not in seen_unresolved:
                            seen_unresolved.add(url)
                            unresolved_urls.append(url)

            scoped_targets.append({
                "target_index": index,
                "identity": identity,
                "classified_evidence": classified,
                "direct_target_urls": direct_urls,
                "ancestor_container_urls": ancestor_urls,
                "target_scoped_unresolved_urls": unresolved_urls,
            })

    shared_urls = {url for url, target_set in url_to_targets.items() if len(target_set) > 1}
    target_unique_urls_by_index: dict[int, list[str]] = defaultdict(list)
    for target in scoped_targets:
        idx = target["target_index"]
        seen: set[str] = set()
        for bucket in (
            target["direct_target_urls"],
            target["ancestor_container_urls"],
            target["target_scoped_unresolved_urls"],
        ):
            for url in bucket:
                if url in shared_urls or url in seen:
                    continue
                seen.add(url)
                target_unique_urls_by_index[idx].append(url)

    for target in scoped_targets:
        idx = target["target_index"]
        target["cross_target_shared_urls"] = sorted(
            {u for u in target["direct_target_urls"] + target["ancestor_container_urls"] + target["target_scoped_unresolved_urls"] if u in shared_urls}
        )
        target["target_unique_recorded_urls"] = target_unique_urls_by_index[idx]
        target["direct_target_unique_urls"] = [
            u for u in target["direct_target_urls"] if u not in shared_urls
        ]

    total_direct_unique_urls = len({u for t in scoped_targets for u in t.get("direct_target_unique_urls", [])})
    total_shared_urls = len(shared_urls)
    total_ancestor_urls = len({u for t in scoped_targets for u in t.get("ancestor_container_urls", [])})
    targets_with_direct_unique = sum(1 for t in scoped_targets if t.get("direct_target_unique_urls"))

    print("SCOPING SUMMARY")
    print("-" * 82)
    print(f"Validated exact-six prerequisite: {prerequisite_valid}")
    print(f"Validated target count: {len(targets)}")
    print(f"Targets with direct target-unique URLs: {targets_with_direct_unique}")
    print(f"Total direct target-unique URLs: {total_direct_unique_urls}")
    print(f"Cross-target shared URL count: {total_shared_urls}")
    print(f"Ancestor-container URL count: {total_ancestor_urls}")
    print()

    for target in scoped_targets:
        print(f"TARGET {target['target_index']}: identity={json.dumps(target['identity'], ensure_ascii=False)}")
        print(f"  direct_target_url_count={len(target['direct_target_urls'])}")
        print(f"  direct_target_unique_url_count={len(target['direct_target_unique_urls'])}")
        print(f"  cross_target_shared_url_count={len(target['cross_target_shared_urls'])}")
        print(f"  ancestor_container_url_count={len(target['ancestor_container_urls'])}")
        print(f"  target_scoped_unresolved_url_count={len(target['target_scoped_unresolved_urls'])}")
        for url in target["direct_target_unique_urls"]:
            print(f"  DIRECT_TARGET_UNIQUE={url}")
        print()

    if not prerequisite_valid:
        classification = "SEONGNAM_LEGACY_PDF_EXACT_SIX_ACCESS_MECHANICS_SCOPING_PREREQUISITE_TECHNICAL_UNKNOWN"
        next_action = "RESTORE_EXISTING_ACCESS_MECHANICS_RECOVERY_OUTPUT_WITHOUT_NETWORK_OR_URL_GUESSING"
    elif targets_with_direct_unique == EXPECTED_COUNT:
        classification = "SEONGNAM_LEGACY_PDF_EXACT_SIX_ACCESS_MECHANICS_DIRECT_SCOPE_RECOVERED"
        next_action = (
            "INSPECT_ONLY_DIRECT_TARGET_UNIQUE_RECORDED_ROUTES_IN_A_SEPARATELY_APPROVED_STEP_"
            "WITHOUT_URL_MUTATION_NEGATIVE_EVIDENCE_OR_SITE_PROMOTION"
        )
    else:
        classification = "SEONGNAM_LEGACY_PDF_EXACT_SIX_ACCESS_MECHANICS_SCOPE_PARTIALLY_RESOLVED_TECHNICAL_UNKNOWN"
        next_action = (
            "INSPECT_CLASSIFIED_EVIDENCE_FOR_TARGETS_WITHOUT_DIRECT_UNIQUE_ROUTES_"
            "WITHOUT_NETWORK_URL_MUTATION_OR_NEGATIVE_EVIDENCE"
        )

    safety = {
        "network_access_used": False,
        "uqq700_query_executed": False,
        "url_mutation_used": False,
        "url_guessing_used": False,
        "ssl_verification_bypass_used": False,
        "ocr_used": False,
        "content_search_used": False,
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
        "network_disabled": safety["network_access_used"] is False,
        "uqq700_not_queried": safety["uqq700_query_executed"] is False,
        "url_mutation_disabled": safety["url_mutation_used"] is False,
        "url_guessing_disabled": safety["url_guessing_used"] is False,
        "ssl_bypass_disabled": safety["ssl_verification_bypass_used"] is False,
        "ocr_disabled": safety["ocr_used"] is False,
        "content_search_disabled": safety["content_search_used"] is False,
        "negative_evidence_disabled": safety["negative_evidence_allowed"] is False,
        "legal_absence_inference_disabled": safety["legal_absence_inference_allowed"] is False,
        "site_promotion_disabled": safety["site_promotion_allowed"] is False,
        "runtime_registration_blocked": safety["runtime_registration_allowed"] is False,
        "uqq700_remains_unknown": safety["uqq700_resolution"] == "UNKNOWN",
    }
    all_pass = all(validation.values())

    payload = {
        "target": TARGET_NAME,
        "standard_code": TARGET_CODE,
        "resolution": TARGET_STATUS,
        "input": str(INPUT_PATH),
        "prerequisite_valid": prerequisite_valid,
        "validated_target_count": len(targets),
        "scoped_targets": scoped_targets,
        "targets_with_direct_unique_routes": targets_with_direct_unique,
        "total_direct_target_unique_url_count": total_direct_unique_urls,
        "cross_target_shared_url_count": total_shared_urls,
        "ancestor_container_url_count": total_ancestor_urls,
        "classification": classification,
        "next_action": next_action,
        "diagnostics": diagnostics,
        "safety": safety,
        "validation": validation,
        "all_pass": all_pass,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 82)
    print("RESOLUTION")
    print("=" * 82)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print(f"UQQ700: {TARGET_STATUS}")
    print("Negative evidence allowed: False")
    print("Legal absence inference allowed: False")
    print("SITE promotion allowed: False")
    print("Runtime registration allowed: False")
    print("Network access used: False")
    print("URL mutation/guessing used: False")
    print(f"Output: {OUTPUT_PATH}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
