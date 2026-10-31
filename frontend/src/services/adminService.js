import { apiRequest } from "./apiClient";

export function getAdminDashboard() {
  return apiRequest("/admin/dashboard/");
}

export function getUsers(status) {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiRequest(`/admin/users/${query}`);
}

export function getPendingUsers() {
  return apiRequest("/admin/users/pending/");
}

export function approveUser(userId) {
  return apiRequest(`/admin/users/${userId}/approve/`, { method: "POST" });
}

export function resendApprovalEmail(userId) {
  return apiRequest(`/admin/users/${userId}/resend-approval/`, { method: "POST" });
}

export function rejectUser(userId) {
  return apiRequest(`/admin/users/${userId}/reject/`, { method: "POST" });
}
