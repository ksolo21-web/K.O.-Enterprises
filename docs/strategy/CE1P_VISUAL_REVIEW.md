# CE-1P protected visual review

On a private Linux graphical session, run the desktop as the dedicated reviewer
account. Use the root-owned room provisioned for the reviewer's dedicated group
as in the CE-1N cross-UID exercise (0550 directories, 0440 files). The OS group
grants read access. Supply the manifest SHA-256 received through the separate
handoff. Install Tk and the project PDF rendering and source-verification extras.

    PYTHONPATH=src python -m company_os.competitive_visual_review ROOM SHA256 PRIVATE_DIR review REVIEWER_ID KEY_ID

Use an existing mode-0700 output directory owned by the reviewer outside the
repository. Select a page or claim in the left column. Open a page at its native
resolution and scroll to inspect it. The claim view includes the dossier's
supporting and counter sources and buttons for the available issuer-original
pages. Sources without an attached issuer page require separate investigation.
Choose each finding, write the limitations and enter an overall summary. Edits
are held in memory until a complete unsigned receipt is saved. Closing the
window discards unexported edits. The CE-1O one-hour observation window applies.

Use the existing reviewer-controlled Ed25519 signing procedure over the CE-1O
domain and canonical receipt. The desktop takes a public key identifier only.
To verify and archive a signed envelope on the provisioned system, supply the
trusted current local critic ledger root and root-signed policy:

    PYTHONPATH=src python -m company_os.competitive_visual_review ROOM SHA256 PRIVATE_DIR archive LEDGER_ROOT POLICY_JSON SIGNED_ENVELOPE_JSON

Only CE-1O-validated receipts can be archived through this command. Output files
are created once with mode 0600. A successful archive reports HOLD. Screen
access depends on the private host and graphical session. Neither page display
nor a signed receipt establishes independent inspection. No approved private
host or operational reviewer session has been demonstrated here.
