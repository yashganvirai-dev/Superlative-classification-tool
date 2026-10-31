import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getDataset, selectTargetColumn, uploadDataset } from "../services/datasetService";
import { getModel } from "../services/modelService";

export function DatasetPage() {
  const { modelId } = useParams();
  const [data, setData] = useState(null);
  const [modelStatus, setModelStatus] = useState("");
  const [file, setFile] = useState(null);
  const [expandExisting, setExpandExisting] = useState(false);
  const [targetColumn, setTargetColumn] = useState("");
  const [taskType, setTaskType] = useState("auto");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isSelectingTarget, setIsSelectingTarget] = useState(false);

  async function loadDataset() {
    setIsLoading(true);
    setError("");
    try {
      const response = await getDataset(modelId);
      setData(response);
      setModelStatus(response.model_status || "");
      setTargetColumn(response.dataset.target_column || "");
      setTaskType(response.preview.task_type || "auto");
    } catch (requestError) {
      if (requestError.status === 404) {
        setData(null);
        try {
          const modelResponse = await getModel(modelId);
          setModelStatus(modelResponse.model.status);
        } catch {
          setModelStatus("");
        }
      } else {
        setError(requestError.message);
      }
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadDataset();
  }, [modelId]);

  async function handleUpload(event) {
    event.preventDefault();
    if (!file) {
      setError("Choose a CSV file first.");
      return;
    }
    setError("");
    setNotice("");
    setIsUploading(true);
    try {
      const response = await uploadDataset(modelId, file, expandExisting);
      setData(response);
      setModelStatus(response.model_status || "DRAFT");
      setTargetColumn(expandExisting ? (response.dataset.target_column || "") : "");
      setTaskType(response.preview.task_type || "auto");
      setFile(null);
      setNotice(expandExisting ? "Dataset expanded and validated." : "Dataset uploaded and validated.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleTargetSubmit(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    setIsSelectingTarget(true);
    try {
      const response = await selectTargetColumn(modelId, targetColumn, taskType);
      setData((current) => ({ ...current, dataset: response.dataset }));
      setNotice("Target column saved.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSelectingTarget(false);
    }
  }

  if (isLoading) {
    return <LoadingState label="Loading dataset..." />;
  }

  const canEdit = !modelStatus || ["DRAFT", "FAILED", "TRAINED"].includes(modelStatus);

  return (
    <section>
      <Link className="text-sm text-slate-400 hover:text-slate-200" to={`/models/${modelId}`}>
        ← Back to model
      </Link>
      <div className="mt-6">
        <p className="text-sm font-medium text-cyan-300">Model workflow</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Dataset</h1>
        <p className="mt-3 text-sm text-slate-400">Upload a UTF-8 CSV, choose the target, and select classification or regression.</p>
      </div>

      {error ? <div className="mt-6"><ErrorState message={error} /></div> : null}
      {notice ? <p className="mt-6 rounded-md border border-emerald-900/70 bg-emerald-950/30 px-4 py-3 text-sm text-emerald-200" role="status">{notice}</p> : null}

      {canEdit ? (
        <form className="mt-8 rounded-xl border border-slate-800 bg-slate-900/60 p-6" onSubmit={handleUpload}>
          <h2 className="font-semibold text-slate-100">{modelStatus === "TRAINED" ? (expandExisting ? "Expand training dataset" : "Replace training dataset") : "Upload CSV"}</h2>
          <p className="mt-2 text-sm text-slate-400">
            {modelStatus === "TRAINED"
              ? "Upload a new CSV to prepare this trained model for retraining. The existing dataset and artifact remain available until retraining succeeds."
              : "The server validates structure, row and column limits, and stores a generated filename."}
          </p>
          {modelStatus === "TRAINED" || expandExisting ? (
            <label className="mt-5 flex items-center gap-3 text-sm text-slate-300">
              <input
                checked={expandExisting}
                className="h-4 w-4 accent-cyan-400"
                onChange={(event) => setExpandExisting(event.target.checked)}
                type="checkbox"
              />
              Expand the existing dataset instead of replacing it
            </label>
          ) : null}
          <div className="mt-5 flex flex-wrap items-center gap-4">
            <input
              accept=".csv,text/csv"
              className="max-w-full text-sm text-slate-300 file:mr-4 file:rounded file:border-0 file:bg-slate-700 file:px-3 file:py-2 file:text-sm file:text-slate-100"
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              type="file"
            />
            <button
              className="rounded-md bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isUploading}
              type="submit"
            >
              {isUploading ? "Validating..." : "Upload and validate"}
            </button>
          </div>
        </form>
      ) : (
        <div className="mt-8 rounded-xl border border-amber-900/70 bg-amber-950/20 p-5 text-sm text-amber-200">
          Dataset replacement is available while this model is draft, failed, or trained.
        </div>
      )}

      {data ? (
        <>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Rows</p>
              <p className="mt-2 text-2xl font-semibold">{data.preview.row_count}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Columns</p>
              <p className="mt-2 text-2xl font-semibold">{data.preview.column_count}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">File</p>
              <p className="mt-2 truncate text-sm text-slate-200" title={data.dataset.original_filename}>{data.dataset.original_filename}</p>
            </div>
          </div>

          {canEdit ? (
            <>
            <form className="mt-6 flex flex-wrap items-end gap-4 rounded-xl border border-slate-800 bg-slate-900/60 p-6" onSubmit={handleTargetSubmit}>
            <div className="min-w-56 flex-1 space-y-2">
              <label className="text-sm text-slate-300" htmlFor="target-column">Target column</label>
              <select
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
                id="target-column"
                onChange={(event) => setTargetColumn(event.target.value)}
                required
                value={targetColumn}
              >
                <option value="">Select a target</option>
                {data.preview.target_candidates.map((column) => <option key={column} value={column}>{column}</option>)}
              </select>
            </div>
            <div className="min-w-56 flex-1 space-y-2">
              <label className="text-sm text-slate-300" htmlFor="task-type">Task type</label>
              <select
                className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
                id="task-type"
                onChange={(event) => setTaskType(event.target.value)}
                value={taskType}
              >
                <option value="auto">Detect automatically</option>
                <option value="classification">Classification</option>
                <option value="regression">Regression</option>
              </select>
              <p className="text-xs text-slate-500">Automatic detection is based on the selected target. Choose explicitly when the target is numeric but represents classes or a value to predict.</p>
            </div>
            <button
              className="rounded-md border border-slate-700 px-4 py-2.5 text-sm text-slate-300 hover:border-slate-500 disabled:opacity-50"
              disabled={isSelectingTarget}
              type="submit"
            >
              {isSelectingTarget ? "Saving..." : "Save target"}
            </button>
            </form>
            {modelStatus === "TRAINED" || targetColumn ? (
              <Link className="mt-4 inline-block rounded-md bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-300" to={`/models/${modelId}/training`}>
                Go to Training and retrain
              </Link>
            ) : null}
            </>
          ) : null}

          <div className="mt-8 overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead className="border-b border-slate-800 text-xs uppercase tracking-[0.14em] text-slate-500">
                <tr>
                  {data.preview.columns.map((column) => <th className="px-4 py-3 font-medium" key={column.name}>{column.name}</th>)}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {data.preview.preview.map((row, index) => (
                  <tr key={index}>
                    {data.preview.columns.map((column) => <td className="px-4 py-3 text-slate-300" key={column.name}>{String(row[column.name] ?? "")}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="mt-8 rounded-xl border border-dashed border-slate-700 px-6 py-12 text-center text-sm text-slate-500">
          No dataset uploaded yet.
        </div>
      )}
    </section>
  );
}
