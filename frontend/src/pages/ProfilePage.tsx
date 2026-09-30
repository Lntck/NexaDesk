/**
 * Profile page: account details and session actions.
 *
 * Password change is not part of the current API contract (planned
 * `POST /api/v1/me/password`), so the section is shown as a placeholder.
 */

import { useNavigate } from 'react-router-dom';
import { Copy, KeyRound, LogOut } from 'lucide-react';
import { useLogout, useSession } from '@/entities/session/hooks';
import { copyText } from '@/shared/lib/clipboard';
import { formatDate } from '@/shared/lib/format';
import { Avatar, Badge, Button, Divider, Panel, PageHeader, Tooltip, useToast } from '@/shared/ui';
import styles from './ProfilePage.module.css';

/**
 * Render the current user profile page.
 *
 * @returns profile page element.
 */
export function ProfilePage() {
  const { user } = useSession();
  const logout = useLogout();
  const navigate = useNavigate();
  const toast = useToast();

  /**
   * Sign out and return to the login screen.
   */
  const handleLogout = () => {
    logout.mutate(undefined, { onSettled: () => navigate('/login') });
  };

  /**
   * Copy the current user id for project invitations.
   */
  const handleCopyId = async () => {
    const ok = await copyText(String(user?.id ?? ''));
    toast.push({
      title: ok ? 'User id copied' : 'Copy failed',
      text: ok ? 'Share it so teammates can add you to a project.' : 'Clipboard is not available.',
      tone: ok ? 'success' : 'error',
    });
  };

  if (!user) return null;

  return (
    <>
      <PageHeader title="Profile" description="Your account in this workspace." />
      <div className={styles.columns}>
        <Panel title="Account">
          <div className={styles.profile}>
            <Avatar username={user.username} size="lg" />
            <div>
              <p className={styles.name}>{user.username}</p>
              <p className={styles.email}>{user.email}</p>
            </div>
            <Badge tone={user.role === 'admin' ? 'accent' : 'neutral'}>
              {user.role === 'admin' ? 'Administrator' : 'Member'}
            </Badge>
          </div>
          <Divider />
          <dl className={styles.facts}>
            <div>
              <dt>User ID</dt>
              <dd className={styles.idRow}>
                <span>{user.id}</span>
                <Tooltip label="Copy user id">
                  <span>
                    <Button
                      variant="ghost"
                      size="sm"
                      iconOnly
                      icon={<Copy size={14} />}
                      aria-label="Copy user id"
                      onClick={handleCopyId}
                    />
                  </span>
                </Tooltip>
              </dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{user.is_active ? 'Active' : 'Disabled'}</dd>
            </div>
            <div>
              <dt>Registered</dt>
              <dd>{formatDate(user.created_at)}</dd>
            </div>
            <div>
              <dt>Updated</dt>
              <dd>{formatDate(user.updated_at)}</dd>
            </div>
          </dl>
        </Panel>

        <Panel title="Security">
          <div className={styles.securityRow}>
            <div>
              <p className={styles.securityTitle}>Password</p>
              <p className={styles.securityText}>
                Password management is coming with the account API.
              </p>
            </div>
            <Tooltip label="Available with the planned account endpoints">
              <span>
                <Button icon={<KeyRound size={16} />} disabled>
                  Change password
                </Button>
              </span>
            </Tooltip>
          </div>
          <Divider />
          <div className={styles.securityRow}>
            <div>
              <p className={styles.securityTitle}>Session</p>
              <p className={styles.securityText}>Sign out of this device.</p>
            </div>
            <Button
              variant="danger"
              icon={<LogOut size={16} />}
              loading={logout.isPending}
              onClick={handleLogout}
            >
              Sign out
            </Button>
          </div>
        </Panel>
      </div>
    </>
  );
}
