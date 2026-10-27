# Native workflow validation — 27 October 2026

Reference structure inspected: `chirackd/COMPENG_4DK4_Lab_2`, commit
`0d8330cd779ded20859b10e619f573f8fb878314` (root run_exp1/run_exp2 PowerShell
scripts and separate exp3–exp6 folders). This refactor supplies per-part folders
and PowerShell scripts, while retaining one shared C implementation.

Verified in the current Linux execution environment with GCC 14.2 and actual
PowerShell 7.5.4 (official release archive verified against its SHA-256 list):

- `setup.ps1`: created a fresh `.venv`, installed pinned packages, compiled the
  simulator directly with GCC, and passed all 19 existing model checks.
- All 17 authored PowerShell scripts parse successfully.
- `build.ps1` and an individual root experiment script execute successfully.
- A script invoked from inside `exp6/` also resolves the root and accepts `-Time`.
- `run_all.ps1 -Quick`: 305 one-seed main replications, 36 sensitivity
  replications, all 14 PNG/PDF figures. This is explicitly a smoke run.
- `run_all.ps1`: 1,525 main replications and 180 sensitivity replications, all
  14 figures. Every run checks packet conservation and station completion totals.
- The full refactored workflow's 1,525 aggregate rows, 12,750 station rows, and
  180 sensitivity rows match the original reference data within CSV precision
  after sorting by configuration/seed. The C model and RNG have not changed.
- All six experiment directories contain CSVs, text output, and manifests with
  matching record counts (540, 540, 180, 100, 180, 525). Parts 1 and 2 deliberately
  share the same 540 fixed-backoff replications.
- Three new integration tests pass: compile/run from a path containing spaces,
  per-part export/routing and output isolation, and a missing-compiler diagnostic.
- Output directories containing spaces work through the real PowerShell scripts.
- PDF rendering uses Matplotlib's bundled fonts; the updated reference report
  retains the group names, all 14 figure captions, and native setup instructions.

No Windows VM is attached to this execution environment. Local PowerShell-on-
Linux tests do not establish actual Windows execution. The added GitHub Actions
workflow has a Windows job using Windows PowerShell, native MSYS2 UCRT64 GCC,
Python setup, the complete quick pipeline, integration tests, and PDF generation.
Its run result is separate from the local checks recorded here.

The archived reference experiment provenance remains historical. Updated wrapper
source hashes are recorded separately in `lab/results/provenance.json` under
`workflow_refactor`; the old hashes are retained rather than relabeling the new
runner as the exact program originally used on 26 October.
