import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  AUTH_EXPIRED_EVENT,
  clearAuthTokens,
  getAuthTokens,
  setAuthTokens,
} from "../services/apiClient";
import {
  login as loginRequest,
  logout as logoutRequest,
  restoreSession,
} from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [initialRefreshToken] = useState(() => getAuthTokens()?.refresh || null);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(Boolean(initialRefreshToken));

  const clearSession = useCallback(() => {
    clearAuthTokens();
    setUser(null);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    let active = true;

    async function restore() {
      if (!initialRefreshToken) {
        return;
      }
      try {
        const currentUser = await restoreSession();
        if (active) {
          setUser(currentUser);
        }
      } catch (error) {
        if (
          active &&
          ["AUTHENTICATION_REQUIRED", "AUTHENTICATION_FAILED"].includes(error.code)
        ) {
          clearSession();
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    const handleExpired = () => clearSession();
    window.addEventListener(AUTH_EXPIRED_EVENT, handleExpired);
    restore();

    return () => {
      active = false;
      window.removeEventListener(AUTH_EXPIRED_EVENT, handleExpired);
    };
  }, [clearSession, initialRefreshToken]);

  const login = useCallback(async (credentials) => {
    const data = await loginRequest(credentials);
    setAuthTokens(data);
    setUser(data.user);
    setIsLoading(false);
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    const refreshToken = getAuthTokens()?.refresh;
    if (refreshToken) {
      try {
        await logoutRequest(refreshToken);
      } catch {
        // Local sign-out must still complete when the server is unavailable.
      }
    }
    clearSession();
  }, [clearSession]);

  const value = useMemo(
    () => ({ isLoading, login, logout, user }),
    [isLoading, login, logout, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
