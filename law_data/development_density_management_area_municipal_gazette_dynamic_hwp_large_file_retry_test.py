# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S2
Bounded retry for the first unresolved dynamic-HWP row caused only by the
16 MiB download cap.

Safety:
- reuses T-34 state repair, signature routing, extraction, and legal semantics
- retries exactly one unresolved/next row
- raises only the per-file bounded download cap to 32 MiB
- at most 2 network requests (metadata + download)
- zero matches remain UNKNOWN, never FALSE
"""
from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_bounded_batch_search_test as t34


def main() -> None:
    t34.BATCH_SIZE = 1
    t34.MAX_REQUESTS = 2
    t34.hwp5.MAX_FILE_BYTES = 32 * 1024 * 1024
    t34.main()


if __name__ == "__main__":
    main()
