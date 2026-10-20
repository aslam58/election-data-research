# Election Data Research

Python source from a study of Tamil Nadu voter-roll revisions and Assembly election outcomes. The wider research workspace also studies Puducherry; this snapshot contains the Tamil Nadu workflow.

## Workflow

`work/download.py` collects sources; `build_data.py` structures data; `analyze.py` and `extras.py` compute analyses; `final_figures.py` and `report.py` generate charts and a report; `package_sources.py` assembles provenance material.

`python work/run_all.py` runs analysis using an already-populated source cache. The runner does not download missing data. Raw electoral records, local source caches, spreadsheets, research reports, and generated figures are excluded from this repository. Downloading sources separately may use network access and depends on the original sites remaining available.

## Status and interpretation

Observational research, not evidence of causal effects. Treat changing voter-roll totals, turnout, and election results as different measures. Reproduce the source collection and inspect the code before relying on any result. Python 3 and the libraries imported by individual scripts are required; an independently validated clean-environment dependency lock has not yet been prepared.
