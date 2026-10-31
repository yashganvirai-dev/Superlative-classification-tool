import { useState } from "react";
import { Link } from "react-router-dom";

import { ErrorState } from "../components/ErrorState";
import { resendVerification } from "../services/authService";

export function ResendVerificationPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    setIsSubmitting(true);
    try {
      await resendVerification(email);
      setNotice("If the account is eligible, a verification email has been sent.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="mx-auto max-w-md">
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-8">
        <p className="text-sm font-medium text-cyan-300">Account verification</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Resend verification</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          Enter your email address and we will send a new verification link if the account is eligible.
        </p>
        <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <label className="text-sm text-slate-300" htmlFor="verification-email">
              Email
            </label>
            <input
              className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none transition focus:border-cyan-400"
              id="verification-email"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
              autoComplete="email"
            />
          </div>
          {error ? <ErrorState message={error} /> : null}
          {notice ? <p className="text-sm text-emerald-300" role="status">{notice}</p> : null}
          <button
            className="w-full rounded-md bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Sending..." : "Send verification email"}
          </button>
        </form>
        <Link className="mt-6 inline-block text-sm text-cyan-300 hover:text-cyan-200" to="/login">
          Return to sign in
        </Link>
      </div>
    </section>
  );
}
