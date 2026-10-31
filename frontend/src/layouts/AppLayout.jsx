import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

const navigationClass = ({ isActive }) =>
  `rounded-md px-3 py-2 text-sm transition ${
    isActive
      ? "bg-cyan-400/10 text-cyan-300"
      : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
  }`;

export function AppLayout() {
  const { logout, user } = useAuth();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-900/60">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <div>
            <p className="text-sm font-semibold tracking-wide text-cyan-300">
              SUPERLATIVE CLASSIFICATION
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {user?.role === "SUPER_ADMIN" ? "Administration" : "Developer workspace"}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <span className="hidden text-sm text-slate-400 sm:inline">{user?.email}</span>
            <button
              className="rounded-md border border-slate-700 px-3 py-2 text-sm text-slate-300 transition hover:border-slate-500 hover:text-white"
              type="button"
              onClick={() => logout()}
            >
              Sign out
            </button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-7xl gap-1 px-4 pb-3 sm:px-6 lg:px-8" aria-label="Primary navigation">
          <NavLink
            className={navigationClass}
            end
            to={user?.role === "SUPER_ADMIN" ? "/admin" : "/dashboard"}
          >
            {user?.role === "SUPER_ADMIN" ? "Overview" : "Dashboard"}
          </NavLink>
          <NavLink
            className={navigationClass}
            to={user?.role === "SUPER_ADMIN" ? "/admin/models" : "/models"}
          >
            Models
          </NavLink>
          {user?.role === "SUPER_ADMIN" ? (
            <>
              <NavLink className={navigationClass} to="/admin/approvals">
                Pending approvals
              </NavLink>
              <NavLink className={navigationClass} to="/admin/users">
                Users
              </NavLink>
            </>
          ) : null}
        </nav>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}

