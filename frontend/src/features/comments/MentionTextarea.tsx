/**
 * Comment textarea with @mention autocomplete.
 *
 * Typing "@" opens a suggestion list built from project members; picking a
 * name inserts "@username " and keeps the caret position.
 */

import { useMemo, useRef, useState, type KeyboardEvent } from 'react';
import type { UserBrief } from '@/shared/api/types';
import { Avatar } from '@/shared/ui';
import { cn } from '@/shared/lib/cn';
import styles from './Comments.module.css';

/** Props of the MentionTextarea component. */
export interface MentionTextareaProps {
  /** Current draft text. */
  value: string;
  /** Called with the next draft text. */
  onChange: (value: string) => void;
  /** Members that can be mentioned. */
  members: UserBrief[];
  /** Placeholder hint. */
  placeholder?: string;
  /** Disables the input. */
  disabled?: boolean;
  /** Called on Enter without Shift. */
  onSubmit?: () => void;
}

/** Active mention query detected before the caret. */
interface MentionQuery {
  /** Index of the "@" character. */
  start: number;
  /** Text typed after the "@". */
  query: string;
}

/**
 * Render a textarea with mention autocomplete.
 *
 * @param props draft value, member suggestions and handlers.
 * @returns rendered mention input.
 */
export function MentionTextarea({
  value,
  onChange,
  members,
  placeholder,
  disabled = false,
  onSubmit,
}: MentionTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [mention, setMention] = useState<MentionQuery | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  const suggestions = useMemo(() => {
    if (!mention) return [];
    const query = mention.query.toLowerCase();
    return members.filter((member) => member.username.toLowerCase().startsWith(query)).slice(0, 6);
  }, [mention, members]);

  /**
   * Detect an "@name" token right before the caret.
   *
   * @param text current draft text.
   * @param caret caret offset inside the text.
   * @returns mention query or null when there is none.
   */
  const detectMention = (text: string, caret: number): MentionQuery | null => {
    const head = text.slice(0, caret);
    const match = /(^|[\s(])@([\w.-]*)$/.exec(head);
    if (!match) return null;
    return { start: caret - match[2].length - 1, query: match[2] };
  };

  /**
   * Update the draft and refresh the mention query.
   *
   * @param next next draft text.
   */
  const handleChange = (next: string) => {
    onChange(next);
    const caret = textareaRef.current?.selectionStart ?? next.length;
    setMention(detectMention(next, caret));
    setActiveIndex(0);
  };

  /**
   * Insert a mention at the query start.
   *
   * @param username selected username.
   */
  const applyMention = (username: string) => {
    if (!mention) return;
    const before = value.slice(0, mention.start);
    const after = value.slice(mention.start + 1 + mention.query.length);
    const next = `${before}@${username} ${after}`;
    onChange(next);
    setMention(null);
    textareaRef.current?.focus();
  };

  /**
   * Handle keyboard navigation of the suggestion list.
   *
   * @param event keyboard event.
   */
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (mention && suggestions.length > 0) {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setActiveIndex((index) => (index + 1) % suggestions.length);
        return;
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault();
        setActiveIndex((index) => (index - 1 + suggestions.length) % suggestions.length);
        return;
      }
      if (event.key === 'Enter' || event.key === 'Tab') {
        event.preventDefault();
        applyMention(suggestions[activeIndex].username);
        return;
      }
      if (event.key === 'Escape') {
        setMention(null);
        return;
      }
    }
    if (event.key === 'Enter' && !event.shiftKey && onSubmit) {
      event.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className={styles.composer}>
      <textarea
        ref={textareaRef}
        className={styles.commentText}
        style={{
          padding: 'var(--space-3)',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid var(--color-border)',
          backgroundColor: 'var(--color-surface)',
          minHeight: 72,
          resize: 'vertical',
        }}
        placeholder={placeholder ?? 'Write a comment. Use @ to mention teammates.'}
        value={value}
        disabled={disabled}
        onChange={(event) => handleChange(event.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => window.setTimeout(() => setMention(null), 120)}
      />
      {mention && suggestions.length > 0 && (
        <div className={styles.mentionMenu} role="listbox" aria-label="Mention suggestions">
          {suggestions.map((member, index) => (
            <button
              key={member.id}
              type="button"
              role="option"
              aria-selected={index === activeIndex}
              className={cn(styles.mentionItem, index === activeIndex && styles.mentionItemActive)}
              onMouseDown={(event) => {
                event.preventDefault();
                applyMention(member.username);
              }}
            >
              <Avatar username={member.username} size="sm" />
              {member.username}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
