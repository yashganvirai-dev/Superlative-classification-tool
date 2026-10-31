# Superlative Classification Platform

A CSV machine-learning platform: upload and validate a dataset, choose a target
and classification or regression task, compare algorithms, train the best
pipeline, review metrics, and generate predictions through a dynamic feature form.

## Repository layout

- `backend/` — Django REST API with a custom user model, developer registration
  and approval workflow, JWT authentication, CSV dataset validation, training,
  metrics, and prediction endpoints, plus PostgreSQL settings and environment
  templates.
- `frontend/` — React/Vite/Tailwind single-page app with protected
  authentication routing.
- `storage/` — filesystem boundary for datasets and trained model artifacts.
  Large files are not stored in PostgreSQL.

See [`backend/README.md`](backend/README.md) and
[`frontend/README.md`](frontend/README.md) for setup commands.

Developer registration and approval are implemented, along with the CSV model,
dataset, training, metrics, and prediction workflow. Image classification remains
intentionally deferred.

## CSV workflow

1. Register and verify the developer email.
2. Sign in after a Super Admin approves the account.
3. Create a CSV model.
4. Upload and validate a CSV dataset.
5. Select and validate the target column and task type.
6. Compare supported algorithms and train the best-performing pipeline.
7. Review classification or regression metrics and the confusion matrix when applicable.
8. Generate predictions through the dynamic feature form.

## Security

See [SECURITY.md](SECURITY.md) for the vulnerability reporting policy. CI runs
tests, Gitleaks scans repository history, CodeQL analyzes Python code, and
Dependabot monitors dependencies and Actions.