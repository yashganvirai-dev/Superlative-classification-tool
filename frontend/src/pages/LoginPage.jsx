import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { ErrorState } from "../components/ErrorState";
import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const destination = location.state?.from?.pathname || "/dashboard";

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      await login(form);
      navigate(destination, { replace: true });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-md">
      <div className="mb-8">
        <p className="text-sm font-medium text-cyan-300">Platform access</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Sign in</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          Use your approved account to access the classification workspace.
        </p>
      </div>

      <form className="space-y-5 rounded-xl border border-slate-800 bg-slate-900/60 p-6" onSubmit={handleSubmit}>
        <div className="space-y-2">
          <label className="text-sm text-slate-300" htmlFor="email">
            Email
          </label>
          <input
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none transition focus:border-cyan-400"
            id="email"
            name="email"
            onChange={updateField}
            required
            type="email"
            value={form.email}
            autoComplete="email"
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm text-slate-300" htmlFor="password">
            Password
          </label>
          <input
            className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none transition focus:border-cyan-400"
            id="password"
            name="password"
            onChange={updateField}
            required
            type="password"
            value={form.password}
            autoComplete="current-password"
          />
        </div>
        {error ? <ErrorState message={error} /> : null}
        <button
          className="w-full rounded-md bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Signing in..." : "Sign in"}
        </button>
      </form>

      <p className="mt-6 text-sm text-slate-500">
        Need an account? <Link className="text-cyan-300 hover:text-cyan-200" to="/register">Register</Link>
      </p>
    </section>
  );
}
