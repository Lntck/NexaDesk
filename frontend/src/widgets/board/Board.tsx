/**
 * Kanban board with drag and drop.
 *
 * Cross-column moves and reordering are sent to the server with one reorder
 * command; the board cache is refetched on success and restored on error
 * (frontend/PLAN.md, "Экраны и роуты").
 */

import { useEffect, useMemo, useState } from 'react';
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCorners,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { useQueryClient } from '@tanstack/react-query';
import type { BoardCard, BoardColumn as BoardColumnData } from '@/shared/api/types';
import { queryKeys } from '@/shared/api/queryKeys';
import { asApiError } from '@/shared/api/errors';
import { useBoard, useReorderTask } from '@/entities/task/hooks';
import { useProjectRole } from '@/entities/project/hooks';
import { projectPermissions } from '@/entities/project/model';
import { CenteredSpinner, useToast } from '@/shared/ui';
import { BoardColumn } from './BoardColumn';
import { BoardCardItem } from './BoardCard';
import styles from './Board.module.css';

/** Props of the Board component. */
export interface BoardProps {
  /** Project to render. */
  projectId: number;
  /** Called when a card is opened. */
  onOpenCard: (card: BoardCard) => void;
  /** Called when a card is created inside a column. */
  onCreateCard: (statusId: number) => void;
}

/**
 * Render the kanban board with drag and drop.
 *
 * @param props project id and card handlers.
 * @returns board element with columns and cards.
 */
export function Board({ projectId, onOpenCard, onCreateCard }: BoardProps) {
  const { data, isLoading, refetch } = useBoard(projectId);
  const role = useProjectRole(projectId);
  const permissions = projectPermissions(role);
  const reorder = useReorderTask();
  const toast = useToast();
  const client = useQueryClient();

  const [columns, setColumns] = useState<BoardColumnData[]>([]);
  const [activeCard, setActiveCard] = useState<BoardCard | null>(null);
  const [overColumnId, setOverColumnId] = useState<number | null>(null);

  useEffect(() => {
    if (data) setColumns(data.columns);
  }, [data]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const columnOfCard = useMemo(
    () => (cardId: number) =>
      columns.find((column) => column.tasks.some((task) => task.id === cardId)) ?? null,
    [columns],
  );

  /**
   * Track the card being dragged for the overlay.
   *
   * @param event drag start event.
   */
  const handleDragStart = (event: DragStartEvent) => {
    const card = event.active.data.current?.card as BoardCard | undefined;
    setActiveCard(card ?? null);
  };

  /**
   * Mirror cross-column moves in local state while dragging.
   *
   * @param event drag over event.
   */
  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    if (!over) return;
    const activeId = Number(active.id);
    const overData = over.data.current;
    const source = columnOfCard(activeId);
    if (!source) return;

    const targetStatusId =
      overData?.type === 'column'
        ? (overData.column as BoardColumnData).status.id
        : (columnOfCard(Number(over.id))?.status.id ?? source.status.id);

    setOverColumnId(targetStatusId);
    if (targetStatusId === source.status.id) return;

    setColumns((current) =>
      current.map((column) => {
        if (column.status.id === source.status.id) {
          return { ...column, tasks: column.tasks.filter((task) => task.id !== activeId) };
        }
        if (column.status.id === targetStatusId) {
          const card = source.tasks.find((task) => task.id === activeId);
          if (!card) return column;
          const overIndex = column.tasks.findIndex((task) => task.id === Number(over.id));
          const tasks = [...column.tasks];
          const insertAt = overIndex >= 0 ? overIndex : tasks.length;
          tasks.splice(insertAt, 0, card);
          return { ...column, tasks };
        }
        return column;
      }),
    );
  };

  /**
   * Persist the final card position with the reorder command.
   *
   * @param event drag end event.
   */
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCard(null);
    setOverColumnId(null);
    if (!over) return;

    const activeId = Number(active.id);
    const snapshot = data ? data.columns : columns;
    const target = columns.find((column) => column.tasks.some((task) => task.id === activeId));
    if (!target) return;

    const index = target.tasks.findIndex((task) => task.id === activeId);
    const after_task_id = index > 0 ? target.tasks[index - 1].id : null;
    const before_task_id =
      index >= 0 && index < target.tasks.length - 1 ? target.tasks[index + 1].id : null;

    const sourceColumn = snapshot.find((column) =>
      column.tasks.some((task) => task.id === activeId),
    );
    const movedWithinColumn =
      sourceColumn?.status.id === target.status.id &&
      sourceColumn.tasks.findIndex((task) => task.id === activeId) === index;

    if (movedWithinColumn && sourceColumn) return;

    reorder.mutate(
      { taskId: activeId, body: { status_id: target.status.id, before_task_id, after_task_id } },
      {
        onSuccess: () => {
          void client.invalidateQueries({ queryKey: queryKeys.board(projectId) });
          void refetch();
        },
        onError: (error) => {
          setColumns(snapshot);
          const apiError = asApiError(error);
          toast.push({
            title: 'Move failed',
            text:
              apiError.code === 'invalid_transition'
                ? 'Tasks can only move to adjacent columns.'
                : apiError.message,
            tone: 'error',
          });
          void refetch();
        },
      },
    );
  };

  if (isLoading) return <CenteredSpinner size={32} />;

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={() => {
        setActiveCard(null);
        setOverColumnId(null);
        setColumns(data ? data.columns : columns);
      }}
    >
      <div className={styles.board}>
        {columns.map((column) => (
          <BoardColumn
            key={column.status.id}
            column={column}
            onOpenCard={onOpenCard}
            onCreateCard={onCreateCard}
            canCreate={permissions.canEditTasks}
            isOver={overColumnId === column.status.id}
          />
        ))}
      </div>
      <DragOverlay dropAnimation={{ duration: 200, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' }}>
        {activeCard && <BoardCardItem card={activeCard} onOpen={() => undefined} dragging />}
      </DragOverlay>
    </DndContext>
  );
}
