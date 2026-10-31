import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { deleteModel, getModel } from "../services/modelService";
import { useAuth } from "../hooks/useAuth";

function statusClass(status) {
  if (status === "TRAINED") return "border-emerald-800 text-emerald-300";
  if (status === "FAILED") return "border-red-800 text-red-300";
  if (status === "TRAINING") return "border-cyan-800 text-cyan-300";
  return "border-amber-800 text-amber-300";
}

export function ModelDetailsPage() {
  const { modelId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === "SUPER_ADMIN";
  const [model, setModel] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isDeleting, setIsDeleting] = useState(false);

  async function loadModel() {
    setIsLoading(true);
    setError("");
    try {
      const data = await getModel(modelId);
      setModel(data.model);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadModel();
  }, [modelId]);

  async function handleDelete() {
    if (!window.confirm("Delete this model and its stored dataset/artifact? This cannot be undone.")) {
      return;
    }
    setIsDeleting(true);
    setError("");
    try {
      await deleteModel(modelId);
      navigate("/models");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsDeleting(false);
    }
  }

  if (isLoading) {
    return <LoadingState label="Loading model..." />;
  }

  if (error && !model) {
    return <ErrorState message={error} onRetry={loadModel} />;
  }

  return (
    <section>
      <Link className="text-sm text-slate-400 hover:text-slate-200" to="/models">
        ← Back to models
      </Link>
      <div className="mt-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-cyan-300">CSV · {model.algorithm?.replaceAll("_", " ")}</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">{model.name}</h1>
          <p className="mt-3 text-sm text-slate-400">Model ID: {model.id}</p>
        </div>
        <span className={`rounded-full border px-3 py-1 text-xs font-medium ${statusClass(model.status)}`}>
          {model.status}
        </span>
      </div>

      {error ? <div className="mt-6"><ErrorState message={error} /></div> : null}

      <div className="mt-8 grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 md:col-span-2">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Description</p>
          <p className="mt-3 text-sm leading-6 text-slate-300">
            {model.description || "No description provided."}
          </p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Owner</p>
          <p className="mt-3 text-sm text-slate-300">{model.owner_email}</p>
          <p className="mt-3 text-xs text-slate-500">Dataset: {model.has_dataset ? "Uploaded" : "Not uploaded"}</p>
          <p className="mt-1 text-xs text-slate-500">Target: {model.target_column || "Not selected"}</p>
          <p className="mt-1 text-xs text-slate-500">Artifact: {model.has_artifact ? "Available" : "Not trained"}</p>
        </div>
      </div>

      <div className="mt-8 flex flex-wrap gap-3">
        {isAdmin ? (
          <>
            <Link className="rounded-md bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-300" to={`/models/${model.id}/dataset`}>
              Dataset
            </Link>
            <Link className="rounded-md border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:border-slate-500" to={`/models/${model.id}/training`}>
              Training
            </Link>
          </>
        ) : null}
        <Link className="rounded-md border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:border-slate-500" to={`/models/${model.id}/prediction`}>
          Test model
        </Link>
        {isAdmin && model.status !== "TRAINING" && model.status !== "VALIDATING" ? (
          <button
            className="rounded-md border border-red-800 px-4 py-2.5 text-sm text-red-300 hover:bg-red-950/30 disabled:opacity-50"
            disabled={isDeleting}
            onClick={handleDelete}
            type="button"
          >
            {isDeleting ? "Deleting..." : "Delete model"}
          </button>
        ) : null}
      </div>
    </section>
  );
}
