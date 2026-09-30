/** Topbar with project switcher, notification bell and user menu. */

import { useNavigate, useParams } from 'react-router-dom';
import { ChevronDown, FolderKanban, LogOut, Search, UserRound } from 'lucide-react';
import { useProject, useProjects } from '@/entities/project/hooks';
import { useLogout, useSession } from '@/entities/session/hooks';
import {
  Avatar,
  Badge,
  Dropdown,
  DropdownDivider,
  DropdownItem,
  DropdownLabel,
  Tooltip,
} from '@/shared/ui';
import { NotificationBell } from '@/widgets/notifications/NotificationBell';
import styles from './Topbar.module.css';

/**
 * Render the application topbar.
 *
 * Holds the project switcher, a hidden search placeholder (API is planned),
 * the notification bell and the user menu.
 *
 * @returns topbar element.
 */
export function Topbar() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const id = projectId ? Number(projectId) : undefined;
  const { data: project } = useProject(id);
  const { data: projects } = useProjects({ archived: false });
  const { user } = useSession();
  const logout = useLogout();

  /**
   * Sign the current user out and return to the login screen.
   */
  const handleLogout = () => {
    logout.mutate(undefined, { onSettled: () => navigate('/login') });
  };

  return (
    <header className={styles.topbar}>
      <div className={styles.left}>
        <Dropdown
          minWidth={260}
          trigger={({ open, toggle }) => (
            <button
              type="button"
              className={styles.switcher}
              aria-haspopup="menu"
              aria-expanded={open}
              onClick={toggle}
            >
              <span className={styles.switcherKey}>{project ? project.key : 'ALL'}</span>
              <span className={styles.switcherName}>{project ? project.name : 'Projects'}</span>
              <ChevronDown size={15} />
            </button>
          )}
        >
          {({ close }) => (
            <>
              <DropdownLabel>Projects</DropdownLabel>
              {(projects?.items ?? []).slice(0, 8).map((item) => (
                <DropdownItem
                  key={item.id}
                  active={item.id === id}
                  onClick={() => {
                    close();
                    navigate(`/projects/${item.id}/board`);
                  }}
                >
                  <Badge tone="accent">{item.key}</Badge>
                  {item.name}
                </DropdownItem>
              ))}
              <DropdownDivider />
              <DropdownItem
                icon={<FolderKanban size={16} />}
                onClick={() => {
                  close();
                  navigate('/projects');
                }}
              >
                All projects
              </DropdownItem>
            </>
          )}
        </Dropdown>

        <Tooltip label="Global search is coming with the search API">
          <span className={styles.searchStub}>
            <Search size={16} />
            Search
          </span>
        </Tooltip>
      </div>

      <div className={styles.right}>
        <NotificationBell />
        <Dropdown
          align="end"
          trigger={({ open, toggle }) => (
            <button
              type="button"
              className={styles.userButton}
              aria-label="Account menu"
              aria-haspopup="menu"
              aria-expanded={open}
              onClick={toggle}
            >
              {user && <Avatar username={user.username} size="sm" />}
            </button>
          )}
        >
          {({ close }) => (
            <>
              <DropdownLabel>{user?.username ?? 'Account'}</DropdownLabel>
              <DropdownItem
                icon={<UserRound size={16} />}
                onClick={() => {
                  close();
                  navigate('/me');
                }}
              >
                Profile
              </DropdownItem>
              <DropdownDivider />
              <DropdownItem icon={<LogOut size={16} />} danger onClick={handleLogout}>
                Sign out
              </DropdownItem>
            </>
          )}
        </Dropdown>
      </div>
    </header>
  );
}
