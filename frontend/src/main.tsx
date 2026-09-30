/**
 * Application bootstrap: mounts the React tree with global providers.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './app/App';
import { AppProviders } from './app/providers';
import './shared/styles/tokens.css';
import './shared/styles/global.css';

/**
 * Mount the application into the DOM root.
 */
function bootstrap(): void {
  const container = document.getElementById('root');
  if (!container) throw new Error('Root element not found');
  createRoot(container).render(
    <StrictMode>
      <AppProviders>
        <App />
      </AppProviders>
    </StrictMode>,
  );
}

bootstrap();
