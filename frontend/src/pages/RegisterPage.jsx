import { useState } from "react";
import { Link } from "react-router-dom";

import { ErrorState } from "../components/ErrorState";
import { register } from "../services/authService";

const initialForm = {
  name: "",
  email: "",
  password: "",
  password_confirm: "",
};

export function RegisterPage() {
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [verificationEmailSent, setVerificationEmailSent] = useState(null);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const data = await register(form);
      setVerificationEmailSent(
        typeof data.verification_email_sent === "boolean"
          ? data.verification_email_sent
          : null,
      );
      setIsSubmitted(true);
      setForm(initialForm);
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
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Request access</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          Create a developer account. A Super Admin must approve it before you can sign in.
        </p>
      </div>

      {isSubmitted ? (
        <div className="rounded-xl border border-emerald-900/70 bg-emerald-950/30 p-6" role="status">
          <h2 className="font-semibold text-emerald-200">Registration received</h2>
          <p className="mt-2 text-sm leading-6 text-emerald-100/80">
            {verificationEmailSent === true
              ? "Your account is pending email verification and administrator approval. Check your email to verify your address, then wait for approval."
              : verificationEmailSent === false
                ? "Your account was created, but the verification email could not be sent. Use the resend page after a short cooldown."
                : "If the registration details are eligible, the account will require email verification and administrator approval."}
          </p>
          <div className="mt-6 flex flex-wrap gap-4 text-sm">
            <Link className="text-cyan-300 hover:text-cyan-200" to="/login">
              Return to sign in
            </Link>
            <Link className="text-slate-400 hover:text-slate-200" to="/resend-verification">
              Resend verification email
            </Link>
          </div>
        </div>
      ) : (
        <form className="space-y-5 rounded-xl border border-slate-800 bg-slate-900/60 p-6" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="text-sm text-slate-300" htmlFor="name">
              Full name
            </label>
            <input
              className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none transition focus:border-cyan-400"
              id="name"
              name="name"
              onChange={updateField}
              required
              value={form.name}
              autoComplete="name"
            />
          </div>
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
              autoComplete="new-password"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm text-slate-300" htmlFor="password_confirm">
              Confirm password
            </label>
            <input
              className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none transition focus:border-cyan-400"
              id="password_confirm"
              name="password_confirm"
              onChange={updateField}
              required
              type="password"
              value={form.password_confirm}
              autoComplete="new-password"
            />
          </div>
          {error ? <ErrorState message={error} /> : null}
          <button
            className="w-full rounded-md bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Submitting..." : "Submit registration"}
          </button>
        </form>
      )}

      {!isSubmitted ? (
        <p className="mt-6 text-sm text-slate-500">
          Already approved? <Link className="text-cyan-300 hover:text-cyan-200" to="/login">Sign in</Link>
        </p>
      ) : null}
    </section>
  );
}
