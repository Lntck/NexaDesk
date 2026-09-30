/** Dark glass sidebar with project navigation. */

import { NavLink, useLocation, useParams } from 'react-router-dom';
import { Activity, CheckSquare, FolderKanban, Layers, Settings, Tags, Users } from 'lucide-react';
import { useProject, useProjectRole } from '@/entities/project/hooks';
import { projectPermissions } from '@/entities/project/model';
import { useSession } from '@/entities/session/hooks';
import { cn } from '@/shared/lib/cn';
import styles from './Sidebar.module.css';

/**
 * Render the application sidebar with project sections.
 *
 * The project block appears only on project routes and hides management
 * sections for viewers.
 *
 * @returns sidebar element.
 */
export function Sidebar() {
  const { projectId } = useParams();
  const location = useLocation();
  const { user } = useSession();
  const id = projectId ? Number(projectId) : undefined;
  const { data: project } = useProject(id);
  const role = useProjectRole(id);
  const permissions = projectPermissions(role);
  const onProject = location.pathname.startsWith('/projects/');

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <div className={styles.brandMark}>
          <Layers size={20} />
        </div>
        <div>
          <p className={styles.brandName}>NexaDesk</p>
          <p className={styles.brandTagline}>Workspace</p>
        </div>
      </div>

      <nav className={styles.nav}>
        <NavLink
          to="/projects"
          className={({ isActive }) => cn(styles.link, isActive && styles.linkActive)}
        >
          <FolderKanban size={18} />
          Projects
        </NavLink>

        {onProject && id && (
          <>
            <p className={styles.sectionLabel}>{project ? project.name : 'Project'}</p>
            <NavLink
              to={`/projects/${id}/board`}
              className={({ isActive }) => cn(styles.link, isActive && styles.linkActive)}
            >
              <Layers size={18} />
              Board
            </NavLink>
            <NavLink
              to={`/projects/${id}/tasks`}
              className={({ isActive }) => cn(styles.link, isActive && styles.linkActive)}
            >
              <CheckSquare size={18} />
              Tasks
            </NavLink>
            <NavLink
              to={`/projects/${id}/activity`}
              className={({ isActive }) => cn(styles.link, isActive && styles.linkActive)}
            >
              <Activity size={18} />
              Activity
            </NavLink>
            <NavLink
              to={`/projects/${id}/members`}
              className={({ isActive }) => cn(styles.link, isActive && styles.linkActive)}
            >
              <Users size={18} />
              Members
            </NavLink>
            {permissions.canManage && (
              <>
                <p className={styles.sectionLabel}>Manage</p>
                <NavLink
                  to={`/projects/${id}/labels`}
                  className={({ isActive }) => cn(styles.link, isActive && styles.linkActive)}
                >
                  <Tags size={18} />
                  Labels
                </NavLink>
                <NavLink
                  to={`/projects/${id}/settings`}
                  className={({ isActive }) => cn(styles.link, isActive && styles.linkActive)}
                >
                  <Settings size={18} />
                  Settings
                </NavLink>
              </>
            )}
          </>
        )}
      </nav>

      {user && (
        <div className={styles.userCard}>
          <div className={styles.userAvatar}>{user.username.slice(0, 2).toUpperCase()}</div>
          <div className={styles.userInfo}>
            <p className={styles.userName}>{user.username}</p>
            <p className={styles.userEmail}>{user.email}</p>
          </div>
        </div>
      )}
    </aside>
  );
}
