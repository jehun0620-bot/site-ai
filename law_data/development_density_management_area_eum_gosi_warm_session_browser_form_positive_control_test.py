# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_eum_gosi_warm_session_browser_form_positive_control.json"
LIST_URL = "https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp"
HOST = "www.eum.go.kr"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 12 * 1024 * 1024

CONTROLS = [
    {"query": "분당지구단위계획", "expected_seq": "638968", "expected_notice": "2026-121"},
    {"query": "모란생태공원", "expected_seq": "632588", "expected_notice": "2026-87"},
]


def attrs_dict(attrs):
    return {str(k).lower(): ("" if v is None else str(v)) for k, v in attrs}


class BrowserFormParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_target = False
        self.depth = 0
        self.form = None
        self.controls = []
        self.current_select = None
        self.current_option = None
        self.current_textarea = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        a = attrs_dict(attrs)
        if tag == "form":
            if self.in_target:
                self.depth += 1
                return
            if a.get("id") == "frmGosi" or a.get("name") == "frmGosi":
                self.in_target = True
                self.depth = 1
                self.form = {
                    "action": a.get("action", ""),
                    "method": a.get("method", "get").lower(),
                    "id": a.get("id"),
                    "name": a.get("name"),
                }
            return
        if not self.in_target:
            return
        if tag == "input":
            name = a.get("name", "")
            typ = a.get("type", "text").lower()
            if not name or "disabled" in a or typ in {"submit", "button", "reset", "file", "image"}:
                return
            if typ in {"checkbox", "radio"} and "checked" not in a:
                return
            self.controls.append((name, a.get("value", "on" if typ in {"checkbox", "radio"} else "")))
        elif tag == "select":
            if a.get("name") and "disabled" not in a:
                self.current_select = {"name": a["name"], "multiple": "multiple" in a, "options": []}
        elif tag == "option" and self.current_select is not None:
            self.current_option = {"value": a.get("value"), "selected": "selected" in a, "text": []}
        elif tag == "textarea":
            if a.get("name") and "disabled" not in a:
                self.current_textarea = {"name": a["name"], "text": []}

    def handle_data(self, data):
        if self.current_option is not None:
            self.current_option["text"].append(data)
        if self.current_textarea is not None:
            self.current_textarea["text"].append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if not self.in_target:
            return
        if tag == "option" and self.current_option is not None and self.current_select is not None:
            value = self.current_option["value"]
            if value is None:
                value = "".join(self.current_option["text"]).strip()
            self.current_select["options"].append((value, self.current_option["selected"]))
            self.current_option = None
        elif tag == "select" and self.current_select is not None:
            options = self.current_select["options"]
            selected = [v for v, s in options if s]
            if not selected and options:
                selected = [options[0][0]]
            if not self.current_select["multiple"] and selected:
                selected = selected[:1]
            for value in selected:
                self.controls.append((self.current_select["name"], value))
            self.current_select = None
        elif tag == "textarea" and self.current_textarea is not None:
            self.controls.append((self.current_textarea["name"], "".join(self.current_textarea["text"])))
            self.current_textarea = None
        elif tag == "form":
            self.depth -= 1
            if self.depth <= 0:
                self.in_target = False
                self.depth = 0


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def bounded_request(session: requests.Session, method: str, url: str, data=None) -> dict:
    try:
        kwargs = {
            "timeout": 25,
            "stream": True,
            "allow_redirects": True,
            "headers": {"Referer": LIST_URL},
        }
        if method == "post":
            kwargs["data"] = data
            kwargs["headers"]["Origin"] = "https://www.eum.go.kr"
            r = session.post(url, **kwargs)
        else:
            kwargs["params"] = data
            r = session.get(url, **kwargs)
        buf = bytearray()
        overflow = False
        try:
            for chunk in r.iter_content(65536):
                if not chunk:
                    continue
                if len(buf) + len(chunk) > MAX_BYTES:
                    overflow = True
                    break
                buf.extend(chunk)
        finally:
            r.close()
        return {
            "state": "HTTP_RESPONSE_CAPTURED" if not overflow else "TECHNICAL_REQUEST_UNKNOWN",
            "http": r.status_code,
            "final_url": str(r.url),
            "body": bytes(buf),
            "overflow": overflow,
            "error": "RESPONSE_SIZE_LIMIT_EXCEEDED" if overflow else None,
        }
    except requests.RequestException as exc:
        return {"state": "TECHNICAL_REQUEST_UNKNOWN", "http": None, "final_url": url, "body": b"", "overflow": False, "error": f"{type(exc).__name__}: {exc}"}


def decode(raw: bytes) -> tuple[str, str]:
    for enc in ("euc-kr", "utf-8", "cp949"):
        try:
            text = raw.decode(enc)
            if "고시정보" in text or "고시제목" in text:
                return text, enc
        except UnicodeDecodeError:
            pass
    return raw.decode("euc-kr", errors="ignore"), "euc-kr-ignore"


def main() -> None:
    print("=" * 60)
    print("EUM GOSI WARM-SESSION BROWSER FORM POSITIVE CONTROL - S169")
    print("=" * 60)
    print("Form payload guessing: DISABLED")
    print("UQQ700 target search: DISABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    results = []
    for c in CONTROLS:
        session = requests.Session()
        session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})

        pre = bounded_request(session, "get", LIST_URL)
        pre_text, pre_enc = decode(pre["body"])
        parser = BrowserFormParser()
        parser.feed(pre_text)

        form_ok = bool(parser.form) and pre["state"] == "HTTP_RESPONSE_CAPTURED" and pre["http"] == 200 and host(pre["final_url"]) == HOST
        action = urljoin(pre["final_url"], parser.form["action"] if parser.form else "")
        method = (parser.form or {}).get("method", "get")

        payload = [(k, v) for k, v in parser.controls if k != "zonenm"]
        payload.append(("zonenm", c["query"]))
        payload_names = [k for k, _ in payload]

        submitted = bounded_request(session, method, action, payload) if form_ok and method in {"get", "post"} else {
            "state": "TECHNICAL_REQUEST_UNKNOWN", "http": None, "final_url": action, "body": b"", "overflow": False, "error": "FORM_CONTRACT_NOT_QUALIFIED"
        }
        text, encoding = decode(submitted["body"])
        official = host(submitted["final_url"]) == HOST
        seq_ok = bool(re.search(r"gvGosiDet\.jsp[^\"']*seq\s*=\s*" + re.escape(c["expected_seq"]), text, re.I)) or c["expected_seq"] in text
        year, num = c["expected_notice"].split("-")
        notice_ok = bool(re.search(r"성남시\s*고시\s*제?\s*" + re.escape(year) + r"\s*[-－]\s*" + re.escape(num) + r"\s*호", text))
        query_echo = c["query"] in text
        qualified = form_ok and submitted["state"] == "HTTP_RESPONSE_CAPTURED" and submitted["http"] == 200 and official and seq_ok and notice_ok and query_echo
        state = "EUM_GOSI_WARM_SESSION_BROWSER_FORM_QUALIFIED" if qualified else ("TECHNICAL_REQUEST_UNKNOWN" if submitted["state"] == "TECHNICAL_REQUEST_UNKNOWN" else "EUM_GOSI_WARM_SESSION_BROWSER_FORM_NOT_RESOLVED")

        row = {
            "query": c["query"],
            "expected_seq": c["expected_seq"],
            "expected_notice": c["expected_notice"],
            "state": state,
            "preflight_http": pre["http"],
            "preflight_encoding": pre_enc,
            "form_ok": form_ok,
            "form_action": action,
            "form_method": method,
            "payload_control_count": len(payload),
            "payload_names": payload_names,
            "cookie_names": sorted(cookie.name for cookie in session.cookies),
            "submit_http": submitted["http"],
            "submit_encoding": encoding,
            "seq_ok": seq_ok,
            "notice_ok": notice_ok,
            "query_echo": query_echo,
            "final_url": submitted["final_url"],
            "error": submitted["error"],
        }
        results.append(row)
        print("QUERY:", c["query"], "| STATE:", state, "| PREFLIGHT:", pre["http"], "| METHOD:", method.upper(), "| CONTROLS:", len(payload), "| COOKIES:", row["cookie_names"], "| SUBMIT:", submitted["http"], "| SEQ_OK:", seq_ok, "| NOTICE_OK:", notice_ok, "| QUERY_ECHO:", query_echo)
        print("  PAYLOAD_NAMES:", payload_names)

    qualified_count = sum(1 for r in results if r["state"] == "EUM_GOSI_WARM_SESSION_BROWSER_FORM_QUALIFIED")
    technical = sum(1 for r in results if r["state"] == "TECHNICAL_REQUEST_UNKNOWN")
    unresolved = sum(1 for r in results if r["state"] == "EUM_GOSI_WARM_SESSION_BROWSER_FORM_NOT_RESOLVED")

    out = {
        "step": "STEP 17-21-C-16-8-T-65-S169",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "NATIONAL_LAND_USE_PORTAL",
        "search_endpoint": LIST_URL,
        "search_transport": "WARM_SESSION_HTML_FORM_SUCCESSFUL_CONTROLS_REPLAY",
        "results": results,
        "summary": {
            "positive_control_count": len(results),
            "warm_session_browser_form_qualified_count": qualified_count,
            "technical_unknown_count": technical,
            "positive_control_unresolved_count": unresolved,
            "semantic_state": "EUM_GOSI_SEARCH_CONTRACT_QUALIFIED" if qualified_count == len(CONTROLS) else "EUM_GOSI_SEARCH_CONTRACT_NOT_YET_QUALIFIED",
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "uqq700_target_search_executed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "positive control request exact": len(results) == len(CONTROLS),
        "preflight forms qualified": all(r["form_ok"] for r in results),
        "technical unknown zero": technical == 0,
        "UQQ700 target search disabled": not out["uqq700_target_search_executed"],
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "unsafe promotion leakage zero": not any(out[k] for k in ["site_positive_allowed", "site_negative_allowed", "runtime_registration_allowed"]),
        "final resolution unknown": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\nVALIDATION")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S169 EUM warm-session browser form positive control technical validation failed")


if __name__ == "__main__":
    main()
