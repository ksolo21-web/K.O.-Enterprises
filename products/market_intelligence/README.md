# Market Intelligence — Evidence-first pilot

This business has a shared company-wide document quality gate in src/company_os/document_quality.py, with tests in tests/test_document_quality.py and policy in docs/company/CLIENT_DOCUMENT_CRITIC_GATE.md.

This implementation is a zero-spend, internal structural validator only. Source URLs and reviewer identity are not authenticated. It never publishes documents, contacts customers or lifts PAUSE_AUTONOMY.

Client reports, invoices and personal or confidential information must not enter this public repository. Next: actual source validation, separate reviewer authentication, PDF page inspection and an owner-approved secure delivery process.
