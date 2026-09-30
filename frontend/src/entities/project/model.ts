/** Project role helpers derived from the project membership hierarchy. */

import type { ProjectRole } from '@/shared/api/types';

/** Role hierarchy level; higher numbers dominate lower ones. */
const ROLE_LEVEL: Record<ProjectRole, number> = {
  viewer: 0,
  member: 1,
  admin: 2,
  owner: 3,
};

/**
 * Compare two project roles by hierarchy.
 *
 * @param role role to test.
 * @param minimum required role.
 * @returns true when role is at least as powerful as minimum.
 */
export function roleAtLeast(role: ProjectRole | undefined, minimum: ProjectRole): boolean {
  if (!role) return false;
  return ROLE_LEVEL[role] >= ROLE_LEVEL[minimum];
}

/** Effective permissions of a project member in the UI. */
export interface ProjectPermissions {
  /** Can read project data. */
  canView: boolean;
  /** Can create and edit tasks, comment. */
  canEditTasks: boolean;
  /** Can delete own tasks. */
  canDeleteOwnTasks: boolean;
  /** Can delete any task, manage statuses, labels and members. */
  canManage: boolean;
  /** Can archive or restore the project. */
  canArchive: boolean;
  /** Can transfer ownership. */
  canTransfer: boolean;
}

/**
 * Resolve UI permissions from a project role.
 *
 * @param role current user role in the project.
 * @returns permission flags for menus and buttons.
 */
export function projectPermissions(role: ProjectRole | undefined): ProjectPermissions {
  return {
    canView: roleAtLeast(role, 'viewer'),
    canEditTasks: roleAtLeast(role, 'member'),
    canDeleteOwnTasks: roleAtLeast(role, 'member'),
    canManage: roleAtLeast(role, 'admin'),
    canArchive: roleAtLeast(role, 'admin'),
    canTransfer: role === 'owner',
  };
}

/**
 * Human readable label of a project role.
 *
 * @param role project role.
 * @returns display label.
 */
export function roleLabel(role: ProjectRole): string {
  const labels: Record<ProjectRole, string> = {
    owner: 'Owner',
    admin: 'Admin',
    member: 'Member',
    viewer: 'Viewer',
  };
  return labels[role];
}
