import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getAdminDashboard } from "../services/adminService";
import { listModels } from "../services/modelService";

export function AdminDashboardPage() {
  const [dashboard, setDashboard] = useState(null);
  const [models, setModels] = useState([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  async function loadDashboard() {
    setIsLoading(true);
    setError("");
    try {
      const [dashboardData, modelData] = await Promise.all([
        getAdminDashboard(),
        listModels(),
      ]);
      setDashboard(dashboardData);
      setModels(modelData.models);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  if (isLoading) {
    return <LoadingState label="Loading administration overview..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={loadDashboard} />;
  }

  const modelCounts = {
    total: models.length,
    drafts: models.filter((model) => model.status === "DRAFT").length,
    training: models.filter((model) => model.status === "TRAINING").length,
    trained: models.filter((model) => model.status === "TRAINED").length,
    failed: models.filter((model) => model.status === "FAILED").length,
  };

  const metrics = [
    ["Pending approvals", dashboard.pending_developers, "text-amber-300"],
    ["Total models", modelCounts.total, "text-slate-100"],
    ["Draft models", modelCounts.drafts, "text-amber-300"],
    ["Training", modelCounts.training, "text-cyan-300"],
    ["Trained models", modelCounts.trained, "text-emerald-300"],
  ];

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-cyan-300">Administration</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Platform overview</h1>
          <p className="mt-3 text-sm text-slate-400">
            Manage approvals, create CSV models, and prepare trained models for testing.
          </p>
        </div>
        <Link className="rounded-md bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-300" to="/models/new">
          Create CSV model
        </Link>
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {metrics.map(([label, value, color]) => (
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5" key={label}>
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
            <p className={`mt-3 text-3xl font-semibold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <Link className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 transition hover:border-cyan-700 hover:bg-slate-900" to="/admin/approvals">
          <p className="text-sm font-semibold text-cyan-300">Step 1 · Approve users</p>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Review verified developer registrations and approve platform access.
          </p>
        </Link>
        <Link className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 transition hover:border-cyan-700 hover:bg-slate-900" to="/models/new">
          <p className="text-sm font-semibold text-cyan-300">Step 2 · Create a model</p>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Create a CSV classification model and define its purpose.
          </p>
        </Link>
        <Link className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 transition hover:border-cyan-700 hover:bg-slate-900" to="/admin/models">
          <p className="text-sm font-semibold text-cyan-300">Step 3 · Train and publish</p>
          <p className="mt-2 text-sm leading-6 text-slate-400">
            Upload data, train the model, review metrics, and make it available for testing.
          </p>
        </Link>
      </div>

      <div className="mt-8 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Model workflow</p>
            <h2 className="mt-2 text-xl font-semibold text-slate-100">Recent models</h2>
          </div>
          <Link className="text-sm text-cyan-300 hover:text-cyan-200" to="/admin/models">
            Manage all models
          </Link>
        </div>
        {models.length ? (
          <div className="mt-5 divide-y divide-slate-800">
            {models.slice(0, 5).map((model) => (
              <Link className="flex flex-wrap items-center justify-between gap-3 py-4 first:pt-0 last:pb-0" key={model.id} to={`/models/${model.id}`}>
                <div>
                  <p className="font-medium text-slate-100">{model.name}</p>
                  <p className="mt-1 text-xs text-slate-500">{model.owner_email}</p>
                </div>
                <span className="text-xs font-medium text-slate-400">{model.status}</span>
              </Link>
            ))}
          </div>
        ) : (
          <p className="mt-5 text-sm text-slate-500">No models have been created yet.</p>
        )}
      </div>
    </section>
  );
}
