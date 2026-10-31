import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { listModels } from "../services/modelService";

function statusClass(status) {
  if (status === "TRAINED") return "text-emerald-300";
  if (status === "FAILED") return "text-red-300";
  if (status === "TRAINING") return "text-cyan-300";
  return "text-amber-300";
}

export function ModelsPage({ admin = false }) {
  const [models, setModels] = useState([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  async function loadModels() {
    setIsLoading(true);
    setError("");
    try {
      const data = await listModels();
      setModels(data.models);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadModels();
  }, []);

  if (isLoading) {
    return <LoadingState label="Loading models..." />;
  }

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-cyan-300">Model registry</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">
            {admin ? "Platform models" : "Your models"}
          </h1>
          <p className="mt-3 text-sm text-slate-400">
            {admin ? "Create and manage CSV classification models across the platform." : "Test available trained CSV classification models."}
          </p>
        </div>
        {admin ? <Link
          className="rounded-md bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300"
          to="/models/new"
        >
          Create model
        </Link> : null}
      </div>

      {error ? <div className="mt-6"><ErrorState message={error} onRetry={loadModels} /></div> : null}

      <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {models.length ? (
          models.map((model) => (
            <article className="rounded-xl border border-slate-800 bg-slate-900/60 p-5" key={model.id}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.16em] text-slate-500">CSV classification</p>
                  <h2 className="mt-2 text-lg font-semibold text-slate-100">{model.name}</h2>
                </div>
                <span className={`text-xs font-medium ${statusClass(model.status)}`}>
                  {model.status}
                </span>
              </div>
              <p className="mt-3 min-h-10 text-sm leading-6 text-slate-400">
                {model.description || "No description provided."}
              </p>
              <div className="mt-5 flex items-center justify-between border-t border-slate-800 pt-4 text-xs text-slate-500">
                <span>{admin ? model.owner_email : `Created ${new Date(model.created_at).toLocaleDateString()}`}</span>
                <Link className="text-cyan-300 hover:text-cyan-200" to={`/models/${model.id}`}>
                  Open
                </Link>
              </div>
            </article>
          ))
        ) : (
          <div className="rounded-xl border border-dashed border-slate-700 px-6 py-12 text-center md:col-span-2 xl:col-span-3">
            <h2 className="font-semibold text-slate-200">No models yet</h2>
            <p className="mt-2 text-sm text-slate-500">Create your first classification model to get started.</p>
          </div>
        )}
      </div>
    </section>
  );
}
