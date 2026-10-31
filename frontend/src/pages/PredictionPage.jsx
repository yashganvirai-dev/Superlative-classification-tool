import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getPredictionSchema, predict } from "../services/predictionService";

export function PredictionPage() {
  const { modelId } = useParams();
  const [schema, setSchema] = useState(null);
  const [values, setValues] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isPredicting, setIsPredicting] = useState(false);

  useEffect(() => {
    let active = true;
    getPredictionSchema(modelId)
      .then((response) => {
        if (active) {
          setSchema(response);
          setValues(Object.fromEntries(response.features.map((feature) => [
            feature.name,
            "",
          ])));
        }
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [modelId]);

  function updateValue(name, value) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  function resetSampleValues() {
    if (!schema) return;
    setValues(Object.fromEntries(schema.features.map((feature) => [
      feature.name,
      schema.sample_values?.[feature.name] ?? "",
    ])));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setResult(null);
    setIsPredicting(true);
    try {
      setResult(await predict(modelId, values));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsPredicting(false);
    }
  }

  if (isLoading) {
    return <LoadingState label="Loading prediction form..." />;
  }

  return (
    <section>
      <Link className="text-sm text-slate-400 hover:text-slate-200" to={`/models/${modelId}`}>
        ← Back to model
      </Link>
      <div className="mt-6">
        <p className="text-sm font-medium text-cyan-300">Model testing</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Generate prediction</h1>
        <p className="mt-3 text-sm text-slate-400">Fields are generated from the trained model feature schema.</p>
      </div>

      {error ? <div className="mt-6"><ErrorState message={error} /></div> : null}

      {schema ? (
        <form className="mt-8 max-w-2xl space-y-5 rounded-xl border border-slate-800 bg-slate-900/60 p-6" onSubmit={handleSubmit}>
          {schema.features.map((feature) => (
            <div className="space-y-2" key={feature.name}>
              <label className="text-sm text-slate-300" htmlFor={`feature-${feature.name}`}>
                {feature.name} <span className="text-xs text-slate-500">({feature.type}{feature.required === false ? ", optional" : ""})</span>
              </label>
              {feature.type === "categorical" && feature.categories ? (
                <select
                  className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
                  id={`feature-${feature.name}`}
                  onChange={(event) => updateValue(feature.name, event.target.value)}
                  required={feature.required !== false}
                  value={values[feature.name] ?? ""}
                >
                  <option value="">Select a value</option>
                  {feature.categories.map((category) => <option key={String(category)} value={String(category)}>{String(category)}</option>)}
                </select>
              ) : (
                <input
                  className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
                  id={`feature-${feature.name}`}
                  onChange={(event) => updateValue(feature.name, event.target.value)}
                  required={feature.required !== false}
                  step="any"
                  type={feature.type === "numerical" ? "number" : "text"}
                  value={values[feature.name] ?? ""}
                />
              )}
            </div>
          ))}
          <div className="flex flex-wrap gap-3">
          <button
            className="rounded-md bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isPredicting}
            type="submit"
          >
            {isPredicting ? "Generating prediction..." : "Generate prediction"}
          </button>
          <button
            className="rounded-md border border-slate-700 px-4 py-2.5 text-sm font-medium text-slate-300 hover:bg-slate-800"
            type="button"
            onClick={resetSampleValues}
          >
            Use sample values
          </button>
          </div>
        </form>
      ) : null}

      {result ? (
        <div className="mt-8 max-w-2xl rounded-xl border border-emerald-900/70 bg-emerald-950/30 p-6" role="status">
          <p className="text-xs uppercase tracking-[0.16em] text-emerald-300/70">
            {result.predicted_value !== undefined && result.probability === null ? "Predicted value" : "Predicted class"}
          </p>
          <p className="mt-2 text-3xl font-semibold text-emerald-100">{String(result.predicted_value ?? result.predicted_class)}</p>
          {result.probability !== null ? (
            <p className="mt-3 text-sm text-emerald-200/80">Estimated probability: {(result.probability * 100).toFixed(1)}%</p>
          ) : (
            <p className="mt-3 text-sm text-emerald-200/80">Probability is not available for this model.</p>
          )}
          {Object.keys(result.probabilities || {}).length ? (
            <div className="mt-5 space-y-2">
              {Object.entries(result.probabilities).map(([label, probability]) => (
                <div className="flex items-center justify-between text-sm text-emerald-100/80" key={label}>
                  <span>{label}</span><span>{(probability * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
