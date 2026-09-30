/** Draggable kanban task card. */

import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Avatar, Badge } from '@/shared/ui';
import type { BoardCard } from '@/shared/api/types';
import { PRIORITY_META } from '@/entities/task/model';
import { cn } from '@/shared/lib/cn';
import styles from './Board.module.css';

/** Props of the BoardCardItem component. */
export interface BoardCardItemProps {
  /** Card data. */
  card: BoardCard;
  /** Called when the card is clicked. */
  onOpen: (card: BoardCard) => void;
  /** True while the card is being dragged. */
  dragging?: boolean;
}

/**
 * Render one sortable kanban card.
 *
 * @param props card data, open handler and dragging flag.
 * @returns rendered card element.
 */
export function BoardCardItem({ card, onOpen, dragging = false }: BoardCardItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: card.id,
    data: { type: 'card', card },
  });

  const priority = PRIORITY_META[card.priority];

  return (
    <div
      ref={setNodeRef}
      className={cn(styles.card, (isDragging || dragging) && styles.cardDragging)}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      {...attributes}
      {...listeners}
      onClick={() => onOpen(card)}
    >
      <span className={styles.cardKey}>{card.key}</span>
      <p className={styles.cardTitle}>{card.title}</p>
      <div className={styles.cardFooter}>
        <div className={styles.cardMeta}>
          <span
            className={styles.priorityDot}
            style={{ backgroundColor: priority.color }}
            title={`${priority.label} priority`}
          />
          <Badge tone="muted">{priority.label}</Badge>
        </div>
        {card.assignee && <Avatar username={card.assignee.username} size="sm" />}
      </div>
    </div>
  );
}
