/** Application router with auth guards and the main layout. */

import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { BrowserRouter } from 'react-router-dom';
import { useSession, useSessionBootstrap, useUnauthorizedHandler } from '@/entities/session/hooks';
import { CenteredSpinner } from '@/shared/ui';
import { AppLayout } from './layout/AppLayout';
import { AuthLayout } from './layout/AuthLayout';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { ProjectsPage } from '@/pages/ProjectsPage';
import { BoardPage } from '@/pages/BoardPage';
import { TasksPage } from '@/pages/TasksPage';
import { ActivityPage } from '@/pages/ActivityPage';
import { MembersPage } from '@/pages/MembersPage';
import { LabelsPage } from '@/pages/LabelsPage';
import { ProjectSettingsPage } from '@/pages/ProjectSettingsPage';
import { TaskPage } from '@/pages/TaskPage';
import { ProfilePage } from '@/pages/ProfilePage';
import { NotFoundPage } from '@/pages/NotFoundPage';

/**
 * Render the router with protected application routes.
 *
 * Also bootstraps the session so a reload on a protected route restores
 * the current user from the refresh cookie.
 *
 * @returns complete route tree.
 */
export function App() {
  useSessionBootstrap();
  useUnauthorizedHandler();

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>
        <Route
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route path="/" element={<Navigate to="/projects" replace />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:projectId/board" element={<BoardPage />} />
          <Route path="/projects/:projectId/tasks" element={<TasksPage />} />
          <Route path="/projects/:projectId/activity" element={<ActivityPage />} />
          <Route path="/projects/:projectId/members" element={<MembersPage />} />
          <Route path="/projects/:projectId/labels" element={<LabelsPage />} />
          <Route path="/projects/:projectId/settings" element={<ProjectSettingsPage />} />
          <Route path="/tasks/:taskId" element={<TaskPage />} />
          <Route path="/me" element={<ProfilePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

/** Props of the RequireAuth guard. */
export interface RequireAuthProps {
  children: React.ReactNode;
}

/**
 * Block protected routes until the session is resolved.
 *
 * Redirects anonymous visitors to the login screen and shows a spinner
 * while the silent refresh bootstrap is running.
 *
 * @param props protected route content.
 * @returns guarded route element.
 */
function RequireAuth({ children }: RequireAuthProps) {
  const { status } = useSession();
  const location = useLocation();

  if (status === 'loading') {
    return (
      <div style={{ height: '100vh', display: 'grid', placeItems: 'center' }}>
        <CenteredSpinner size={32} />
      </div>
    );
  }
  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}
