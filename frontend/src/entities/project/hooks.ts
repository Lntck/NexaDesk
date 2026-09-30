/** TanStack Query hooks for projects. */

import { useMutation, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query';
import { queryKeys } from '@/shared/api/queryKeys';
import type {
  Paginated,
  ProjectCreate,
  ProjectListItem,
  ProjectPatch,
  ProjectRead,
  ProjectRole,
} from '@/shared/api/types';
import {
  archiveProject,
  createProject,
  getProject,
  listProjects,
  patchProject,
  restoreProject,
  transferOwnership,
} from './api';

/**
 * Query the project list of the current user.
 *
 * @param filters search text and archived flag.
 * @returns paginated project list query result.
 */
export function useProjects(filters: {
  search?: string;
  archived?: boolean;
}): UseQueryResult<Paginated<ProjectListItem>> {
  return useQuery({
    queryKey: queryKeys.projects(filters),
    queryFn: () => listProjects({ ...filters, page_size: 100 }),
  });
}

/**
 * Query one project.
 *
 * @param projectId project id from the route.
 * @returns project details query result.
 */
export function useProject(projectId: number | undefined): UseQueryResult<ProjectRead> {
  return useQuery({
    queryKey: queryKeys.project(projectId ?? 0),
    queryFn: () => getProject(projectId as number),
    enabled: projectId !== undefined,
  });
}

/**
 * Resolve the current user role inside a project.
 *
 * The project details payload has no role field, so the role is read from
 * the project list caches (active and archived).
 *
 * @param projectId project id from the route.
 * @returns project role of the current user, if resolvable.
 */
export function useProjectRole(projectId: number | undefined): ProjectRole | undefined {
  const active = useProjects({ archived: false });
  const archived = useProjects({ archived: true });
  const items = [...(active.data?.items ?? []), ...(archived.data?.items ?? [])];
  return items.find((project) => project.id === projectId)?.role;
}

/**
 * Create a project.
 *
 * @returns create mutation.
 */
export function useCreateProject() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: ProjectCreate) => createProject(body),
    onSuccess: () => client.invalidateQueries({ queryKey: ['projects'] }),
  });
}

/**
 * Update project metadata.
 *
 * @returns patch mutation.
 */
export function useUpdateProject() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, body }: { projectId: number; body: ProjectPatch }) =>
      patchProject(projectId, body),
    onSuccess: (project) => {
      void client.invalidateQueries({ queryKey: queryKeys.project(project.id) });
      void client.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

/**
 * Archive or restore a project.
 *
 * @returns archive/restore mutation.
 */
export function useArchiveProject() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, archived }: { projectId: number; archived: boolean }) =>
      archived ? archiveProject(projectId) : restoreProject(projectId),
    onSuccess: (project) => {
      void client.invalidateQueries({ queryKey: queryKeys.project(project.id) });
      void client.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

/**
 * Transfer project ownership to another member.
 *
 * @returns ownership transfer mutation.
 */
export function useTransferOwnership() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, userId }: { projectId: number; userId: number }) =>
      transferOwnership(projectId, userId),
    onSuccess: (project) => {
      void client.invalidateQueries({ queryKey: queryKeys.project(project.id) });
      void client.invalidateQueries({ queryKey: queryKeys.members(project.id) });
      void client.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}
