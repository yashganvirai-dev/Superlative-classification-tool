# Superlative Classification Frontend

React, Vite, JavaScript, Tailwind CSS, and React Router foundation.

Node.js 20 or newer is required.

## Local setup

```powershell
Copy-Item frontend/.env.example frontend/.env
Set-Location frontend
npm.cmd ci
npm.cmd run dev
```

`VITE_API_BASE_URL` defaults to `http://localhost:8000/api` and should point to the
Django API during local development.

The current auth foundation keeps access and refresh tokens in browser
`sessionStorage` for the active tab. Sign-out blacklists the refresh token, while
access tokens remain valid for their short configured lifetime. A deployment review
should decide whether to move refresh tokens to an HttpOnly cookie before
production exposure.

Super Admins create and train CSV models. Approved developers can view trained
models and test predictions; model creation, dataset upload, and training are
not available to developers.

The current routes are:

- `/login`
- `/register`
- `/verify-email`
- `/resend-verification`
- `/dashboard` (protected)
- `/admin` (Super Admin)
- `/admin/approvals` (Super Admin)
- `/admin/users` (Super Admin)
- `/admin/models` (Super Admin)
- `/models`
- `/models/new`
- `/models/:modelId/dataset`
- `/models/:modelId/training`
- `/models/:modelId/prediction`

Registration sends a verification link before a Super Admin can approve the
account. The developer dashboard is an authenticated foundation screen. Super Admin pages
cover real account counts, pending approvals, and user status. The developer workflow
also includes model, dataset, training, metrics, and prediction screens. Trained
models keep their dataset and target locked; the Training screen can safely
retrain an unchanged model. Prediction fields marked optional by the backend are
not required by the browser form. Image classification remains deferred. A
production static host must rewrite unknown
paths such as `/dashboard` to `index.html` so
BrowserRouter can resolve deep links.

On the Dataset screen, choose the target column and either let the app infer
classification vs. regression or select the task explicitly. The Training screen
compares the available algorithms for that task and displays the winning
algorithm with the task-appropriate metrics.
