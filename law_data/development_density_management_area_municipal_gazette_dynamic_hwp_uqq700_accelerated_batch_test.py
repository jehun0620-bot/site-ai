# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S1
Accelerated runner for the validated T-34 signature-routed HWP search.

This does not change parsing, routing, legal semantics, state schema, or safety rules.
It only increases the bounded batch from 10 rows / 20 requests to
25 rows / 50 requests so the 1,325-row remainder can be traversed efficiently.
"""
from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_bounded_batch_search_test as t34


def main() -> None:
    t34.BATCH_SIZE = 25
    t34.MAX_REQUESTS = 50
    t34.main()


if __name__ == "__main__":
    main()
