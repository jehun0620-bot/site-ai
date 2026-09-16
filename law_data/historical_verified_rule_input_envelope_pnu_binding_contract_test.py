"""Contract test for historical verified-envelope repair/PNU binding."""
from __future__ import annotations

from law_data.historical_verified_rule_input_envelope import (
    BOUNDARY_NAME,
    HistoricalVerifiedRuleInputEnvelope,
    seal_verified_historical_rule_input,
)

PNU = "1168010300100120000"
OTHER_PNU = "1168010300100130000"


def _repair(*, pnu=None):
    value = {
        "condition": "도시지역편입해제구역",
        "after": "TRUE",
        "new_confidence": "VERIFIED",
        "new_source": "HISTORICAL_SITE_EVENT",
    }
    if pnu is not None:
        value["pnu"] = pnu
    return value


def _input(repairs):
    return {
        "channel": "HISTORICAL_SITE_EVENT",
        "provenance": "HISTORICAL_SITE_EVENT",
        "repairs": repairs,
    }


def main() -> None:
    legacy = seal_verified_historical_rule_input(
        canonical_pnu=PNU,
        historical_rule_input=_input([_repair()]),
    )
    assert legacy.ready is True

    promotion = seal_verified_historical_rule_input(
        canonical_pnu=PNU,
        historical_rule_input=_input([_repair(pnu=PNU)]),
    )
    assert promotion.ready is True

    cross_pnu = seal_verified_historical_rule_input(
        canonical_pnu=PNU,
        historical_rule_input=_input([_repair(pnu=OTHER_PNU)]),
    )
    assert cross_pnu.ready is False
    assert cross_pnu.verified is False
    assert dict(cross_pnu.historical_rule_input) == {}

    mixed = seal_verified_historical_rule_input(
        canonical_pnu=PNU,
        historical_rule_input=_input([_repair(pnu=PNU), _repair()]),
    )
    assert mixed.ready is False
    assert mixed.verified is False

    forged = HistoricalVerifiedRuleInputEnvelope(
        boundary=BOUNDARY_NAME,
        canonical_pnu=PNU,
        historical_rule_input=_input([_repair(pnu=OTHER_PNU)]),
        verified=True,
    )
    assert forged.ready is False

    forged_mixed = HistoricalVerifiedRuleInputEnvelope(
        boundary=BOUNDARY_NAME,
        canonical_pnu=PNU,
        historical_rule_input=_input([_repair(pnu=PNU), _repair()]),
        verified=True,
    )
    assert forged_mixed.ready is False

    print("HISTORICAL_VERIFIED_RULE_INPUT_ENVELOPE_PNU_BINDING_CONTRACT_PASS")


if __name__ == "__main__":
    main()
