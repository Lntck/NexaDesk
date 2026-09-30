/** Session store: current user and auth status. */

import { create } from 'zustand';
import type { UserRead } from '@/shared/api/types';

/** Auth status of the client session. */
export type SessionStatus = 'loading' | 'authenticated' | 'anonymous';

/** Session state kept outside React Query for fast synchronous access. */
interface SessionState {
  /** Resolved current user, if authenticated. */
  user: UserRead | null;
  /** Auth status after the bootstrap attempt. */
  status: SessionStatus;
  /** Store the authenticated user. */
  setUser: (user: UserRead | null) => void;
  /** Set the auth status. */
  setStatus: (status: SessionStatus) => void;
  /** Drop all session state. */
  clear: () => void;
}

/**
 * Session store with the current user and auth status.
 */
export const useSessionStore = create<SessionState>((set) => ({
  user: null,
  status: 'loading',
  setUser: (user) => set({ user, status: user ? 'authenticated' : 'anonymous' }),
  setStatus: (status) => set({ status }),
  clear: () => set({ user: null, status: 'anonymous' }),
}));

/**
 * Read the current user synchronously outside React.
 *
 * @returns current user or null.
 */
export function getSessionUser(): UserRead | null {
  return useSessionStore.getState().user;
}
