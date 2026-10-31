import { Link, Outlet } from "react-router-dom";

export function PublicLayout() {
  return (
    <div className="min-h-screen bg-slate-950 px-4 py-6 text-slate-100 sm:px-6">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between border-b border-slate-800 pb-5">
        <Link className="text-sm font-semibold tracking-wide text-cyan-300" to="/login">
          SUPERLATIVE CLASSIFICATION
        </Link>
        <span className="text-xs uppercase tracking-[0.2em] text-slate-500">
          Foundation
        </span>
      </header>
      <main className="mx-auto w-full max-w-6xl py-12">
        <Outlet />
      </main>
    </div>
  );
}
