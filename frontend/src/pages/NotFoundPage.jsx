import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 text-slate-100">
      <div className="text-center">
        <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">404</p>
        <h1 className="mt-3 text-2xl font-semibold">Page not found</h1>
        <Link className="mt-6 inline-block text-sm text-cyan-300 hover:text-cyan-200" to="/login">
          Return to sign in
        </Link>
      </div>
    </main>
  );
}
