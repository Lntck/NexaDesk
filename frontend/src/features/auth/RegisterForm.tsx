/** Registration form with field validation and API error display. */

import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';
import { useLogin, useRegister } from '@/entities/session/hooks';
import { errorMessage } from '@/shared/api/errors';
import { Button, Input } from '@/shared/ui';
import styles from './AuthForm.module.css';

/**
 * Render the registration form and handle account creation.
 *
 * After a successful registration the user is signed in automatically and
 * taken to the project list.
 *
 * @returns form element with username, email and password fields.
 */
export function RegisterForm() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const register = useRegister();
  const login = useLogin();
  const navigate = useNavigate();

  /**
   * Create the account and sign in with the same credentials.
   *
   * @param event form submit event.
   */
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    register.mutate(
      { username: username.trim(), email: email.trim(), password },
      {
        onSuccess: () => {
          login.mutate(
            { username: username.trim(), password },
            { onSuccess: () => navigate('/projects', { replace: true }) },
          );
        },
      },
    );
  };

  const pending = register.isPending || login.isPending;

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div>
        <h1 className={styles.title}>Create account</h1>
        <p className={styles.subtitle}>Set up your NexaDesk profile in seconds.</p>
      </div>

      {(register.isError || login.isError) && (
        <div className={styles.alert} role="alert">
          <AlertCircle size={16} style={{ marginTop: 1, flexShrink: 0 }} />
          <span>{errorMessage(register.isError ? register.error : login.error)}</span>
        </div>
      )}

      <Input
        label="Username"
        name="username"
        autoComplete="username"
        required
        minLength={4}
        maxLength={24}
        hint="4 to 24 characters"
        value={username}
        onChange={(event) => setUsername(event.target.value)}
      />
      <Input
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        required
        value={email}
        onChange={(event) => setEmail(event.target.value)}
      />
      <Input
        label="Password"
        name="password"
        type="password"
        autoComplete="new-password"
        required
        minLength={8}
        maxLength={24}
        hint="8 to 24 characters"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
      />

      <Button type="submit" variant="primary" size="lg" block loading={pending}>
        Create account
      </Button>

      <p className={styles.footer}>
        Already have an account?{' '}
        <Link className={styles.link} to="/login">
          Sign in
        </Link>
      </p>
    </form>
  );
}
