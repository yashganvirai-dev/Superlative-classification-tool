# Superlative Classification Backend

Django and Django REST Foundation for the Superlative Classification platform.
Python 3.12 is recommended.

## Local setup

From the repository root:

```powershell
Copy-Item backend/.env.example backend/.env
```

Set `SECRET_KEY`, PostgreSQL connection values, and the development email settings
in `backend/.env`. PostgreSQL is the only database used by the application and its
tests.

Install dependencies and apply migrations:

```powershell
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
$env:DJANGO_SETTINGS_MODULE = "config.settings.development"
.venv\Scripts\python.exe backend\manage.py migrate
.venv\Scripts\python.exe backend\manage.py createsuperuser
```

For non-interactive bootstrap, provide the required name explicitly:

```powershell
$env:DJANGO_SUPERUSER_PASSWORD = "use-a-local-development-password"
.venv\Scripts\python.exe backend\manage.py createsuperuser --noinput --email admin@example.com --name "Platform Admin"
```

Run the development server:

```powershell
.venv\Scripts\python.exe backend\manage.py runserver
```

The WSGI and ASGI entry points fail closed to `config.settings.production` when
`DJANGO_SETTINGS_MODULE` is not set. Configure a production application server
and set the environment explicitly before deployment.

The API is served under `/api/`. The current foundation exposes:

- `POST /api/auth/register/`
- `POST /api/auth/verify-email/`
- `POST /api/auth/resend-verification/`
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`
- `POST /api/auth/logout/` (blacklists the supplied refresh token)
- `GET /api/admin/dashboard/`
- `GET /api/admin/users/`
- `GET /api/admin/users/pending/`
- `POST /api/admin/users/{id}/approve/`
- `POST /api/admin/users/{id}/reject/`
- `POST /api/admin/users/{id}/resend-approval/`
- `GET/POST /api/models/`
- `GET/DELETE /api/models/{id}/`
- `GET/POST /api/models/{id}/dataset/`
- `POST /api/models/{id}/dataset/target/`
- `GET/POST /api/models/{id}/training/`
- `GET /api/models/{id}/metrics/`
- `GET /api/models/{id}/prediction/schema/`
- `POST /api/models/{id}/prediction/`

All API responses use the `success`/`data` and `success`/`error` envelope.
Only active, email-verified users whose `approval_status` is `APPROVED` can
receive or use platform tokens. Registration requires email verification before
an administrator can approve the account. Super Admins create CSV models, upload
datasets, select targets, and start training. Approved developers can view
trained models and generate predictions, but cannot create, modify, or train
models. Precision, recall, and F1 use weighted averages for multiclass
classification.
CSV training supports both classification and regression. The Dataset screen
offers automatic task detection or an explicit task choice; training evaluates
the supported algorithms for that task and saves the best-performing pipeline.
Classification compares Random Forest, Decision Tree, and Logistic Regression.
Regression compares Random Forest Regressor and Linear Regression. Regression
metrics include MAE, MSE, RMSE, and R².
Authentication endpoints use DRF throttling with the default local-memory cache;
configure a shared cache or enforce equivalent limits at the gateway before
multi-process production deployment. Configure SMTP settings for real approval
email delivery; the local console backend is only a development default.
Approval state changes are committed even
when email delivery fails; the API reports `email_sent: false` and logs the
failure for operational follow-up. Verification resend requests are recipient-
throttled and duplicate registration responses do not disclose account existence.

Trained models are immutable with respect to their dataset and target. A trained
model can be retrained only when its dataset hash and target still match the saved
artifact; a failed retrain preserves the last known-good artifact. CSV validation
rejects non-finite values, unusable features, singleton target classes, and
high-cardinality categorical features. Oversized multipart requests are rejected
before parsing when a Content-Length is supplied. Features that had missing values during
training are marked optional in the prediction schema and use synchronized
imputation. Per-user model and storage quotas are configured through the
`MAX_USER_*` settings.

Generated storage is cleaned when a model or owner is deleted. The maintenance
command below removes old unreferenced generated files; use `--dry-run` first:

```powershell
.venv\Scripts\python.exe backend\manage.py cleanup_model_storage --dry-run
```

## Checks and tests

```powershell
.venv\Scripts\python.exe backend\manage.py check
.venv\Scripts\python.exe backend\manage.py test apps.accounts apps.models apps.datasets apps.training --settings=config.settings.test
```

Tests run against PostgreSQL, the same engine as the application, using the
dedicated `test_superlative_classification` database.

Image classification is intentionally deferred until the CSV workflow is reviewed
and accepted.
