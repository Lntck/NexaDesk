/** Kanban column with a droppable card list. */

import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { Plus } from 'lucide-react';
import type { BoardCard, BoardColumn as BoardColumnData } from '@/shared/api/types';
import { hexToRgba } from '@/shared/lib/colors';
import { Button } from '@/shared/ui';
import { BoardCardItem } from './BoardCard';
import styles from './Board.module.css';

/** Props of the BoardColumn component. */
export interface BoardColumnProps {
  /** Column status and its cards. */
  column: BoardColumnData;
  /** Called when a card is clicked. */
  onOpenCard: (card: BoardCard) => void;
  /** Called when a card is created in this column. */
  onCreateCard: (statusId: number) => void;
  /** Cards are hidden for users without task permissions. */
  canCreate: boolean;
  /** True while this column is a drag target. */
  isOver?: boolean;
}

/**
 * Render one kanban column with its cards.
 *
 * @param props column data, card handlers and permissions.
 * @returns rendered column element.
 */
export function BoardColumn({
  column,
  onOpenCard,
  onCreateCard,
  canCreate,
  isOver = false,
}: BoardColumnProps) {
  const { setNodeRef } = useDroppable({
    id: `column-${column.status.id}`,
    data: { type: 'column', column },
  });
  const cardIds = column.tasks.map((task) => task.id);

  return (
    <div
      ref={setNodeRef}
      className={styles.column}
      style={isOver ? { borderColor: 'var(--color-accent)' } : undefined}
    >
      <header className={styles.columnHeader}>
        <span
          className={styles.statusDot}
          style={{ backgroundColor: hexToRgba(column.status.color, 0.9) }}
        />
        <span className={styles.columnName}>{column.status.name}</span>
        <BadgeCount count={column.tasks.length} />
      </header>

      <SortableContext items={cardIds} strategy={verticalListSortingStrategy}>
        <div className={styles.columnList}>
          {column.tasks.map((card) => (
            <BoardCardItem key={card.id} card={card} onOpen={onOpenCard} />
          ))}
        </div>
      </SortableContext>

      {column.has_more && <p className={styles.hasMore}>More cards are hidden in this column</p>}

      {canCreate && (
        <div className={styles.columnFooter}>
          <Button
            variant="ghost"
            size="sm"
            block
            className={styles.addCard}
            icon={<Plus size={15} />}
            onClick={() => onCreateCard(column.status.id)}
          >
            Add task
          </Button>
        </div>
      )}
    </div>
  );
}

/**
 * Render the column card counter pill.
 *
 * @param props card count.
 * @returns rendered counter.
 */
function BadgeCount({ count }: { count: number }) {
  return <span className={styles.countPill}>{count}</span>;
}
