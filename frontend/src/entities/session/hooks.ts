/**
 * Session hooks: bootstrap, login, register and logout flows.
 *
 * The access token lives in memory; on boot the client silently rotates the
 * refresh cookie to restore a session after a page reload.
 */

import { useCallback, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/shared/api/queryKeys';
import { setAccessToken, setUnauthorizedHandler } from '@/shared/api/token';
import type { UserRead, UserRegister } from '@/shared/api/types';
import { aboutMe, login, logout as logoutRequest, register, refreshToken } from './api';
import { useSessionStore } from './model';

/** Shared bootstrap promise: the session is restored exactly once per load. */
let bootstrapPromise: Promise<void> | null = null;

/**
 * Bootstrap the session on app start.
 *
 * Silently refreshes the access token, loads the profile and marks the
 * session anonymous when no valid refresh cookie exists. The work runs once
 * per page load and is shared by every caller, so parallel mounts cannot
 * rotate the refresh cookie twice.
 */
export function useSessionBootstrap(): void {
  const setUser = useSessionStore((state) => state.setUser);
  const setStatus = useSessionStore((state) => state.setStatus);

  useEffect(() => {
    if (!bootstrapPromise) {
      bootstrapPromise = (async () => {
        try {
          const token = await refreshToken();
          setAccessToken(token.access_token);
          setUser(await aboutMe());
        } catch {
          setAccessToken(null);
          setStatus('anonymous');
        }
      })();
    }
  }, [setUser, setStatus]);
}

/**
 * Register the global unauthorized handler that drops the cached session.
 */
export function useUnauthorizedHandler(): void {
  const clear = useSessionStore((state) => state.clear);
  useEffect(() => {
    setUnauthorizedHandler(() => clear());
    return () => setUnauthorizedHandler(null);
  }, [clear]);
}

/**
 * Login mutation storing the user in the session store.
 *
 * @returns mutation exposing login(username, password).
 */
export function useLogin() {
  const setUser = useSessionStore((state) => state.setUser);
  return useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      login(username, password),
    onSuccess: async (token) => {
      setAccessToken(token.access_token);
      const user = await aboutMe();
      setUser(user);
    },
  });
}

/**
 * Register mutation that creates an account.
 *
 * @returns mutation exposing register(payload).
 */
export function useRegister() {
  return useMutation({ mutationFn: (body: UserRegister) => register(body) });
}

/**
 * Logout mutation revoking the refresh token and clearing caches.
 *
 * @returns mutation exposing logout().
 */
export function useLogout() {
  const client = useQueryClient();
  const clear = useSessionStore((state) => state.clear);
  return useMutation({
    mutationFn: () => logoutRequest(),
    onSettled: () => {
      setAccessToken(null);
      clear();
      client.clear();
    },
  });
}

/**
 * Provide the current user from the session store.
 *
 * @returns current user and auth status.
 */
export function useSession(): {
  user: UserRead | null;
  status: 'loading' | 'authenticated' | 'anonymous';
} {
  const user = useSessionStore((state) => state.user);
  const status = useSessionStore((state) => state.status);
  return { user, status };
}

/**
 * Replace the cached current user after profile changes.
 *
 * @returns setter for the current user.
 */
export function useSetUser(): (user: UserRead | null) => void {
  const setUser = useSessionStore((state) => state.setUser);
  const client = useQueryClient();
  return useCallback(
    (user) => {
      setUser(user);
      client.setQueryData(queryKeys.me(), user);
    },
    [setUser, client],
  );
}
