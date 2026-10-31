import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ErrorState } from "../components/ErrorState";
import { createModel } from "../services/modelService";

export function CreateModelPage({ admin = false }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", description: "", algorithm: "AUTO" });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const data = await createModel({ ...form, model_type: "CSV" });
      navigate(`/models/${data.model.id}`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-2xl">
      <Link className="text-sm text-slate-400 hover:text-slate-200" to={admin ? "/admin/models" : "/models"}>
        ← Back to models
      </Link>
      <div className="mt-6">
        <p className="text-sm font-medium text-cyan-300">Model registry</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Create a model</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          Choose an algorithm for your CSV model. Image classification is not available yet.
        </p>
      </div>

      <form className="mt-8 space-y-5 rounded-xl border border-slate-800 bg-slate-900/60 p-6" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <label className="text-sm text-slate-300" htmlFor="model-name">
            Model name
          </label>
          <input
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none transition focus:border-cyan-400"
            key="manual-name"
            id="model-name"
            name="name"
            onChange={updateField}
            required
            value={form.name}
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm text-slate-300" htmlFor="model-description">
            Description
          </label>
          <textarea
            className="min-h-28 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none transition focus:border-cyan-400"
            id="model-description"
            name="description"
            onChange={updateField}
            value={form.description}
          />
        </div>
        <div className="rounded-md border border-slate-800 bg-slate-950/50 p-4">
          <p className="text-sm font-medium text-slate-200">Automatic model selection</p>
          <p className="mt-1 text-xs text-slate-500">The task type and best-performing algorithm will be selected from the dataset.</p>
        </div>
        {error ? <ErrorState message={error} /> : null}
        <button
          className="rounded-md bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Creating..." : "Create model"}
        </button>
      </form>
    </section>
  );
}
