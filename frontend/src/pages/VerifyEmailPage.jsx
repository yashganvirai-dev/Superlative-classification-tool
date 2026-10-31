import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { verifyEmail } from "../services/authService";

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState(token ? "loading" : "error");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setMessage("The verification link is missing its token.");
      return;
    }
    let active = true;
    verifyEmail(token)
      .then(() => {
        if (active) {
          setStatus("success");
          setMessage("Your email is verified. Your account is now awaiting administrator approval.");
        }
      })
      .catch((error) => {
        if (active) {
          setStatus("error");
          setMessage(error.message);
        }
      });
    return () => {
      active = false;
    };
  }, [token]);

  return (
    <section className="mx-auto max-w-md">
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-8">
        <p className="text-sm font-medium text-cyan-300">Account verification</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Verify your email</h1>
        {status === "loading" ? <LoadingState label="Verifying your email..." /> : null}
        {status === "success" ? (
          <div className="mt-6 rounded-md border border-emerald-900/70 bg-emerald-950/30 p-4 text-sm leading-6 text-emerald-200" role="status">
            {message}
          </div>
        ) : null}
        {status === "error" ? (
          <div className="mt-6">
            <ErrorState message={message} />
          </div>
        ) : null}
        <div className="mt-6 flex flex-wrap gap-4 text-sm">
          <Link className="text-cyan-300 hover:text-cyan-200" to="/login">
            Return to sign in
          </Link>
          <Link className="text-slate-400 hover:text-slate-200" to="/resend-verification">
            Resend verification email
          </Link>
        </div>
      </div>
    </section>
  );
}
