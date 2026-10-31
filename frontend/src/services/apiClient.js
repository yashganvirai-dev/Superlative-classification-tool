const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api").replace(
  /\/+$/,
  "",
);
const AUTH_STORAGE_KEY = "superlative_classification_auth";
const AUTH_EXPIRED_EVENT = "superlative-classification-auth-expired";

let refreshPromise = null;
let authGeneration = 0;

export class ApiError extends Error {
  constructor(message, { code = "API_ERROR", status = 500, fields = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.fields = fields;
  }
}

function readTokens() {
  try {
    const stored = window.sessionStorage.getItem(AUTH_STORAGE_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

export function getAuthTokens() {
  return readTokens();
}

export function setAuthTokens({ access, refresh }) {
  authGeneration += 1;
  try {
    window.sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ access, refresh }));
  } catch {
    // The request can still proceed when session storage is unavailable.
  }
}

export function clearAuthTokens() {
  authGeneration += 1;
  try {
    window.sessionStorage.removeItem(AUTH_STORAGE_KEY);
  } catch {
    // The in-memory auth state is cleared by the provider even if storage is unavailable.
  }
}

function notifyAuthExpired() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
  }
}

function buildUrl(path) {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return null;
  }
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function errorFromResponse(response, payload) {
  const error = payload?.error || {};
  return new ApiError(error.message || "The request could not be completed.", {
    code: error.code || "API_ERROR",
    status: response.status,
    fields: error.fields || null,
  });
}

export async function refreshAuthSession() {
  const tokens = readTokens();
  if (!tokens?.refresh) {
    throw new ApiError("Your session has expired.", {
      code: "AUTHENTICATION_REQUIRED",
      status: 401,
    });
  }

  if (!refreshPromise) {
    const generationAtStart = authGeneration;
    refreshPromise = (async () => {
      let response;
      try {
        response = await fetch(buildUrl("/auth/refresh/"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh: tokens.refresh }),
        });
      } catch {
        throw new ApiError("Unable to reach the API. Check your connection and try again.", {
          code: "NETWORK_ERROR",
          status: 0,
        });
      }

      const payload = await parseResponse(response);
      if (!response.ok) {
        const error = errorFromResponse(response, payload);
        if (response.status === 400 || response.status === 401) {
          clearAuthTokens();
          notifyAuthExpired();
        }
        throw error;
      }

      if (generationAtStart !== authGeneration) {
        throw new ApiError("Authentication state changed.", {
          code: "AUTHENTICATION_REQUIRED",
          status: 401,
        });
      }
      if (!payload?.data?.access) {
        throw new ApiError("The authentication response was invalid.", {
          code: "API_ERROR",
          status: 500,
        });
      }

      setAuthTokens({
        access: payload.data.access,
        refresh: payload.data.refresh || tokens.refresh,
      });
      return payload.data;
    })().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}

export async function apiRequest(path, options = {}) {
  const {
    body,
    headers: suppliedHeaders,
    auth = true,
    skipAuthRefresh = false,
    retryOnUnauthorized = true,
    ...fetchOptions
  } = options;
  const headers = new Headers(suppliedHeaders);
  let requestBody = body;

  if (body !== undefined && body !== null && !(body instanceof FormData)) {
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    requestBody = JSON.stringify(body);
  }

  if (auth) {
    const access = readTokens()?.access;
    if (access) {
      headers.set("Authorization", `Bearer ${access}`);
    }
  }

  let response;
  try {
    response = await fetch(buildUrl(path), {
      ...fetchOptions,
      headers,
      body: requestBody,
    });
  } catch {
    throw new ApiError("Unable to reach the API. Check your connection and try again.", {
      code: "NETWORK_ERROR",
      status: 0,
    });
  }
  const payload = await parseResponse(response);

  if (response.status === 401 && auth && !skipAuthRefresh && retryOnUnauthorized) {
    await refreshAuthSession();
    return apiRequest(path, {
      ...options,
      retryOnUnauthorized: false,
    });
  }

  if (!response.ok) {
    throw errorFromResponse(response, payload);
  }

  if (payload && Object.prototype.hasOwnProperty.call(payload, "success")) {
    if (!payload.success) {
      throw new ApiError("The request could not be completed.");
    }
    return payload.data;
  }

  return payload;
}

export { AUTH_EXPIRED_EVENT };
