# Filesystem storage

Large dataset files and trained model artifacts are kept outside PostgreSQL.

The configured storage root contains these phase-specific directories:

- `datasets/` for uploaded CSV files
- `trained_models/` for persisted model pipelines
- `temporary/` for short-lived processing files

The application creates and manages the directories when the corresponding phase
is implemented. The paths are configured with `STORAGE_ROOT` in the backend
environment.
