import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function AdminRoute() {
  const { user } = useAuth();

  if (user?.role !== "SUPER_ADMIN") {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
