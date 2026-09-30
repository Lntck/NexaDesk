/** Pagination controls for paginated collections. */

import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './Button';
import styles from './surface.module.css';

/** Props of the Pagination component. */
export interface PaginationProps {
  /** Current page number, starting at 1. */
  page: number;
  /** Items per page. */
  pageSize: number;
  /** Total item count across pages. */
  total: number;
  /** Called with the requested page number. */
  onChange: (page: number) => void;
}

/**
 * Render previous/next pagination with a range label.
 *
 * @param props paging state and change handler.
 * @returns rendered pagination element or null for a single page.
 */
export function Pagination({ page, pageSize, total, onChange }: PaginationProps) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1 && total <= pageSize) return null;
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);
  return (
    <div className={styles.pagination}>
      <span>
        {first}-{last} of {total}
      </span>
      <div className={styles.paginationButtons}>
        <Button
          size="sm"
          variant="ghost"
          icon={<ChevronLeft size={16} />}
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          Prev
        </Button>
        <Button
          size="sm"
          variant="ghost"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
        >
          Next
          <ChevronRight size={16} />
        </Button>
      </div>
    </div>
  );
}
