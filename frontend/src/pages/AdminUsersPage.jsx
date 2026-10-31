import { useEffect, useState } from "react";

import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import {
  approveUser,
  getPendingUsers,
  getUsers,
  rejectUser,
  resendApprovalEmail,
} from "../services/adminService";

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
  }).format(new Date(value));
}

function statusClass(status) {
  if (status === "APPROVED") return "text-emerald-300";
  if (status === "REJECTED") return "text-red-300";
  return "text-amber-300";
}

export function AdminUsersPage({ pendingOnly = false }) {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [actionId, setActionId] = useState(null);

  async function loadUsers() {
    setIsLoading(true);
    setError("");
    try {
      const data = pendingOnly ? await getPendingUsers() : await getUsers();
      setUsers(data.users);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, [pendingOnly]);

  async function handleApproval(userId) {
    setActionId(userId);
    setNotice(null);
    setError("");
    try {
      const data = await approveUser(userId);
      setUsers((current) =>
        pendingOnly
          ? current.filter((user) => user.id !== userId)
          : current.map((user) => (user.id === userId ? data.user : user)),
      );
      setNotice({
        message: data.email_sent
          ? "Developer approved and approval email sent."
          : "Developer approved, but the approval email could not be sent.",
        warning: !data.email_sent,
      });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setActionId(null);
    }
  }

  async function handleApprovalEmailResend(userId) {
    setActionId(userId);
    setNotice(null);
    setError("");
    try {
      const data = await resendApprovalEmail(userId);
      setNotice({
        message: data.email_sent
          ? "Approval email resent."
          : "The approval email could not be sent.",
        warning: !data.email_sent,
      });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setActionId(null);
    }
  }

  async function handleRejection(userId) {
    if (!window.confirm("Reject this developer registration? This cannot be undone from this screen.")) {
      return;
    }
    setActionId(userId);
    setNotice(null);
    setError("");
    try {
      const data = await rejectUser(userId);
      setUsers((current) =>
        pendingOnly
          ? current.filter((user) => user.id !== userId)
          : current.map((user) => (user.id === userId ? data.user : user)),
      );
      setNotice({
        message: "Developer registration rejected.",
        warning: false,
      });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setActionId(null);
    }
  }

  if (isLoading) {
    return <LoadingState label={pendingOnly ? "Loading pending registrations..." : "Loading users..."} />;
  }

  return (
    <section>
      <div>
        <p className="text-sm font-medium text-cyan-300">Administration</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">
          {pendingOnly ? "Pending approvals" : "User management"}
        </h1>
        <p className="mt-3 text-sm text-slate-400">
          {pendingOnly
            ? "Review developer registrations before they can access the platform."
            : "View registered users and their current account status."}
        </p>
      </div>

      {error ? <div className="mt-6"><ErrorState message={error} onRetry={loadUsers} /></div> : null}
      {notice ? (
        <p
          className={`mt-6 rounded-md border px-4 py-3 text-sm ${
            notice.warning
              ? "border-amber-900/70 bg-amber-950/30 text-amber-200"
              : "border-emerald-900/70 bg-emerald-950/30 text-emerald-200"
          }`}
          role="status"
        >
          {notice.message}
        </p>
      ) : null}

      <div className="mt-8 overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/60">
        {users.length ? (
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b border-slate-800 text-xs uppercase tracking-[0.14em] text-slate-500">
              <tr>
                <th className="px-5 py-4 font-medium">User</th>
                <th className="px-5 py-4 font-medium">Role</th>
                <th className="px-5 py-4 font-medium">Status</th>
                <th className="px-5 py-4 font-medium">Email verification</th>
                <th className="px-5 py-4 font-medium">Registered</th>
                <th className="px-5 py-4 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {users.map((user) => (
                <tr key={user.id}>
                  <td className="px-5 py-4">
                    <p className="font-medium text-slate-100">{user.name}</p>
                    <p className="mt-1 text-xs text-slate-500">{user.email}</p>
                  </td>
                  <td className="px-5 py-4 text-slate-400">{user.role}</td>
                  <td className={`px-5 py-4 font-medium ${statusClass(user.approval_status)}`}>
                    {user.approval_status}
                  </td>
                  <td className={`px-5 py-4 ${user.email_verified ? "text-emerald-300" : "text-amber-300"}`}>
                    {user.email_verified ? "Verified" : "Not verified"}
                  </td>
                  <td className="px-5 py-4 text-slate-400">{formatDate(user.created_at)}</td>
                  <td className="px-5 py-4 text-right">
                    {user.approval_status === "PENDING" ? (
                      <div className="flex justify-end gap-2">
                        <button
                          className="rounded border border-emerald-700 px-3 py-1.5 text-xs text-emerald-300 transition hover:bg-emerald-950/40 disabled:opacity-50"
                          disabled={!user.email_verified || actionId === user.id}
                          onClick={() => handleApproval(user.id)}
                          title={user.email_verified ? "Approve developer" : "Verify developer email first"}
                          type="button"
                        >
                          {actionId === user.id ? "Working..." : "Approve"}
                        </button>
                        <button
                          className="rounded border border-red-800 px-3 py-1.5 text-xs text-red-300 transition hover:bg-red-950/40 disabled:opacity-50"
                          disabled={actionId === user.id}
                          onClick={() => handleRejection(user.id)}
                          type="button"
                        >
                          Reject
                        </button>
                      </div>
                    ) : user.role === "DEVELOPER" && user.approval_status === "APPROVED" ? (
                      <button
                        className="rounded border border-slate-700 px-3 py-1.5 text-xs text-slate-300 transition hover:bg-slate-800 disabled:opacity-50"
                        disabled={actionId === user.id}
                        onClick={() => handleApprovalEmailResend(user.id)}
                        type="button"
                      >
                        {actionId === user.id ? "Working..." : "Resend email"}
                      </button>
                    ) : (
                      <span className="text-xs text-slate-600">No action</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="px-5 py-12 text-center text-sm text-slate-500">
            {pendingOnly ? "No pending developer registrations." : "No users found."}
          </div>
        )}
      </div>
    </section>
  );
}

