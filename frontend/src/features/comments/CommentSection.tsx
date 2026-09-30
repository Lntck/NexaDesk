/**
 * Comment section of a task.
 *
 * Lists comments with author, time and inline edit/delete actions and
 * renders the mention-aware composer above the list.
 */

import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { MessageSquare, Pencil, Trash2 } from 'lucide-react';
import {
  useComments,
  useCreateComment,
  useDeleteComment,
  useUpdateComment,
} from '@/entities/comment/hooks';
import { useMembers } from '@/entities/member/hooks';
import { useSession } from '@/entities/session/hooks';
import type { CommentRead } from '@/shared/api/types';
import { errorMessage } from '@/shared/api/errors';
import { formatDateTime } from '@/shared/lib/format';
import { Avatar, Button, ConfirmDialog, Pagination, useToast } from '@/shared/ui';
import { MentionTextarea } from './MentionTextarea';
import styles from './Comments.module.css';

/** Props of the CommentSection component. */
export interface CommentSectionProps {
  /** Task to show comments for. */
  taskId: number;
  /** Whether the current user can post comments. */
  canComment: boolean;
  /** Whether the current user can moderate comments of others. */
  canManage: boolean;
  /** Project whose members can be mentioned. */
  projectId: number | undefined;
}

/**
 * Render the comment list and composer of a task.
 *
 * @param props task id, permissions and mention scope.
 * @returns rendered comment section.
 */
export function CommentSection({ taskId, canComment, canManage, projectId }: CommentSectionProps) {
  const { user } = useSession();
  const [page, setPage] = useState(1);
  const { data } = useComments(taskId, page);
  const { data: members } = useMembers(projectId);
  const create = useCreateComment();
  const update = useUpdateComment();
  const remove = useDeleteComment();
  const toast = useToast();

  const [draft, setDraft] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<CommentRead | null>(null);

  useEffect(() => {
    setPage(1);
  }, [taskId]);

  const items = data?.items ?? [];
  const mentionable = (members?.items ?? []).map((member) => member.user);

  /**
   * Post the drafted comment.
   *
   * The draft is cleared immediately and restored if the request fails; the
   * new comment itself is inserted optimistically by the mutation.
   */
  const handleCreate = () => {
    const body = draft.trim();
    if (!body) return;
    setDraft('');
    create.mutate(
      { taskId, body: { body }, page },
      {
        onError: (error) => {
          setDraft(body);
          toast.push({ title: 'Comment not posted', text: errorMessage(error), tone: 'error' });
        },
      },
    );
  };

  /**
   * Save the edited comment body.
   *
   * @param comment comment being edited.
   */
  const handleUpdate = (comment: CommentRead) => {
    const body = editDraft.trim();
    if (!body || body === comment.body) {
      setEditingId(null);
      return;
    }
    update.mutate(
      { commentId: comment.id, body: { body }, taskId },
      {
        onSuccess: () => setEditingId(null),
        onError: (error) =>
          toast.push({ title: 'Comment not saved', text: errorMessage(error), tone: 'error' }),
      },
    );
  };

  return (
    <section className={styles.comments}>
      <h3 className={styles.commentHeader} style={{ fontSize: 'var(--font-size-16)' }}>
        <MessageSquare size={16} /> Comments
      </h3>

      {items.length === 0 && <p className={styles.commentTime}>No comments yet.</p>}

      <AnimatePresence initial={false}>
        {items.map((comment) => {
          const mine = comment.author.id === user?.id;
          return (
            <CommentItem
              key={comment.id}
              comment={comment}
              canEdit={mine}
              canDelete={mine || canManage}
              editing={editingId === comment.id}
              editDraft={editDraft}
              onEdit={() => {
                setEditingId(comment.id);
                setEditDraft(comment.body);
              }}
              onEditDraft={setEditDraft}
              onSave={() => handleUpdate(comment)}
              onCancelEdit={() => setEditingId(null)}
              onDelete={() => setDeleteTarget(comment)}
            />
          );
        })}
      </AnimatePresence>

      {data && data.total > data.page_size && (
        <Pagination page={page} pageSize={data.page_size} total={data.total} onChange={setPage} />
      )}

      {canComment && (
        <div>
          <MentionTextarea
            value={draft}
            onChange={setDraft}
            members={mentionable}
            disabled={create.isPending}
            onSubmit={handleCreate}
          />
          <div className={styles.composerActions}>
            <Button
              size="sm"
              variant="primary"
              loading={create.isPending}
              disabled={draft.trim().length === 0}
              onClick={handleCreate}
            >
              Comment
            </Button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete comment?"
        text="The comment will be hidden from the task. Activity history is kept."
        confirmLabel="Delete"
        danger
        loading={remove.isPending}
        onConfirm={() => {
          if (!deleteTarget) return;
          remove.mutate(
            { commentId: deleteTarget.id, taskId },
            {
              onSuccess: () => setDeleteTarget(null),
              onError: (error) =>
                toast.push({ title: 'Delete failed', text: errorMessage(error), tone: 'error' }),
            },
          );
        }}
        onCancel={() => setDeleteTarget(null)}
      />
    </section>
  );
}

/**
 * Highlight @mentions inside a comment body.
 *
 * @param body comment text.
 * @returns text nodes with mention spans.
 */
function renderMentions(body: string) {
  const parts = body.split(/(@[\w.-]+)/g);
  return parts.map((part, index) =>
    part.startsWith('@') ? (
      <span key={index} className={styles.mention}>
        {part}
      </span>
    ) : (
      part
    ),
  );
}

/** Props of the internal comment item. */
interface CommentItemProps {
  comment: CommentRead;
  canEdit: boolean;
  canDelete: boolean;
  editing: boolean;
  editDraft: string;
  onEdit: () => void;
  onEditDraft: (value: string) => void;
  onSave: () => void;
  onCancelEdit: () => void;
  onDelete: () => void;
}

/**
 * Render one comment with its actions.
 *
 * @param props comment data, permissions and handlers.
 * @returns rendered comment item.
 */
function CommentItem({
  comment,
  canEdit,
  canDelete,
  editing,
  editDraft,
  onEdit,
  onEditDraft,
  onSave,
  onCancelEdit,
  onDelete,
}: CommentItemProps) {
  return (
    <motion.article
      className={styles.comment}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0, transition: { duration: 0.2 } }}
      exit={{ opacity: 0, transition: { duration: 0.15 } }}
      layout
    >
      <Avatar username={comment.author.username} size="sm" />
      <div className={styles.commentBody}>
        <div className={styles.commentHeader}>
          <span className={styles.commentAuthor}>{comment.author.username}</span>
          <span className={styles.commentTime}>{formatDateTime(comment.created_at)}</span>
          <span className={styles.commentActions}>
            {canEdit && !editing && (
              <button
                type="button"
                className={styles.mentionItem}
                onClick={onEdit}
                aria-label="Edit comment"
              >
                <Pencil size={13} />
              </button>
            )}
            {canDelete && !editing && (
              <button
                type="button"
                className={styles.mentionItem}
                onClick={onDelete}
                aria-label="Delete comment"
              >
                <Trash2 size={13} />
              </button>
            )}
          </span>
        </div>
        {editing ? (
          <div>
            <MentionTextarea
              value={editDraft}
              onChange={onEditDraft}
              members={[]}
              onSubmit={onSave}
            />
            <div className={styles.composerActions}>
              <Button size="sm" variant="primary" onClick={onSave}>
                Save
              </Button>
              <Button size="sm" variant="ghost" onClick={onCancelEdit}>
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <p className={styles.commentText}>{renderMentions(comment.body)}</p>
        )}
      </div>
    </motion.article>
  );
}
