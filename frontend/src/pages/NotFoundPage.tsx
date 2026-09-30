/** Placeholder page for unknown routes. */

import { useNavigate } from 'react-router-dom';
import { Compass } from 'lucide-react';
import { Button, EmptyState } from '@/shared/ui';

/**
 * Render the 404 page with a way back to the workspace.
 *
 * @returns not found page element.
 */
export function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <EmptyState
      icon={<Compass size={24} />}
      title="Page not found"
      text="The page you are looking for does not exist or has been moved."
      action={
        <Button variant="primary" onClick={() => navigate('/projects')}>
          Back to projects
        </Button>
      }
    />
  );
}
