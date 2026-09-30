/** Project settings page: metadata, archive and ownership transfer. */

import { useEffect, useState, type FormEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Archive, ArchiveRestore, Settings, UserCog } from 'lucide-react';
import {
  useArchiveProject,
  useProject,
  useProjectRole,
  useUpdateProject,
} from '@/entities/project/hooks';
import { projectPermissions } from '@/entities/project/model';
import { errorMessage } from '@/shared/api/errors';
import { formatDateTime } from '@/shared/lib/format';
import { Badge, Button, ConfirmDialog, Input, PageHeader, Skeleton, useToast } from '@/shared/ui';
import { TransferOwnershipModal } from '@/features/project/TransferOwnershipModal';
import styles from './ProjectSettingsPage.module.css';

/**
 * Render the project settings form and project-level actions.
 *
 * @returns settings page element.
 */
export function ProjectSettingsPage() {
  const { projectId } = useParams();
  const id = Number(projectId);
  const projectQueryId = Number.isFinite(id) ? id : undefined;
  const { data: project, isLoading } = useProject(projectQueryId);
  const role = useProjectRole(projectQueryId);
  const permissions = projectPermissions(role);
  const update = useUpdateProject();
  const archive = useArchiveProject();
  const toast = useToast();
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [transferOpen, setTransferOpen] = useState(false);

  useEffect(() => {
    if (project) setName(project.name);
  }, [project]);

  /**
   * Save the edited project metadata.
   *
   * @param event submit event of the settings form.
   */
  const handleSave = (event: FormEvent) => {
    event.preventDefault();
    if (!projectQueryId || !name.trim()) return;
    update.mutate(
      { projectId: projectQueryId, body: { name: name.trim() } },
      {
        onSuccess: () => toast.push({ title: 'Project saved', text: name.trim(), tone: 'success' }),
        onError: (error) =>
          toast.push({ title: 'Save failed', text: errorMessage(error), tone: 'error' }),
      },
    );
  };

  /**
   * Archive or restore the project after confirmation.
   */
  const handleArchiveToggle = () => {
    if (!projectQueryId || !project) return;
    archive.mutate(
      { projectId: projectQueryId, archived: !project.is_archived },
      {
        onSuccess: (updated) => {
          toast.push({
            title: updated.is_archived ? 'Project archived' : 'Project restored',
            text: updated.name,
            tone: 'success',
          });
          setArchiveOpen(false);
        },
        onError: (error) =>
          toast.push({ title: 'Action failed', text: errorMessage(error), tone: 'error' }),
      },
    );
  };

  if (isLoading || !project) {
    return (
      <>
        <PageHeader title="Project settings" />
        <Skeleton height={180} radius="var(--radius-md)" />
      </>
    );
  }

  return (
    <>
      <PageHeader
        title={`${project.name} settings`}
        description="Project metadata and lifecycle actions."
        meta={
          <>
            <Badge tone="accent">{project.key}</Badge>
            {project.is_archived && <Badge tone="warning">Archived</Badge>}
          </>
        }
      />

      <section className={styles.section}>
        <h2 className={styles.title}>
          <Settings size={17} /> General
        </h2>
        <p className={styles.hint}>The project key cannot be changed after creation.</p>
        <form className={styles.form} onSubmit={handleSave}>
          <Input
            label="Name"
            maxLength={100}
            value={name}
            disabled={!permissions.canManage}
            onChange={(event) => setName(event.target.value)}
          />
          <Button
            type="submit"
            variant="primary"
            loading={update.isPending}
            disabled={!permissions.canManage || name.trim() === project.name || !name.trim()}
          >
            Save
          </Button>
        </form>
        <div className={styles.meta}>
          <span>Owner: {project.owner.username}</span>
          <span>{project.members_count} members</span>
          <span>{project.tasks_count} tasks</span>
          <span>Created {formatDateTime(project.created_at)}</span>
        </div>
      </section>

      {permissions.canTransfer && (
        <section className={styles.section}>
          <h2 className={styles.title}>
            <UserCog size={17} /> Ownership
          </h2>
          <p className={styles.hint}>
            Transfer the project to another member. You will become an admin.
          </p>
          <div className={styles.actions}>
            <Button
              variant="secondary"
              icon={<UserCog size={16} />}
              onClick={() => setTransferOpen(true)}
            >
              Transfer ownership
            </Button>
          </div>
        </section>
      )}

      {permissions.canArchive && (
        <section className={`${styles.section} ${styles.danger}`}>
          <h2 className={styles.title}>
            {project.is_archived ? <ArchiveRestore size={17} /> : <Archive size={17} />} Lifecycle
          </h2>
          <p className={styles.hint}>
            {project.is_archived
              ? 'Restore the project to make it writable again.'
              : 'Archiving hides the project from the active list and blocks writes.'}
          </p>
          <div className={styles.actions}>
            <Button
              variant={project.is_archived ? 'secondary' : 'danger'}
              icon={project.is_archived ? <ArchiveRestore size={16} /> : <Archive size={16} />}
              onClick={() => setArchiveOpen(true)}
            >
              {project.is_archived ? 'Restore project' : 'Archive project'}
            </Button>
          </div>
        </section>
      )}

      <div className={styles.actions}>
        <Button variant="ghost" onClick={() => navigate(`/projects/${project.id}/board`)}>
          Back to board
        </Button>
      </div>

      <ConfirmDialog
        open={archiveOpen}
        title={project.is_archived ? 'Restore project?' : 'Archive project?'}
        text={
          project.is_archived
            ? `${project.name} will become writable again.`
            : `${project.name} will be hidden from the active list.`
        }
        confirmLabel={project.is_archived ? 'Restore' : 'Archive'}
        danger={!project.is_archived}
        loading={archive.isPending}
        onConfirm={handleArchiveToggle}
        onCancel={() => setArchiveOpen(false)}
      />

      <TransferOwnershipModal
        project={transferOpen ? project : null}
        onClose={() => setTransferOpen(false)}
      />
    </>
  );
}
