# -*- coding: utf-8 -*-
"""Offline/no-write contract for the credential-free MOLEG request descriptor."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qsl, urlsplit

from law_data.legal_source_public_request_descriptor import (
    ENDPOINT,
    LegalSourcePublicRequestDescriptor,
    build_legal_source_public_request_descriptor,
)


NATIONAL = {
    "target": "eflaw", "type": "JSON", "MST": "288857", "efYd": "20260918",
}
SEOUL = {"target": "ordin", "type": "JSON", "MST": "2149501"}
SYNTHETIC_SECRET = "SYNTHETIC_PRIVATE_VALUE_DO_NOT_ECHO"


def rejected(criteria: object, reason: str) -> None:
    try:
        build_legal_source_public_request_descriptor(criteria)  # type: ignore[arg-type]
    except ValueError as exc:
        assert SYNTHETIC_SECRET not in str(exc), reason
        assert SYNTHETIC_SECRET not in repr(exc), reason
    else:
        raise AssertionError("accepted invalid criteria: " + reason)


def with_field(criteria: dict[str, object], field: str, value: object) -> dict[str, object]:
    result = dict(criteria)
    result[field] = value
    return result


def main() -> None:
    # No HTTP, filesystem access, or actual credential is needed or permitted.
    with patch("builtins.open", side_effect=AssertionError("unexpected disk I/O")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("unexpected disk I/O")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("unexpected disk I/O")), patch(
        "socket.socket", side_effect=AssertionError("unexpected network I/O")
    ), patch("socket.create_connection", side_effect=AssertionError("unexpected network I/O")):
        national = build_legal_source_public_request_descriptor(NATIONAL)
        seoul = build_legal_source_public_request_descriptor(SEOUL)
        preserved = build_legal_source_public_request_descriptor(
            with_field(NATIONAL, "MST", "000288857")
        )

        assert isinstance(national, LegalSourcePublicRequestDescriptor)
        assert preserved.mst == "000288857"  # No reinterpretation of version IDs.
        assert national.public_parameters() == NATIONAL
        assert seoul.public_parameters() == SEOUL
        assert national.public_descriptor_url() == (
            ENDPOINT + "?target=eflaw&type=JSON&MST=288857&efYd=20260918"
        )
        assert seoul.public_descriptor_url() == ENDPOINT + "?target=ordin&type=JSON&MST=2149501"
        for obj, expected in ((national, NATIONAL), (seoul, SEOUL)):
            public_data = obj.to_dict()
            assert public_data["schema_version"] == "LEGAL_PUBLIC_REQUEST_V1"
            assert public_data["record_kind"] == "PUBLIC_REQUEST_DESCRIPTOR"
            assert public_data["source_system"] == "MOLEG_DRF"
            assert public_data["endpoint"] == ENDPOINT
            assert public_data["credential_included"] is False
            assert set(obj.public_parameters()) == set(expected)
            assert obj.public_parameters() == expected
            assert all("OC" not in k.upper() for k in public_data)
            assert SYNTHETIC_SECRET not in str(public_data)
            parsed = urlsplit(obj.public_descriptor_url())
            assert parsed.scheme == "https" and parsed.netloc == "www.law.go.kr"
            assert dict(parse_qsl(parsed.query, strict_parsing=True)) == expected
            assert "OC=" not in obj.public_descriptor_url()
            # Returned copies cannot mutate the immutable object.
            public_data["MST"] = "tampered"
            values = obj.public_parameters()
            values["MST"] = "tampered"
            assert obj.public_parameters() == expected
            try:
                obj.mst = "tampered"  # type: ignore[misc]
            except (FrozenInstanceError, AttributeError):
                pass
            else:
                raise AssertionError("descriptor is mutable")

        # Validate the public constructor as well, not only the factory.
        for kwargs in (
            {"target": "invalid", "mst": "288857"},
            {"target": "ordin", "mst": "2149501", "efyd": "20260713"},
            {"target": "eflaw", "mst": "288857", "efyd": "20260931"},
            {"target": "eflaw", "mst": "288857", "efyd": None},
            {"target": "eflaw", "mst": "288857", "efyd": SYNTHETIC_SECRET},
            {"target": "ordin", "mst": True},
        ):
            try:
                LegalSourcePublicRequestDescriptor(**kwargs)
            except ValueError as exc:
                assert SYNTHETIC_SECRET not in str(exc)
            else:
                raise AssertionError("constructor accepted invalid values")

        invalid = (
            (with_field(NATIONAL, "OC", SYNTHETIC_SECRET), "secret uppercase"),
            (with_field(NATIONAL, "oc", SYNTHETIC_SECRET), "secret lowercase"),
            (with_field(NATIONAL, "O%43", SYNTHETIC_SECRET), "secret encoded"),
            (with_field(NATIONAL, "O%2543", SYNTHETIC_SECRET), "secret double-encoded"),
            (with_field(NATIONAL, SYNTHETIC_SECRET, "value"), "secret key"),
            (with_field(NATIONAL, "unexpected", SYNTHETIC_SECRET), "unknown field"),
            (with_field(SEOUL, "efYd", "20260713"), "efYd forbidden for ordin"),
            (with_field(NATIONAL, "type", "xml"), "invalid format"),
            (with_field(NATIONAL, "MST", "288857&OC=" + SYNTHETIC_SECRET), "MST injection"),
            (with_field(NATIONAL, "MST", "２８８８５７"), "non-ASCII digits"),
            (with_field(NATIONAL, "MST", "0" * 21), "overlong MST"),
            (with_field(NATIONAL, "MST", 288857), "non-string MST"),
            (with_field(NATIONAL, "MST", True), "boolean MST"),
            (with_field(NATIONAL, "efYd", "20260931"), "impossible date"),
            (with_field(NATIONAL, "efYd", "20260229"), "non-leap day"),
            (with_field(NATIONAL, "efYd", "20260918&OC=" + SYNTHETIC_SECRET), "efYd injection"),
            (with_field(NATIONAL, "efYd", 20260918), "non-string date"),
            ({"target": "eflaw", "type": "JSON", "MST": "288857"}, "missing date"),
            ("https://www.law.go.kr/DRF/lawService.do?OC=" + SYNTHETIC_SECRET, "raw URL"),
            (None, "missing object"),
            ({1: SYNTHETIC_SECRET, **SEOUL}, "non-string field name"),
        )
        for data, label in invalid:
            rejected(data, label)

        # Input is never retained or reflected after successful construction.
        public_input = dict(NATIONAL)
        obj = build_legal_source_public_request_descriptor(public_input)
        public_input["MST"] = "123"
        assert obj.mst == "288857"
        assert SYNTHETIC_SECRET not in repr(obj)
        assert "oc" not in {k.casefold() for k in obj.to_dict()}

    print("LEGAL_SOURCE_PUBLIC_REQUEST_DESCRIPTOR_CONTRACT_PASS")


if __name__ == "__main__":
    main()
