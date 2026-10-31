import { Navigate, Route, Routes } from "react-router-dom";

import { AdminRoute } from "./components/AdminRoute";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppLayout } from "./layouts/AppLayout";
import { PublicLayout } from "./layouts/PublicLayout";
import { AdminApprovalsPage } from "./pages/AdminApprovalsPage";
import { AdminDashboardPage } from "./pages/AdminDashboardPage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { CreateModelPage } from "./pages/CreateModelPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DatasetPage } from "./pages/DatasetPage";
import { ModelDetailsPage } from "./pages/ModelDetailsPage";
import { ModelsPage } from "./pages/ModelsPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PredictionPage } from "./pages/PredictionPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ResendVerificationPage } from "./pages/ResendVerificationPage";
import { TrainingPage } from "./pages/TrainingPage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />

      <Route element={<PublicLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/resend-verification" element={<ResendVerificationPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/models" element={<ModelsPage />} />
          <Route path="/models/:modelId" element={<ModelDetailsPage />} />
          <Route path="/models/:modelId/dataset" element={<DatasetPage />} />
          <Route path="/models/:modelId/training" element={<TrainingPage />} />
          <Route path="/models/:modelId/prediction" element={<PredictionPage />} />
          <Route element={<AdminRoute />}>
            <Route path="/models/new" element={<CreateModelPage admin />} />
            <Route path="/admin" element={<AdminDashboardPage />} />
            <Route path="/admin/models" element={<ModelsPage admin />} />
            <Route path="/admin/models/new" element={<CreateModelPage admin />} />
            <Route path="/admin/approvals" element={<AdminApprovalsPage />} />
            <Route path="/admin/users" element={<AdminUsersPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
