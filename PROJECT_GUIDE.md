# Superlative Classification — Complete Project Guide

> **Project location:** `D:\projects\superlative-classification`
> **Remote:** `https://github.com/rutujbarsagade/superlative-classification.git`
> **Current commit:** `212c6a9` — working tree clean
> **Last verified:** all 68 backend tests pass, backend + frontend dev servers running

This guide explains **what** the project does, **what each part is**, **how it is implemented**, **why it was built that way**, **how to access the database**, and **how to run everything** — end to end.

---

## Table of contents

1. [Project overview](#1-project-overview)
2. [Repository layout](#2-repository-layout)
3. [Technology stack](#3-technology-stack)
4. [How the two halves talk to each other](#4-how-the-two-halves-talk-to-each-other)
5. [Backend module guide](#5-backend-module-guide)
6. [The machine-learning CSV pipeline](#6-the-machine-learning-csv-pipeline)
7. [Frontend module guide](#7-frontend-module-guide)
8. [Database guide (PostgreSQL)](#8-database-guide-postgresql)
9. [How to run the project](#9-how-to-run-the-project)
10. [End-to-end workflow (with live API examples)](#10-end-to-end-workflow-with-live-api-examples)
11. [API reference](#11-api-reference)
12. [Tests and CI](#12-tests-and-ci)
13. [Security, quotas, and limits](#13-security-quotas-and-limits)
14. [Operations: storage cleanup command](#14-operations-storage-cleanup-command)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Project overview

**Superlative Classification** is a web platform that lets a user (called a **Developer**)
upload a **CSV dataset**, choose a **target column** and task, and train a
classification or regression model through a web browser. The platform compares
several algorithms for the selected task and saves the best pipeline. When training
finishes, the same user can enter new rows in a generated form and get class
predictions or a numeric prediction.

The platform is a **single-page web application** split into two parts:

| Part | Folder | What it is |
|---|---|---|
| Backend | `backend/` | Django + Django REST Framework API, PostgreSQL database, the ML pipeline |
| Frontend | `frontend/` | React single-page app (Vite build) that calls the backend API |

### The core workflow (one sentence per step)

1. A user registers as a Developer with name + email + password.
2. The backend sends an **email verification link**.
3. The user clicks the link (prints to the console in local development).
4. A **Super Admin** approves the account in the admin area.
5. The Developer logs in and **creates a “model”** (a record, e.g. “Iris classifier”).
6. The Developer **uploads a CSV** — the backend validates it and shows a preview + candidate target columns.
7. The Developer **selects the target column** (the column to predict).
8. The Developer chooses automatic task detection or selects classification/regression. Training compares the supported algorithms, evaluates them, and saves the best pipeline.
9. The Developer opens **Prediction**, gets a generated form (one field per feature), submits values, and sees the predicted class and probabilities or the predicted numeric value.

Two roles exist: **SUPER_ADMIN** (sees everything, manages accounts and all models) and
**DEVELOPER** (sees only their own models).

---

## 2. Repository layout

```
superlative-classification/
├── backend/                        # Django project (Python)
│   ├── manage.py                   # Django CLI entry point
│   ├── requirements.txt            # Python dependencies
│   ├── .env                        # LOCAL ONLY (git-ignored) — real secrets
│   ├── .env.example                # Template with every setting documented
│   ├── config/                     # Project-level configuration
│   │   ├── settings/               # base.py / development.py / test.py / production.py
│   │   ├── urls.py                 # Root URL routes (API + admin)
│   │   ├── api.py                  # Shared success/error response envelope
│   │   ├── middleware.py           # 413 upload-size middleware
│   │   ├── wsgi.py / asgi.py       # Server entry points
│   ├── apps/                       # Four Django "apps" (modules)
│   │   ├── accounts/               # Users, roles, registration, JWT, admin approvals
│   │   ├── models/                 # The model registry ("MLModel")
│   │   ├── datasets/               # CSV upload, validation, preview, target column
│   │   └── training/               # Training jobs, metrics, predictions
│   ├── ml/                         # Pure machine-learning code (no Django)
│   │   └── csv/                    # validation, preprocessing, trainer, evaluator, predictor
│   └── services/                   # Shared services (email_service.py)
├── frontend/                       # React single-page app
│   ├── index.html                  # HTML shell with <div id="root">
│   ├── vite.config.js              # Vite dev/prod config
│   ├── package.json                # React, React Router, Tailwind, Vite
│   └── src/
│       ├── main.jsx                # React bootstrap (router + auth provider)
│       ├── App.jsx                 # All routes
│       ├── services/               # apiClient + per-feature API clients
│       ├── hooks/useAuth.jsx       # Auth state (login/logout/session restore)
│       ├── layouts/                # PublicLayout, AppLayout (nav shell)
│       ├── components/             # ProtectedRoute, AdminRoute, Loading, Error
│       └── pages/                  # 16 pages (login, dashboard, model flow, admin)
├── storage/                        # Filesystem data (git-ignored except README)
│   ├── datasets/<model_id>/<uuid>.csv      # Uploaded datasets
│   ├── trained_models/<model_id>/model.joblib  # Trained pipeline artifacts
│   └── temporary/                  # Reserved for future use
├── .github/
│   ├── workflows/security-and-ci.yml   # CI: backend tests (Postgres), frontend, secret scan, CodeQL
│   └── dependabot.yml                  # Weekly dependency updates
├── README.md                       # Short project readme
├── SECURITY.md                     # Security policy
├── .gitignore                      # Ignores .env, storage/, node_modules, .venv, etc.
└── PROJECT_GUIDE.md                # This document
```

Key design point: **`storage/` and the database work together.** PostgreSQL stores
*metadata* (who owns what, the target column, metrics, SHA-256 hashes) while the raw
CSV files and serialized model binaries live on disk in `storage/`. This keeps large
files out of the database.

---

## 3. Technology stack

### Backend (`backend/requirements.txt`)

| Technology | Version | Why it is used |
|---|---|---|
| Python | 3.12 | Language runtime |
| Django | ≥ 5.1, < 6.0 | Web framework: ORM, migrations, admin, auth plumbing |
| Django REST Framework (DRF) | ≥ 3.15 | JSON API views, serializers, permissions, throttling |
| djangorestframework-simplejwt | ≥ 5.3 | JWT access/refresh tokens + token blacklist |
| django-cors-headers | ≥ 4.6 | Lets the React dev server (`:5173`) call the API (`:8000`) |
| psycopg (binary) | ≥ 3.2 | PostgreSQL driver — **the only database engine in the project** |
| python-dotenv | ≥ 1.0 | Loads `backend/.env` into the environment |
| numpy / pandas | 2.x | Data frames: loading, validating, analyzing CSVs |
| scikit-learn | ≥ 1.6 | `RandomForestClassifier`, preprocessing, train/test split, metrics |
| joblib | ≥ 1.4 | Saves/loads the trained pipeline to `model.joblib` |

### Frontend (`frontend/package.json`)

| Technology | Version | Why it is used |
|---|---|---|
| Node.js | ≥ 20 | Runtime for the build tool |
| React + react-dom | 18.3 | UI library (note: React **is** JavaScript — JSX compiles to plain JS) |
| react-router-dom | 7.x | Client-side routing (public, protected, admin areas) |
| Vite | 6.x | Dev server (`:5173`) + production bundler, Hot Module Replacement |
| Tailwind CSS | 3.4 | Utility-first styling (with PostCSS + Autoprefixer) |
| Fetch API | — | The app calls the API with native `fetch` (no axios dependency) |

### Infrastructure / quality

| Item | Detail |
|---|---|
| Database | PostgreSQL 16, local dev at `localhost:5432`, DB `superlative_classification` |
| CI | GitHub Actions — see [Tests and CI](#12-tests-and-ci) |
| Secret scanning | Gitleaks on every push; CodeQL security analysis (Python + JavaScript) |
| Dependency updates | Dependabot (weekly) |

---

## 4. How the two halves talk to each other

The frontend is a **single-page app**. The browser loads `frontend/` once; from then on
the page uses `fetch()` to call the backend JSON API and re-renders.

- Frontend base URL: `http://localhost:5173`
- API base URL: `http://localhost:8000/api` (configurable via `VITE_API_BASE_URL` in `frontend/.env`)
- Backend allows cross-origin requests from `http://localhost:5173` and `http://127.0.0.1:5173` (`CORS_ALLOWED_ORIGINS`).
- Every protected API request sends an `Authorization: Bearer <access-token>` header.
- All responses use a **uniform envelope**:

```json
// Success
{ "success": true,  "data": { ... } }

// Error
{ "success": false, "error": { "code": "...", "message": "...", "fields": { ... } } }
```

The envelope lives in `backend/config/api.py` (`success()` helper and the
`api_exception_handler()` that converts every DRF/Django exception into the error
shape above). The frontend's `apiClient.js` parses exactly this shape.

---

## 5. Backend module guide

### 5.1 Configuration — `backend/config/settings/`

The settings are split into four files that all build on **`base.py`**:

| File | Used when | Key behavior |
|---|---|---|
| `base.py` | Always (imported by the others) | Installed apps, middleware, PostgreSQL connection, JWT lifetimes, throttling, email, storage paths, upload limits, logging |
| `development.py` | `DJANGO_SETTINGS_MODULE=config.settings.development` (default) | `DEBUG=True`; refuses to start without a `SECRET_KEY` |
| `test.py` | Running tests (`manage.py test --settings=config.settings.test`) | Fast password hasher, in-memory email backend, throttle rates raised, **PostgreSQL test database** `test_superlative_classification` |
| `production.py` | Real deployments | Enforces 50+ char `SECRET_KEY`, HTTPS, SMTP email, no wildcard hosts/CORS, HSTS headers; hard-fails on unsafe config |

`base.py` reads **every** value from environment variables (or `backend/.env`) with
helper functions `env_bool`, `env_int`, `env_list`, `env_path`. This is why the
project runs identically on a developer laptop and in CI.

**Why this design:** no configuration switches in code; the environment decides. The
`.env` file is git-ignored, so secrets never enter the repository.

### 5.2 The `accounts` app — users, roles, email verification, approvals

**Model — `backend/apps/accounts/models.py`**

`User` is a custom user model (`AUTH_USER_MODEL = "accounts.User"`) with email as the
login identifier (`USERNAME_FIELD = "email"`). Fields and meaning:

| Field | Meaning |
|---|---|
| `name` | Display name |
| `email` | Unique login (stored lower-cased, case-insensitive unique constraint) |
| `role` | `SUPER_ADMIN` or `DEVELOPER` (renamed from CUSTOMER in migration `0003`, with a DB check constraint) |
| `approval_status` | `PENDING` → `APPROVED` / `REJECTED` (DB check constraint) |
| `is_active` | False until approved |
| `email_verified` | True after the user clicks the verification link |
| `verification_email_sent_at` | Timestamp used for resend cooldown |
| `is_staff` / `is_superuser` | Django admin access (Super Admin only) |
| `created_at` / `updated_at` | Audit timestamps |

The custom `UserManager.create_user()` defaults every new signup to
`DEVELOPER / PENDING / inactive / unverified` — a brand-new account **cannot** log in
until the full flow completes. `create_superuser()` enforces `SUPER_ADMIN / APPROVED /
active`.

**Why this design:** a developer account is only usable after three gates — email
verified, approved by a Super Admin, and activated. No approved account can be
silently created.

**Registration flow — `services.py`**

- `register_developer()` — creates the user inside a DB transaction; a unique-email race
  returns `RegistrationConflict`, which the view answers with a deliberately vague
  “eligible accounts …” message (prevents email enumeration). Then it sends the
  verification email and records `verification_email_sent_at`.
- Email tokens are created by `services/email_service.py` using Django's **signed
  datagrams** (`signing.dumps` with a fixed salt, compressed, `max_age` = 24 h). The
  token contains only `user_id` + `email` — it is a signed, time-limited URL, not a DB row.
- `verify_developer_email()` — `signing.loads` validates signature + expiry, then marks
  `email_verified = True`. Invalid/expired tokens raise errors, surfaced as 400s.
- `resend_verification_email()` — allows resend only for `PENDING`/`REJECTED` unverified
  accounts, with a **60-second cooldown** derived from `verification_email_sent_at`.
- `approve_developer()` / `reject_developer()` / `resend_approval_email()` — Super Admin
  actions; approval requires `email_verified == True`; approval sets `APPROVED` + active
  and emails the developer. All use `select_for_update()` so concurrent actions can't
  approve twice.

**Email — `backend/services/email_service.py`**

Two emails exist: verification and approval. In development the backend uses the
**console email backend**, so the emails (with their links) are printed to the
**backend terminal** — no SMTP needed locally.

**JWT auth — `authentication.py`, `permissions.py`, `views.py`**

- `LoginView` validates credentials with Django `authenticate()`, then (critical) checks
  `can_access_platform(user)` — the login is rejected unless the account is
  *active + verified + APPROVED*. On success it returns `access` + `refresh` JWT.
- `ApprovedJWTAuthentication` extends SimpleJWT: after decoding the token it re-checks
  `can_access_platform`, so a revoked/blocked account is rejected even with a valid token.
- `RefreshView` only refreshes tokens for accounts that still pass the same gate.
- `LogoutView` **blacklists** the refresh token (SimpleJWT `token_blacklist`), so one
  account's refresh token cannot be reused by another.
- Default DRF permission is `IsApprovedUser`; admin endpoints use `IsSuperAdmin`.

**Super Admin API — `admin_views.py`**

- `GET /api/admin/dashboard/` — aggregate counts (total, developers, pending, approved, rejected) via a single SQL aggregate.
- `GET /api/admin/users/?status=…` — list users, optionally filtered by approval status.
- `GET /api/admin/users/pending/` — pending developers.
- `POST /api/admin/users/<id>/approve/`, `…/reject/`, `…/resend-approval/` — the three lifecycle actions.

### 5.3 The `models` app — the model registry

**Model — `apps/models/models.py`**

`MLModel` records:

| Field | Meaning |
|---|---|
| `name`, `description` | Human labels |
| `owner` | FK → `accounts.User` (the creator; `on_delete=CASCADE`) |
| `model_type` | `CSV` (current phase) or `IMAGE` (reserved for the future) |
| `status` | Lifecycle machine: `DRAFT → VALIDATING → TRAINING → TRAINED` (or `FAILED`) |
| `artifact_reference` | Relative path to `model.joblib` once trained |
| `metadata` | JSON: trained-at, dataset fingerprint, feature schema, algorithm info |
| `created_at` / `updated_at` | Audit timestamps |

Indexes cover `(owner, status)` and `(model_type, status)` — the two common query paths.

**Why a "model" is just a record:** the expensive artifact lives on disk; the DB row is
a handle + state machine that tells the UI exactly what step the user can do next.

**Services — `apps/models/services.py`**

- `create_csv_model()` — enforces platform access, per-user model **count quota** (100),
  then creates a `DRAFT` CSV model in a transaction.
- `visible_models(user)` — Super Admin sees all models; a Developer sees only their own.
- `storage_usage()` / `ensure_model_capacity()` — walk a user's dataset + artifact files,
  sum their sizes, enforce the **500 MB quota** (with `exclude_references` so replacing a
  file doesn't double-count it).
- `delete_model_with_files()` — blocks deletion while `VALIDATING`/`TRAINING`, deletes the
  DB row, then unlinks the CSV + joblib artifacts (also `.joblib.tmp` / `.joblib.previous`)
  and removes the now-empty folder. Django signals (`signals.py`) repeat the file cleanup
  so a model deleted through any path (e.g. Admin) still cleans its files.
- Every path handling uses `_safe_storage_path()`, which **rejects absolute paths and
  path traversal** (`resolve()` must stay inside `STORAGE_ROOT`).

**Views — `apps/models/views.py`**

- `GET/POST /api/models/` — list or create.
- `GET/DELETE /api/models/<id>/` — detail or delete.
- Permission: `IsModelOwnerOrSuperAdmin` (object-level).

### 5.4 The `datasets` app — CSV upload, validation, preview, target

**Model — `apps/datasets/models.py`**

`Dataset` is a **OneToOne** with `MLModel` (one model ⇔ one dataset):

| Field | Meaning |
|---|---|
| `original_filename` | Display name of the uploaded file |
| `storage_path` | Relative path under `storage/datasets/<model_id>/<uuid>.csv` |
| `file_size`, `sha256`, `row_count`, `column_count` | Fingerprint + size, checked before training |
| `target_column` | The column to predict (empty until chosen) |
| `metadata` | JSON: per-column stats + preview rows |

**Upload flow — `apps/datasets/services.py`**

1. `upload_dataset()` locks the model row and only allows upload when the model is
   `DRAFT` or `FAILED`. It reserves a new relative path, checks the storage quota, and
   flips the model to `VALIDATING`.
2. `_copy_upload()` streams the file to disk in 1 MB chunks, computing **SHA-256 while
   copying**, and aborts over 10 MB (`MAX_DATASET_UPLOAD_BYTES`).
3. `_read_dataframe()` opens the CSV once **as text** to check: non-empty header, no
   blank/duplicate column names, every row has the same column count. Then pandas reads it.
4. `validate_dataframe()` (see [ML section](#6-the-machine-learning-csv-pipeline)) runs rules.
5. `build_metadata()` computes per-column stats + a 10-row preview + **target candidates**
   (classification candidates with 2–50 classes represented at least twice, plus
   complete numeric columns that could be regression targets).
6. The `Dataset` row is created/updated, the model returns to `DRAFT`.
7. On any failure the partial file is deleted and the model becomes `FAILED` (visible to
   the user; they may retry).

**Target selection — `select_target_column()`**

Locks the model, requires `DRAFT`/`FAILED`, re-reads the file, and runs
The selected task determines target validation: classification requires ≥ 2 classes,
every class ≥ 2 rows, and enough rows for both train and test splits; regression
requires a complete numeric target. Both tasks limit categorical features to 100
categories. The target **cannot be changed after training** — the API returns a clear
error, because the trained artifact is tied to that column.

**Preview API** returns the columns, first 10 rows, target candidates, and counts —
exactly what the Dataset page renders.

**Middleware — `backend/config/middleware.py`**

`DatasetRequestLimitMiddleware` intercepts `POST /api/models/<id>/dataset/` **before**
DRF parses the body and returns HTTP 413 if `Content-Length` exceeds the request limit.
This rejects oversized uploads without buffering them into memory.

### 5.5 The `training` app — training jobs, metrics, predictions

**Model — `apps/training/models.py`**

`TrainingJob` (one model → many jobs):

| Field | Meaning |
|---|---|
| `status` | `PENDING → RUNNING → COMPLETED / FAILED` |
| `progress` | 0–100 (reported to the UI) |
| `algorithm` | `RANDOM_FOREST` |
| `metrics` | JSON (accuracy, precision, recall, F1, confusion matrix) |
| `error_message` | Safe, user-facing failure text |
| `started_at` / `completed_at` | Timing |

**Training orchestration — `apps/training/services.py`**

`start_training()` is **synchronous** (one HTTP request = one training run — fine for the
10 MB / 100 k-row scope of this phase):

1. Guard checks: model is CSV, has a dataset, has a target column.
2. Locks the model row; state must be `DRAFT`/`FAILED`/`TRAINED`. If retraining a
   `TRAINED` model, it verifies the **dataset SHA-256 and target still match** what was
   trained on — otherwise it refuses (data changed).
3. Creates the job `RUNNING` (progress 10), sets model `TRAINING`.
4. Re-reads the CSV from disk and re-verifies its SHA-256 against the DB (the file
   could have changed between upload and training).
5. Runs `train_random_forest()` (progress 35 → 80).
6. Writes the pipeline to `model.joblib.tmp`, checks the storage quota, then performs a
   **crash-safe swap**: existing `model.joblib` → `model.joblib.previous`, then
   `model.joblib.tmp` → `model.joblib`. The DB is only updated to point at the new file
   afterwards. If anything fails mid-way, `_restore_previous_artifact()` puts the last
   known-good artifact back and the model returns to `TRAINED`; otherwise `FAILED`.
7. Stores metrics on the job and rich metadata (algorithm, features schema, class
   labels, preprocessing description, train/test sizes) on the model.

**Why the tmp/previous dance:** the DB row and the file on disk must never disagree.
Writing the new binary first, then flipping the DB reference (with a rollback path)
guarantees the model is never “trained” but pointing at a missing/corrupt file.

**Prediction — `apps/training/prediction.py`**

- `prediction_schema()` returns the feature list built at training time
  (`{name, type: numerical|categorical, required, categories}`) — the Prediction page
  renders a form from it without knowing the data in advance.
- `predict()` first re-validates state (model `TRAINED`, artifact hash present, dataset
  still matches the trained fingerprint), loads `model.joblib` with joblib, validates the
  submitted values against the schema (unknown keys rejected, missing required rejected,
  numbers must be finite, categories must be exactly the trained categories), then runs
  the pipeline and returns `predicted_class` + `probability` + per-class `probabilities`.

**Views** — `GET/POST /api/models/<id>/training/`, `GET /api/models/<id>/metrics/`,
`GET /api/models/<id>/prediction/schema/`, `POST /api/models/<id>/prediction/`. All
require `IsTrainingOwnerOrSuperAdmin`.

---

## 6. The machine-learning CSV pipeline

All ML code lives in **`backend/ml/csv/`** as pure functions (no Django imports), so it
is trivially testable and reusable.

### `validation.py` — is this CSV usable for classification?

- `validate_dataframe()`: non-empty, ≥ 2 rows, ≤ row/column limits, ≥ 2 columns,
  non-blank unique column names, no all-empty column, no non-finite numbers.
- `build_metadata()`: per-column `dtype`, missing count/%, unique count, minimum class
  frequency + JSON-safe preview + **target candidates**.
- `validate_target_column()`: target must exist, no missing values, 2–50 classes, every
  class present ≥ 2×, enough rows for a 80/20 split to represent every class, categorical
  features ≤ 100 categories.

**Why these rules:** Random Forest needs every class in both train and test splits;
`traint_test_split(..., stratify=target)` fails otherwise. The rules fail *early with a
clear message* instead of a confusing sklearn error.

### `preprocessing.py` — leakage-free feature engineering

- `identify_feature_types()` splits columns into numeric vs categorical.
- `build_preprocessor()` builds a scikit-learn `ColumnTransformer`:
  - **Numeric:** `SimpleImputer(strategy="constant", fill_value=0)` — missing numbers become 0.
  - **Categorical:** `SimpleImputer(constant="__MISSING__")` + `OneHotEncoder(handle_unknown="ignore")`.
  - The transformer is **fitted on the training split only** — this is the “no leakage” rule.
- `build_feature_schema()` records, per feature, the type, required/optional, and the
  exact categories seen — saved into model metadata and used later to build the
  prediction form and validate inputs.

### `trainer.py` — fit + evaluate + record

- Validates again (min 10 rows) and compares candidates using a reproducible 80/20
  train/test split. Classification compares Random Forest, Decision Tree, and Logistic
  Regression; regression compares Random Forest Regressor and Linear Regression. The
  best candidate is refit on the full dataset and saved. The returned metadata includes
  the candidate leaderboard and held-out metrics.

### `evaluator.py` — metrics

Classification reports `accuracy`, weighted `precision`, `recall`, `f1`, and the raw
`confusion_matrix`. Regression reports MAE, MSE, RMSE, and R². Metrics use the held-out
test split.

### `predictor.py` — inference

Runs `pipeline.predict()` and, when the pipeline supports it (Random Forest does),
`predict_proba()` to return per-class probabilities.

---

## 7. Frontend module guide

### Bootstrap — `src/main.jsx`

Mounts React into `<div id="root">` (from `index.html`), wrapped in
`<BrowserRouter>` and `<AuthProvider>`.

### Routing — `src/App.jsx`

| Area | Routes | Guard |
|---|---|---|
| Public | `/login`, `/register`, `/verify-email`, `/resend-verification` | none |
| Protected | `/dashboard`, `/models`, `/models/new`, `/models/:modelId`, `/models/:modelId/{dataset,training,prediction}` | `ProtectedRoute` |
| Admin | `/admin`, `/admin/models`, `/admin/models/new`, `/admin/approvals`, `/admin/users` | `ProtectedRoute` + `AdminRoute` |
| Fallback | `*` → `NotFoundPage` | — |

`ProtectedRoute` checks `useAuth().user`; `AdminRoute` additionally requires
`role === "SUPER_ADMIN"`. The same `ModelsPage`/`CreateModelPage` are reused for admin
with an `admin` prop.

### Auth state — `src/hooks/useAuth.jsx`

- Keeps `user` + `isLoading` in a React context.
- On first load, if a refresh token exists in `sessionStorage`, it calls
  `restoreSession()` (POST refresh → GET me) to resurrect the session.
- `login()` stores tokens and sets the user; `logout()` blacklists the refresh token
  server-side, then clears local state **even if the server call fails**.

### The API client — `src/services/apiClient.js`

This is the heart of frontend↔backend communication:

- Reads `VITE_API_BASE_URL` (default `http://localhost:8000/api`).
- Tokens live in `sessionStorage` under `superlative_classification_auth`.
- `apiRequest()` adds `Authorization: Bearer …` when `auth=true`, JSON-encodes bodies
  (but **not** `FormData` — file uploads pass through raw), and throws a typed
  `ApiError {code, message, fields}` from the backend envelope.
- **Automatic refresh:** on a 401 it calls `refreshAuthSession()` (single in-flight
  promise so concurrent requests share one refresh) and retries the original request
  once. If refresh also fails, tokens are cleared and the app shows the login page.
- On a 401 from `/auth/refresh/`, it broadcasts an `AUTH_EXPIRED_EVENT` that the auth
  provider listens for, forcing a clean sign-out.

### Feature services (`src/services/`)

| File | Backend endpoints it calls |
|---|---|
| `authService.js` | register, verify-email, resend-verification, login, refresh, logout, me |
| `modelService.js` | `/models/`, `/models/<id>/` |
| `datasetService.js` | `/models/<id>/dataset/`, `/models/<id>/dataset/target/` |
| `trainingService.js` | `/models/<id>/training/`, `/models/<id>/metrics/` |
| `predictionService.js` | `/models/<id>/prediction/schema/`, `/models/<id>/prediction/` |
| `adminService.js` | `/admin/dashboard/`, `/admin/users/`, `/admin/users/pending/`, approve/reject/resend |

### Pages and what each one does

| Page | Purpose |
|---|---|
| `LoginPage` | Email/password → login; redirects by role (admin → `/admin`) |
| `RegisterPage` | Name/email/password/confirm; validates confirmation client-side |
| `VerifyEmailPage` | Reads `?token=` from the URL, POSTs it, shows the result + “awaiting approval” state |
| `ResendVerificationPage` | Lets a user request a new verification email |
| `DashboardPage` | Developer overview: counts plus quick links into the model flow |
| `ModelsPage` | Lists models (own, or all when `admin`); shows status badge; link to create |
| `CreateModelPage` | Name + description form → creates a `DRAFT` CSV model |
| `ModelDetailsPage` | Model info + status + next-step cards into dataset → training → prediction; delete |
| `DatasetPage` | Upload CSV; then renders the preview table + target candidate chips; posts the target |
| `TrainingPage` | Starts training, polls `metrics`/`training`, shows progress + metric bars + confusion matrix |
| `PredictionPage` | Fetches the schema, renders a form (numbers/categorical selects), posts values, shows the predicted class + probabilities |
| `AdminDashboardPage` | Admin stats cards |
| `AdminApprovalsPage` | Pending developers list with Approve / Reject actions |
| `AdminUsersPage` | Full user list with status filter + resend-approval-email |
| `NotFoundPage` | 404 fallback |

### Layouts and components

- `PublicLayout` — centered card shell for login/register/verify pages.
- `AppLayout` — dark sidebar-lite nav (Dashboard/Models + admin links when allowed),
  user email, Sign out.
- `ProtectedRoute` / `AdminRoute` — route guards.
- `LoadingState` / `ErrorState` — shared loading spinner and error panel (both consume
  the `ApiError` shape).

### Why this frontend design

Small, focused services mapped 1:1 to API groups; token refresh centralized in one file;
routes mirror the backend workflow (model → dataset → training → prediction). React
components keep the pages declarative — the alternative (hand-built DOM updates) was
considered but rejected: routing, auth state, and re-rendering are exactly what the
framework already provides.

---

## 8. Database guide (PostgreSQL)

### 8.1 Connection details (local development)

| Setting | Value |
|---|---|
| Engine | PostgreSQL (the **only** database engine in the project) |
| Host / Port | `localhost` / `5432` |
| Database | `superlative_classification` |
| Test database | `test_superlative_classification` (created/destroyed by the test runner) |
| User | `postgres` |
| Password | the value of `POSTGRES_PASSWORD` in `backend/.env` (local default: `postgres` — local dev only) |

These values are read from environment variables with sane defaults in
`base.py` (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`,
`POSTGRES_PORT`, `POSTGRES_CONN_MAX_AGE`, `POSTGRES_CONNECT_TIMEOUT`).

### 8.2 Connect with psql

```powershell
# Password will be the same as POSTGRES_PASSWORD in backend\.env (dev default: postgres)
psql -h localhost -U postgres -d superlative_classification
```

Handy queries:

```sql
-- Who are the users and what state are they in?
SELECT id, email, name, role, approval_status, is_active, email_verified
FROM accounts_user
ORDER BY id;

-- All models with owner and status
SELECT m.id, m.name, u.email AS owner, m.model_type, m.status
FROM models_mlmodel m
JOIN accounts_user u ON u.id = m.owner_id
ORDER BY m.id;

-- Datasets
SELECT d.id, d.model_id, d.original_filename, d.row_count, d.column_count,
       d.target_column, d.sha256
FROM datasets_dataset d
ORDER BY d.id;

-- Training jobs
SELECT id, model_id, status, algorithm, progress, metrics, error_message
FROM training_trainingjob
ORDER BY created_at DESC
LIMIT 10;

-- JWT refresh tokens that are still active (blacklist table)
SELECT id, user_id, created_at, expires_at
FROM token_blacklist_outstandingtoken
WHERE token_blacklist_blacklistedtoken.id IS NULL
... -- (blacklist is a separate table; also fine: SELECT count(*) FROM token_blacklist_outstandingtoken;)
```

### 8.3 Full list of tables (created by migrations)

- Django built-ins: `django_migrations`, `django_content_type`, `django_admin_log`,
  `auth_permission`, `auth_group`, `auth_group_permissions`, `django_session`.
- App tables: `accounts_user` (+ `accounts_user_groups`, `accounts_user_user_permissions`),
  `models_mlmodel`, `datasets_dataset`, `training_trainingjob`.
- SimpleJWT: `token_blacklist_outstandingtoken`, `token_blacklist_blacklistedtoken`.

### 8.4 Django shell (Python, full ORM power)

```powershell
cd D:\projects\superlative-classification
.venv\Scripts\python.exe backend\manage.py shell
```

```python
from apps.accounts.models import User
from apps.models.models import MLModel
from apps.datasets.models import Dataset
from apps.training.models import TrainingJob

# Inspect
print(User.objects.count(), "users")
for u in User.objects.all():
    print(u.id, u.email, u.role, u.approval_status, "verified:", u.email_verified)

# Upgrade a specific developer account directly (careful — normally done via admin UI)
u = User.objects.get(email="someone@example.com")
u.approval_status = "APPROVED"
u.is_active = True
u.save()

# Clean model list
for m in MLModel.objects.all():
    print(m.id, m.name, m.status, "artifact:", m.artifact_reference)
```

### 8.5 Migrations workflow

```powershell
# Create a migration for model changes (auto-detects)
.venv\Scripts\python.exe backend\manage.py makemigrations

# Check that no pending model changes exist (CI runs this)
.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run

# Apply
.venv\Scripts\python.exe backend\manage.py migrate

# See which migrations applied
.venv\Scripts\python.exe backend\manage.py showmigrations
```

### 8.6 django-admin (browser)

- URL: `http://localhost:8000/admin` (log in with the Super Admin account).
- Browse users, ML models, datasets, training jobs, and the JWT blacklist.

---

## 9. How to run the project

### Prerequisites

- Python 3.12
- Node.js ≥ 20 (with npm)
- PostgreSQL 16 running locally on `localhost:5432`
- A database named `superlative_classification`

### Step 1 — create the database (once)

```powershell
# With psql on PATH (or via pgAdmin): create if it doesn't exist
psql -h localhost -U postgres -c "CREATE DATABASE superlative_classification;"
```

### Step 2 — backend

```powershell
cd D:\projects\superlative-classification

# Virtual environment (used in this session; already created)
python -m venv .venv

# Install dependencies
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# Local environment file
Copy-Item backend\.env.example backend\.env
#  → edit backend\.env: set SECRET_KEY and POSTGRES_PASSWORD (dev default: postgres)

# Apply migrations and create the admin account
$env:DJANGO_SETTINGS_MODULE = "config.settings.development"
.venv\Scripts\python.exe backend\manage.py migrate
.venv\Scripts\python.exe backend\manage.py createsuperuser   # admin superuser

# Run the API (prints to backend console: Django logs + verification emails)
.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000 --noreload
```

### Step 3 — frontend

```powershell
cd D:\projects\superlative-classification\frontend
npm install
# optional: Copy-Item .env.example .env  (VITE_API_BASE_URL, default http://localhost:8000/api)
npm run dev        # → http://localhost:5173
```

### Step 4 — use it

1. Open `http://localhost:5173` → **Register** a developer account.
2. Read the **verification link from the backend terminal** and open it (or paste the
   token into `/verify-email?token=…`).
3. Log in as the Super Admin (`http://localhost:8000/admin` or the frontend `/login`
   with admin credentials) → **Pending approvals** → approve the developer.
4. Sign in as the developer in the frontend → **Models → New model → upload a CSV →
   pick target → Train → Predict**.

> **Already-running state:** both dev servers were running when this guide was written
> (backend `127.0.0.1:8000`, frontend `:5173`). A CSV model (id 2) already exists with a
> trained Random Forest, so the prediction form is immediately demo-able.
>
> **Local accounts:** a Super Admin and at least one approved developer exist in this
> local database. Passwords are intentionally **not** written into this committed
> document — reset or create accounts with `createsuperuser` or the register flow if
> you lose them.

---

## 10. End-to-end workflow (with live API examples)

Using PowerShell `Invoke-RestMethod` against the running API. Adjust host/port as needed.

```powershell
$base = "http://127.0.0.1:8000/api"

# 1) Login as an approved developer
$login = Invoke-RestMethod -Method Post -Uri "$base/auth/login/" -ContentType "application/json" `
  -Body '{"email":"<developer-email>","password":"<password>"}'
$token = $login.data.access
$headers = @{ Authorization = "Bearer $token" }

# 2) Create a model
$model = Invoke-RestMethod -Method Post -Uri "$base/models/" -Headers $headers `
  -ContentType "application/json" -Body '{"name":"My classifier","description":"test"}'
$id = $model.data.model.id

# 3) Upload a CSV (multipart)
$form = @{ file = Get-Item "D:\path\to\data.csv" }
$up = Invoke-RestMethod -Method Post -Uri "$base/models/$id/dataset/" -Headers $headers -Form $form
$up.data.preview.target_candidates     # → candidate columns

# 4) Select the target column
$target = Invoke-RestMethod -Method Post -Uri "$base/models/$id/dataset/target/" -Headers $headers `
  -ContentType "application/json" -Body '{"target_column":"<candidate>"}'

# 5) Train
$job = Invoke-RestMethod -Method Post -Uri "$base/models/$id/training/" -Headers $headers
$metrics = Invoke-RestMethod -Method Get -Uri "$base/models/$id/metrics/" -Headers $headers

# 6) Prediction schema → form → predict
$schema = Invoke-RestMethod -Method Get -Uri "$base/models/$id/prediction/schema/" -Headers $headers
$features = @{}
foreach ($f in $schema.data.features) { $features[$f.name] = "..." }  # values from your data
$pred = Invoke-RestMethod -Method Post -Uri "$base/models/$id/prediction/" -Headers $headers `
  -ContentType "application/json" -Body ($features | ConvertTo-Json)
$pred.data   # { predicted_class, probability, probabilities, model_id, model_name }
```

The same calls, in order, are exactly what the UI performs on each page.

---

## 11. API reference

All endpoints are under `http://localhost:8000/api` except Django Admin (`/admin`).
Authenticated = `Authorization: Bearer <access>` + account must be **approved-active-verified**.

### Auth (`/api/auth/`)

| Method | Path | Body | Purpose |
|---|---|---|---|
| POST | `/auth/register/` | `{name, email, password, password_confirm}` | Submit developer registration (sends verification email) |
| POST | `/auth/verify-email/` | `{token}` | Verify the emailed token |
| POST | `/auth/resend-verification/` | `{email}` | Resend verification email (cooldown 60 s) |
| POST | `/auth/login/` | `{email, password}` | Login → `{user, access, refresh}` |
| POST | `/auth/refresh/` | `{refresh}` | New access token (single-flight on the frontend) |
| POST | `/auth/logout/` | `{refresh}` | Blacklist refresh token |
| GET | `/auth/me/` | — | Current user profile |

### Super Admin (`/api/admin/`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/admin/dashboard/` | Account statistics |
| GET | `/admin/users/?status=…` | List users (filter: PENDING/APPROVED/REJECTED) |
| GET | `/admin/users/pending/` | Pending developers |
| POST | `/admin/users/<id>/approve/` | Approve |
| POST | `/admin/users/<id>/resend-approval/` | Resend approval email |
| POST | `/admin/users/<id>/reject/` | Reject |

### Models (`/api/models/`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/models/` | List visible models |
| POST | `/models/` | Create CSV model `{name, description}` |
| GET | `/models/<id>/` | Model detail |
| DELETE | `/models/<id>/` | Delete model + its files |
| GET | `/models/<id>/dataset/` | Dataset metadata + preview + target candidates |
| POST | `/models/<id>/dataset/` | Upload CSV (multipart `file`) |
| POST | `/models/<id>/dataset/target/` | Select target `{target_column}` |
| GET | `/models/<id>/training/` | Latest training job |
| POST | `/models/<id>/training/` | Start training |
| GET | `/models/<id>/metrics/` | Latest completed metrics |
| GET | `/models/<id>/prediction/schema/` | Feature schema for the form |
| POST | `/models/<id>/prediction/` | Predict `{feature: value, …}` |

---

## 12. Tests and CI

### Run tests locally (PostgreSQL only)

```powershell
cd D:\projects\superlative-classification
.venv\Scripts\python.exe backend\manage.py test apps.accounts apps.models apps.datasets apps.training --settings=config.settings.test -v 1
# Creates the test_superlative_classification DB, runs 68 tests, destroys it.
```

The test settings use the in-memory email backend and a fast password hasher; throttle
rates are lifted so tests never trip the limiter.

### CI — `.github/workflows/security-and-ci.yml`

| Job | What it does |
|---|---|
| `backend-foundation` | Starts a **PostgreSQL 16 service container**, installs deps, runs `check`, `makemigrations --check --dry-run`, migrates, runs all 68 tests **on Postgres** |
| `frontend-foundation` | Node 20, `npm ci`, `npm run build`, `npm audit --audit-level=high` |
| `secret-scan` | Gitleaks over the full git history (fails on committed secrets) |
| `codeql` | GitHub security analysis for Python + JavaScript (`security-extended`) |

Dependabot files: `pip` ecosystem → `/backend`, `npm` → `/frontend`, `github-actions` → `/`.

---

## 13. Security, quotas, and limits

| Control | Where | Value / behavior |
|---|---|---|
| Password hashing | Django | PBKDF2; Django’s full validator set on registration |
| JWT | SimpleJWT | Access 15 min, refresh 1 day, `Bearer` scheme; refresh blacklisted on logout |
| Account gates | `can_access_platform` | Active + email-verified + APPROVED — checked **on every authenticated request** (custom auth class), on login, and on refresh |
| Rate limiting | DRF throttling | Anon 30/min, user 60/min (env-tunable) |
| Email enumeration | `register_developer` | Duplicate signup returns a generic 202 message |
| Upload size | middleware + service | Request ≤ 12 MB, file ≤ 10 MB, rows ≤ 100 000, columns ≤ 200 |
| Per-user quotas | `ensure_model_capacity` | ≤ 100 models, ≤ 500 MB artifacts |
| Path traversal | `_safe_storage_path` + `resolve_dataset_path` | Absolute paths and `..` escapes rejected everywhere |
| Integrity | SHA-256 | Dataset hash stored at upload; re-verified before training and prediction |
| Crash safety | training service | tmp/previous artifact swap + rollback |
| Production settings | `production.py` | Hard-fails unless HTTPS, SMTP, 50+ char secret, no wildcard hosts |

---

## 14. Operations: storage cleanup command

Over time replaced datasets/models can leave orphan files. A management command cleans
them (files not referenced by any DB row, older than a cutoff):

```powershell
# Dry-run: show what would be removed
.venv\Scripts\python.exe backend\manage.py cleanup_model_storage --dry-run --older-than-minutes 60

# Actually remove orphans
.venv\Scripts\python.exe backend\manage.py cleanup_model_storage --older-than-minutes 60
```

---

## 15. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Frontend opens but shows a blank page | Vite `host: true` was added (`vite.config.js`) for IPv6-only machines; run `npm run dev` again. Also ensure all page imports exist in `App.jsx`. |
| Login says “cannot log in” | Account not yet verified and/or not approved. Check `accounts_user` row: `email_verified`, `approval_status`, `is_active`. |
| No verification email arrives locally | `EMAIL_BACKEND` is console in dev → the link prints in the **backend terminal**. |
| API returns 413 on upload | File bigger than `MAX_DATASET_REQUEST_BYTES` (12 MB). |
| Training fails with a row/class error | The CSV doesn’t meet classification rules — read the `error_message` on the training job for the exact reason. |
| Port 8000 or 5173 already in use | `netstat -ano | findstr :8000` → `stop-process -Id <pid>` (or use `--port`). |
| Missing Django tables | Run `backend\manage.py migrate`. |
| Tests fail to create the test DB | The Postgres user needs CREATEDB rights: `ALTER USER postgres CREATEDB;` |
| CORS errors in the browser console | Frontend origin not in `CORS_ALLOWED_ORIGINS` (defaults: `http://localhost:5173`, `http://127.0.0.1:5173`). |
| “Model not found” for a developer | Developers can only see their own models; Super Admin sees all. |
| Prediction says “dataset changed after training” | The CSV was replaced after training. Upload the same data again (or create a new model) and retrain. |

---

*End of guide. Generated from the project at commit `212c6a9` — if the code evolves, this
document should be updated alongside it.*