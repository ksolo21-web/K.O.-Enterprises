# Home inspection — reproducible development branch

This product lives only on `home-inspection-development` of `ksolo21-web/K.O.-Enterprises`, under `ventures/home-inspection/`. No production launch, customer approval, live-model accuracy or external orchestration is implied.

## From a fresh checkout

```bash
# From repository root, on the home-inspection-development branch
cd ventures/home-inspection
python -m pip install -r requirements.txt
# Requires system FFmpeg and ffprobe; code is standard Python 3.12+
python -m scripts.generate_public_fixtures
python -m unittest discover -s tests -q
```

The fixture generator uses Pillow and FFmpeg to create **schematic, synthetic** photo/video test input. The generated PNG and MP4 files stay local and are deliberately **not included** in Git. Do not replace these with actual customers' photos, videos, addresses or reports in this public repository.

Run synthetic demonstrations only after generating fixtures:

```bash
python -m scripts.build_m2_specialist_demo
python -m scripts.build_m2_critic_demo
```

Synthetic demonstrations are scripted, not live vision-model results. The native-zoom, video-photo capture, specialist routing and Q02 review protocols are code and contract tests, not evidence of real-world detection accuracy. Reports remain draft-only until actual qualified inspector signoff and applicable privacy/security controls are implemented and validated.

## CI and governance

The source tree contains a **reference** workflow in `ventures/home-inspection/.github/workflows/validation.yml`. It is **not activated as a root GitHub workflow**. The parent repository's `PAUSE_AUTONOMY` remains in effect; no external/scheduled executions are authorized by committing source. Run checks locally until the owner explicitly approves activation.

## Test and version interpretation

The original v0.7 package had 104 passing tests locally. The existing branch's later deterministic benchmarking code added 10 cases; together these form 114 tests. Public synthetic fixture checks add 2 more. These checks are not independent qualified-inspector validation. They do not change customer-release status.

## Limitations and next work

- A live locally hosted writer vision model and genuinely separate reviewer runtime are not yet exercised.
- Model issue labels and output schema must map to independently reviewed taxonomy before benchmarking.
- Original human-labeled photos/videos and real inspector observations are needed, outside public GitHub, for accuracy measurement.
- The current report generator needs a specific long-report pagination audit to ensure findings are never silently dropped.
- Strict safe paths, evidence custody, frame timestamping, disclosure and human review remain required.
