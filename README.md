# Treasure Row

CSC 404 team project — continuing development of **The Vault**, a campus
marketplace web app for Hampton University students, inherited from CSC 405
and selected over CloudMart after the team's Iteration 1 evaluation.

## Team

| Name | Role |
|---|---|
| Donovan Griffin | Project Manager |
| Jonah Goodwine | Co-PM / Dev Team |
| Cameron Ridgley | Dev Team |
| Pilar Cummings | Dev Team |
| Chi Martin | Docs Team |
| Ricki Davis | Docs Team |
| Chase Jones | Docs Team |
| Noah Higgs | Docs Team (security/deployment) |

## Repo layout

```
app/             The Vault codebase (Flask backend + templates/static)
docs/            All formal deliverables, one folder per document
  evaluation/       Iteration 1 Evaluation Report
  project-plan/     Project Plan (scope, schedule, risk, staffing)
  requirements/     Requirements Document
  functional-spec/  Functional Specification
  design-spec/      Design Specification (kept separate from the above two)
  test-plan/        Test Plan
  meeting-minutes/  Meeting minutes, one file per meeting
  time-logs/        Team time logs
presentations/   Slide decks, one per iteration
```

## Branch strategy

- `main` — always a stable, working state of the app
- `develop` — integration branch; feature work merges here before `main`
- One branch per developer, cut from `develop`:
  `donovan`, `jonah`, `cameron`, `pilar`, `chase`, `ricki`, `chi`, `noah`

Work on your own branch, open a PR into `develop` when a piece is ready,
get one review before merging (per the QA process in the Project Plan).

## Running the app locally

See [`app/README.md`](app/README.md) for setup. Short version: create a
Python venv, `pip install -r requirements.txt`, set up a local Postgres
database, copy `.env.example` to `.env` and fill in **actual** values (the
example file is known to be out of date — that's an Iteration 2 fix), run
`backend/init_db.py`, then `python app.py`.

## Iteration 2 focus

- Fix the account/session ownership bug
- Reliable image upload/display (no hard dependency on live AWS S3)
- Rotate exposed AWS credentials; remove hardcoded secrets
- Two new features: buyer–seller messaging, storefront ratings & reviews
- All five formal documents updated to match the real app

Full detail lives in `docs/project-plan/`.
