# Reports

`reports/generated/` and `reports/private/` are local-only and ignored. A report may be committed under `reports/public/` only after it is reviewed for secrets, personal data, unsupported claims, and publication authority.

Generate the default internal CEO report with:

```powershell
.\.venv\Scripts\python -m company_os --report-dir reports/generated report
```
