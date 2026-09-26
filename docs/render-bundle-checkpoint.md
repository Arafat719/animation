# Phase 2 / 2.8 export bundle checkpoint

Date: 2026-09-16. **2.8 implementation complete.** Next bounded task:
**2.9 missing/corrupt media and insufficient-disk error handling**.

The new export_bundle helper integrates normalization, concatenation, optional
mixing/burn-in and SRT export, then creates a first-frame PNG and versioned JSON
manifest. See [usage and limitations](render-bundle.md).

Four new tests PASS (9.86 seconds):

- Two independent exports are byte-identical, including manifest and all files,
  with both subtitle burn-in enabled and disabled.
- Manifest input/output hashes and sizes match actual files, ordered source roles
  and settings are retained, output duration is within tolerance.
- Thumbnail RGB pixels exactly match the decoded first output frame.
- Existing destinations preserved, corrupt export publishes nothing and cleans
  temporary directories, minimal export and invalid option combinations checked.

Backend incremental formatter and all 17 existing API schema drift checks PASS.
The local render manifest is a separate file format with schema_version=1; it is
not claimed as a new API contract. No dependencies/UI/API/database/model changes.
No paid resource used. Same-toolchain reproducibility is tested; cross-version
encoder/font bit identity is not promised. Source files must remain available.

Full regression: **379 backend tests PASS**, three existing dependency warnings,
80.37 seconds. Command: `DISABLE_REAL_PIPE=1 timeout 180s .venv/bin/python -m pytest -q -o faulthandler_timeout=30`.
Approved local escalation used for established TestClient sandbox limitations.
No UI changed; frontend/browser suite was not repeated. **2.8 PASS** within the
local helper scope; full Phase 2 gate remains pending after 2.9.
