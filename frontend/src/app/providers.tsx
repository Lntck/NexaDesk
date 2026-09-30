/** Global providers: TanStack Query and the toast system. */

import { useState, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MotionConfig } from 'framer-motion';
import { ToastProvider } from '@/shared/ui/Toast';

/** Props of the AppProviders component. */
export interface AppProvidersProps {
  children: ReactNode;
}

/**
 * Wrap the app with query and toast providers.
 *
 * @param props application children.
 * @returns provider tree.
 */
export function AppProviders({ children }: AppProvidersProps) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      <MotionConfig reducedMotion="user">
        <ToastProvider>{children}</ToastProvider>
      </MotionConfig>
    </QueryClientProvider>
  );
}
