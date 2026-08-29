# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S3
50-row accelerated runner for the validated T-34 signature-routed HWP search.

This wrapper does not change parser routing, extraction, state schema, candidate
semantics, or legal safety rules. It only increases the bounded traversal to
50 rows / 100 requests. Requests remain sequential.
"""
from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_bounded_batch_search_test as t34


def main() -> None:
    t34.BATCH_SIZE = 50
    t34.MAX_REQUESTS = 100
    t34.main()


if __name__ == "__main__":
    main()
