/** Project members page: roles, invitations and removals. */

import { useState, type FormEvent } from 'react';
import { useParams } from 'react-router-dom';
import { Trash2, UserPlus, Users } from 'lucide-react';
import { useProject, useProjectRole } from '@/entities/project/hooks';
import { projectPermissions, roleLabel } from '@/entities/project/model';
import {
  useAddMember,
  useMembers,
  useRemoveMember,
  useUpdateMemberRole,
} from '@/entities/member/hooks';
import type { MemberRead, ProjectRole } from '@/shared/api/types';
import { errorMessage } from '@/shared/api/errors';
import { formatDate } from '@/shared/lib/format';
import {
  Avatar,
  Badge,
  Button,
  ConfirmDialog,
  EmptyState,
  Input,
  PageHeader,
  Select,
  Skeleton,
  useToast,
} from '@/shared/ui';
import styles from './MembersPage.module.css';

/** Roles that can be granted to a new member. */
const ASSIGNABLE_ROLES: ProjectRole[] = ['admin', 'member', 'viewer'];

/**
 * Render the project member table with role management.
 *
 * @returns members page element.
 */
export function MembersPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const projectQueryId = Number.isFinite(id) ? id : undefined;
  const { data: project, isLoading: projectLoading } = useProject(projectQueryId);
  const role = useProjectRole(projectQueryId);
  const permissions = projectPermissions(role);
  const { data: members, isLoading } = useMembers(projectQueryId);
  const addMember = useAddMember();
  const updateRole = useUpdateMemberRole();
  const removeMember = useRemoveMember();
  const toast = useToast();

  const [userIdText, setUserIdText] = useState('');
  const [newRole, setNewRole] = useState<ProjectRole>('member');
  const [removeTarget, setRemoveTarget] = useState<MemberRead | null>(null);

  /**
   * Add a user to the project by numeric id.
   *
   * @param event submit event of the invite form.
   */
  const handleAdd = (event: FormEvent) => {
    event.preventDefault();
    const userId = Number(userIdText);
    if (!projectQueryId || !Number.isInteger(userId) || userId <= 0) {
      toast.push({ title: 'Invalid user id', text: 'Enter a positive numeric id.', tone: 'error' });
      return;
    }
    addMember.mutate(
      { projectId: projectQueryId, body: { user_id: userId, role: newRole } },
      {
        onSuccess: (member) => {
          setUserIdText('');
          toast.push({
            title: 'Member added',
            text: `${member.user.username} joined as ${roleLabel(newRole)}`,
            tone: 'success',
          });
        },
        onError: (error) =>
          toast.push({ title: 'Member not added', text: errorMessage(error), tone: 'error' }),
      },
    );
  };

  /**
   * Change the role of a member.
   *
   * @param member member to update.
   * @param nextRole requested role.
   */
  const handleRoleChange = (member: MemberRead, nextRole: ProjectRole) => {
    if (!projectQueryId) return;
    updateRole.mutate(
      { projectId: projectQueryId, userId: member.user.id, role: nextRole },
      {
        onSuccess: () =>
          toast.push({
            title: 'Role updated',
            text: `${member.user.username} is now ${roleLabel(nextRole)}`,
            tone: 'success',
          }),
        onError: (error) =>
          toast.push({ title: 'Role not updated', text: errorMessage(error), tone: 'error' }),
      },
    );
  };

  /**
   * Remove a member after confirmation.
   */
  const handleRemove = () => {
    if (!projectQueryId || !removeTarget) return;
    removeMember.mutate(
      { projectId: projectQueryId, userId: removeTarget.user.id },
      {
        onSuccess: () => {
          toast.push({
            title: 'Member removed',
            text: removeTarget.user.username,
            tone: 'success',
          });
          setRemoveTarget(null);
        },
        onError: (error) =>
          toast.push({ title: 'Remove failed', text: errorMessage(error), tone: 'error' }),
      },
    );
  };

  return (
    <>
      <PageHeader
        title={project ? `${project.name} members` : 'Members'}
        description="Project team, roles and access."
      />

      {permissions.canManage && (
        <div className={styles.toolbar}>
          <form className={styles.form} onSubmit={handleAdd}>
            <Input
              label="User ID"
              type="number"
              min={1}
              placeholder="Numeric user id"
              hint="The user shares it from the Profile page (User ID, copy button)."
              value={userIdText}
              onChange={(event) => setUserIdText(event.target.value)}
            />
            <Select
              label="Role"
              value={newRole}
              onChange={(event) => setNewRole(event.target.value as ProjectRole)}
            >
              {ASSIGNABLE_ROLES.map((value) => (
                <option key={value} value={value}>
                  {roleLabel(value)}
                </option>
              ))}
            </Select>
            <Button
              type="submit"
              variant="primary"
              icon={<UserPlus size={16} />}
              loading={addMember.isPending}
            >
              Add member
            </Button>
          </form>
        </div>
      )}

      {isLoading || projectLoading ? (
        <div style={{ display: 'grid', gap: 'var(--space-2)' }}>
          <Skeleton height={52} radius="var(--radius-sm)" />
          <Skeleton height={52} radius="var(--radius-sm)" />
        </div>
      ) : (members?.items.length ?? 0) === 0 ? (
        <EmptyState
          icon={<Users size={24} />}
          title="No members"
          text="Add users to start collaborating."
        />
      ) : (
        <div className={styles.table}>
          <div className={`${styles.row} ${styles.head}`}>
            <span>User</span>
            <span>Role</span>
            <span>Joined</span>
            <span />
          </div>
          {(members?.items ?? []).map((member) => (
            <div key={member.user.id} className={styles.row}>
              <div className={styles.person}>
                <Avatar username={member.user.username} size="md" />
                <div className={styles.identity}>
                  <span className={styles.name}>{member.user.username}</span>
                  <span className={styles.muted}>ID {member.user.id}</span>
                </div>
              </div>
              <div>
                {permissions.canManage && member.role !== 'owner' ? (
                  <Select
                    aria-label={`Role of ${member.user.username}`}
                    value={member.role}
                    disabled={updateRole.isPending}
                    onChange={(event) =>
                      handleRoleChange(member, event.target.value as ProjectRole)
                    }
                  >
                    {ASSIGNABLE_ROLES.map((value) => (
                      <option key={value} value={value}>
                        {roleLabel(value)}
                      </option>
                    ))}
                  </Select>
                ) : (
                  <Badge tone={member.role === 'owner' ? 'accent' : 'neutral'}>
                    {roleLabel(member.role)}
                  </Badge>
                )}
              </div>
              <span className={styles.muted}>{formatDate(member.joined_at)}</span>
              <div>
                {permissions.canManage && member.role !== 'owner' && (
                  <Button
                    variant="ghost"
                    iconOnly
                    icon={<Trash2 size={16} />}
                    aria-label={`Remove ${member.user.username}`}
                    onClick={() => setRemoveTarget(member)}
                  />
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={removeTarget !== null}
        title="Remove member?"
        text={removeTarget ? `${removeTarget.user.username} will lose access to the project.` : ''}
        confirmLabel="Remove"
        danger
        loading={removeMember.isPending}
        onConfirm={handleRemove}
        onCancel={() => setRemoveTarget(null)}
      />
    </>
  );
}
