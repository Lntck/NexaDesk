/** Project list page: cards, filters, create and archive actions. */

import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Archive,
  ArchiveRestore,
  FolderKanban,
  MoreHorizontal,
  Plus,
  Settings,
  UserCog,
} from 'lucide-react';
import { useArchiveProject, useProjects, useProjectRole } from '@/entities/project/hooks';
import { projectPermissions, roleLabel } from '@/entities/project/model';
import type { ProjectListItem } from '@/shared/api/types';
import { formatDate } from '@/shared/lib/format';
import { errorMessage } from '@/shared/api/errors';
import {
  Badge,
  Button,
  Card,
  Dropdown,
  DropdownItem,
  EmptyState,
  Input,
  Skeleton,
  Tabs,
  useToast,
  PageHeader,
} from '@/shared/ui';
import { ProjectCreateModal } from '@/features/project/ProjectCreateModal';
import { TransferOwnershipModal } from '@/features/project/TransferOwnershipModal';
import styles from './ProjectsPage.module.css';

/**
 * Render the project list with filters and project actions.
 *
 * @returns projects page element.
 */
export function ProjectsPage() {
  const [search, setSearch] = useState('');
  const [archived, setArchived] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [transferTarget, setTransferTarget] = useState<ProjectListItem | null>(null);
  const { data, isLoading } = useProjects({ search: search.trim() || undefined, archived });
  const archive = useArchiveProject();
  const toast = useToast();
  const navigate = useNavigate();

  const items = useMemo(() => data?.items ?? [], [data]);

  /**
   * Archive or restore a project with toast feedback.
   *
   * @param project project to toggle.
   */
  const handleArchiveToggle = (project: ProjectListItem) => {
    archive.mutate(
      { projectId: project.id, archived: !project.is_archived },
      {
        onSuccess: (updated) => {
          toast.push({
            title: updated.is_archived ? 'Project archived' : 'Project restored',
            text: `${updated.name} (${updated.key})`,
            tone: 'success',
          });
        },
        onError: (error) =>
          toast.push({ title: 'Action failed', text: errorMessage(error), tone: 'error' }),
      },
    );
  };

  return (
    <>
      <PageHeader
        title="Projects"
        description="Everything your team is working on."
        actions={
          <Button variant="primary" icon={<Plus size={16} />} onClick={() => setCreateOpen(true)}>
            New project
          </Button>
        }
      />

      <div className={styles.toolbar}>
        <div className={styles.search}>
          <Input
            placeholder="Search projects"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <Tabs
          items={[
            { value: 'active', label: 'Active' },
            { value: 'archived', label: 'Archived' },
          ]}
          value={archived ? 'archived' : 'active'}
          onChange={(value) => setArchived(value === 'archived')}
        />
      </div>

      {isLoading ? (
        <div className={styles.grid}>
          {[0, 1, 2].map((index) => (
            <Skeleton key={index} height={148} radius="var(--radius-md)" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={<FolderKanban size={24} />}
          title={archived ? 'No archived projects' : 'No projects yet'}
          text={
            archived
              ? 'Archived projects will appear here.'
              : 'Create your first project to start tracking work.'
          }
          action={
            !archived && (
              <Button
                variant="primary"
                icon={<Plus size={16} />}
                onClick={() => setCreateOpen(true)}
              >
                New project
              </Button>
            )
          }
        />
      ) : (
        <div className={styles.grid}>
          {items.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onOpen={() => navigate(`/projects/${project.id}/board`)}
              onArchiveToggle={() => handleArchiveToggle(project)}
              onTransfer={() => setTransferTarget(project)}
            />
          ))}
        </div>
      )}

      <ProjectCreateModal open={createOpen} onClose={() => setCreateOpen(false)} />
      <TransferOwnershipModal project={transferTarget} onClose={() => setTransferTarget(null)} />
    </>
  );
}

/** Props of the internal ProjectCard component. */
interface ProjectCardProps {
  project: ProjectListItem;
  onOpen: () => void;
  onArchiveToggle: () => void;
  onTransfer: () => void;
}

/**
 * Render one project card with its action menu.
 *
 * @param props project data and action handlers.
 * @returns rendered project card.
 */
function ProjectCard({ project, onOpen, onArchiveToggle, onTransfer }: ProjectCardProps) {
  const navigate = useNavigate();
  const role = useProjectCardRole(project.id);
  const permissions = projectPermissions(role);

  return (
    <Card interactive onClick={onOpen} className={styles.card}>
      <div className={styles.cardTop}>
        <Badge tone="accent">{project.key}</Badge>
        <div onClick={(event) => event.stopPropagation()}>
          <Dropdown
            align="end"
            trigger={({ toggle }) => (
              <button
                type="button"
                className={styles.menuButton}
                onClick={toggle}
                aria-label="Project actions"
              >
                <MoreHorizontal size={18} />
              </button>
            )}
          >
            {({ close }) => (
              <>
                <DropdownItem
                  icon={<FolderKanban size={16} />}
                  onClick={() => {
                    close();
                    onOpen();
                  }}
                >
                  Open board
                </DropdownItem>
                {permissions.canManage && (
                  <DropdownItem
                    icon={<Settings size={16} />}
                    onClick={() => {
                      close();
                      navigate(`/projects/${project.id}/settings`);
                    }}
                  >
                    Settings
                  </DropdownItem>
                )}
                {permissions.canArchive && (
                  <DropdownItem
                    icon={
                      project.is_archived ? <ArchiveRestore size={16} /> : <Archive size={16} />
                    }
                    onClick={() => {
                      close();
                      onArchiveToggle();
                    }}
                  >
                    {project.is_archived ? 'Restore' : 'Archive'}
                  </DropdownItem>
                )}
                {permissions.canTransfer && (
                  <DropdownItem
                    icon={<UserCog size={16} />}
                    onClick={() => {
                      close();
                      onTransfer();
                    }}
                  >
                    Transfer ownership
                  </DropdownItem>
                )}
              </>
            )}
          </Dropdown>
        </div>
      </div>

      <h3 className={styles.cardTitle}>{project.name}</h3>
      <div className={styles.cardMeta}>
        <Badge tone={project.is_archived ? 'warning' : 'neutral'}>
          {project.is_archived ? 'Archived' : roleLabel(project.role)}
        </Badge>
        <span className={styles.cardDate}>Created {formatDate(project.created_at)}</span>
      </div>
    </Card>
  );
}

/**
 * Resolve the project role for a card without extra requests.
 *
 * @param projectId project id.
 * @returns role of the current user in the project.
 */
function useProjectCardRole(projectId: number) {
  return useProjectRole(projectId);
}
