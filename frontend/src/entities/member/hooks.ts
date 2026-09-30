/** TanStack Query hooks for project members. */

import { useMutation, useQuery, useQueryClient, type UseQueryResult } from '@tanstack/react-query';
import { queryKeys } from '@/shared/api/queryKeys';
import type { MemberAdd, MemberList, ProjectRole } from '@/shared/api/types';
import { addMember, listMembers, removeMember, updateMemberRole } from './api';

/**
 * Query the member list of a project.
 *
 * @param projectId project id.
 * @returns member list query result.
 */
export function useMembers(projectId: number | undefined): UseQueryResult<MemberList> {
  return useQuery({
    queryKey: queryKeys.members(projectId ?? 0),
    queryFn: () => listMembers(projectId as number),
    enabled: projectId !== undefined,
  });
}

/**
 * Add a user to a project.
 *
 * @returns add member mutation.
 */
export function useAddMember() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, body }: { projectId: number; body: MemberAdd }) =>
      addMember(projectId, body),
    onSuccess: (_member, variables) =>
      client.invalidateQueries({ queryKey: queryKeys.members(variables.projectId) }),
  });
}

/**
 * Change a member role.
 *
 * @returns role change mutation.
 */
export function useUpdateMemberRole() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      projectId,
      userId,
      role,
    }: {
      projectId: number;
      userId: number;
      role: ProjectRole;
    }) => updateMemberRole(projectId, userId, role),
    onSuccess: (_member, variables) =>
      client.invalidateQueries({ queryKey: queryKeys.members(variables.projectId) }),
  });
}

/**
 * Remove a member from a project.
 *
 * @returns remove member mutation.
 */
export function useRemoveMember() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, userId }: { projectId: number; userId: number }) =>
      removeMember(projectId, userId),
    onSuccess: (_data, variables) =>
      client.invalidateQueries({ queryKey: queryKeys.members(variables.projectId) }),
  });
}
