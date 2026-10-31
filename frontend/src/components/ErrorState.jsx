export function ErrorState({ message, onRetry }) {
  return (
    <div className="rounded-lg border border-red-900/70 bg-red-950/30 p-4 text-sm text-red-200" role="alert">
      <p>{message || "Something went wrong. Please try again."}</p>
      {onRetry ? (
        <button
          className="mt-3 rounded border border-red-700 px-3 py-1.5 text-xs font-medium transition hover:bg-red-900/40"
          type="button"
          onClick={onRetry}
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}
