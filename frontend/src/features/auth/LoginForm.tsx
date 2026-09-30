/** Login form with inline validation and API error display. */

import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
import { useLogin } from '@/entities/session/hooks';
import { errorMessage } from '@/shared/api/errors';
import { Button, Input } from '@/shared/ui';
import styles from './AuthForm.module.css';

/**
 * Render the login form and handle the login flow.
 *
 * @returns form element with username and password fields.
 */
export function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const login = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/projects';

  /**
   * Submit the credentials and redirect to the requested page.
   *
   * @param event form submit event.
   */
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    login.mutate(
      { username: username.trim(), password },
      { onSuccess: () => navigate(from, { replace: true }) },
    );
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div>
        <h1 className={styles.title}>Sign in</h1>
        <p className={styles.subtitle}>Continue to your NexaDesk workspace.</p>
      </div>

      {login.isError && (
        <div className={styles.alert} role="alert">
          <AlertCircle size={16} style={{ marginTop: 1, flexShrink: 0 }} />
          <span>{errorMessage(login.error)}</span>
        </div>
      )}

      <Input
        label="Username"
        name="username"
        autoComplete="username"
        required
        minLength={4}
        maxLength={24}
        value={username}
        onChange={(event) => setUsername(event.target.value)}
      />
      <Input
        label="Password"
        name="password"
        type="password"
        autoComplete="current-password"
        required
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />

      <Button type="submit" variant="primary" size="lg" block loading={login.isPending}>
        Sign in
      </Button>

      <p className={styles.footer}>
        No account yet?{' '}
        <Link className={styles.link} to="/register">
          Create one
        </Link>
      </p>
    </form>
  );
}
