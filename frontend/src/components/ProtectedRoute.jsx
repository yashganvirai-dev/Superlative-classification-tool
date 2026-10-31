import { Navigate, Outlet, useLocation } from "react-router-dom";

import { LoadingState } from "./LoadingState";
import { useAuth } from "../hooks/useAuth";

export function ProtectedRoute() {
  const { isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <LoadingState label="Restoring your session..." />;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
