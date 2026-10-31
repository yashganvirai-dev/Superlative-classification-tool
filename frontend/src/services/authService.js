import { apiRequest, refreshAuthSession } from "./apiClient";

export function register(registration) {
  return apiRequest("/auth/register/", {
    method: "POST",
    body: registration,
    auth: false,
    skipAuthRefresh: true,
  });
}

export function verifyEmail(token) {
  return apiRequest("/auth/verify-email/", {
    method: "POST",
    body: { token },
    auth: false,
    skipAuthRefresh: true,
  });
}

export function resendVerification(email) {
  return apiRequest("/auth/resend-verification/", {
    method: "POST",
    body: { email },
    auth: false,
    skipAuthRefresh: true,
  });
}

export function login(credentials) {
  return apiRequest("/auth/login/", {
    method: "POST",
    body: credentials,
    auth: false,
    skipAuthRefresh: true,
  });
}

export function getCurrentUser() {
  return apiRequest("/auth/me/", {
    skipAuthRefresh: true,
  });
}

export function logout(refreshToken) {
  return apiRequest("/auth/logout/", {
    method: "POST",
    body: { refresh: refreshToken },
  });
}

export function restoreSession() {
  return refreshAuthSession().then(() => getCurrentUser());
}
