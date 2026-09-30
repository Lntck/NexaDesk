/** Landing page: product overview with entry points to the workspace. */

import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BellRing, Columns3, Layers, MessageSquareText, ShieldCheck, Zap } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useSession } from '@/entities/session/hooks';
import { screenVariants } from '@/shared/motion/variants';
import { Button } from '@/shared/ui';
import styles from './HomePage.module.css';

/** Feature cards rendered under the hero. */
const FEATURES: { icon: LucideIcon; title: string; text: string }[] = [
  {
    icon: Columns3,
    title: 'Kanban board',
    text: 'Columns from project statuses, drag and drop with ordering, and a task list with filters.',
  },
  {
    icon: MessageSquareText,
    title: 'Comments and mentions',
    text: 'Discuss tasks inline, mention teammates with @, attach labels and watch the tasks you care about.',
  },
  {
    icon: Zap,
    title: 'Live updates',
    text: 'Every change is broadcast over SSE, so the board and the activity feed stay in sync for the whole team.',
  },
  {
    icon: BellRing,
    title: 'Notifications',
    text: 'Mentions, assignments and watched-task changes land in the bell, the drawer and toast messages.',
  },
  {
    icon: ShieldCheck,
    title: 'Roles and access',
    text: 'Project roles from viewer to owner, ownership transfer and archived projects kept out of the way.',
  },
  {
    icon: Layers,
    title: 'Structured work',
    text: 'Projects, board statuses, task priorities, deadlines and estimates keep the workflow predictable.',
  },
];

/**
 * Render the public home page with the product overview.
 *
 * The header adapts to the session: anonymous visitors get sign in and
 * registration actions, authenticated users get a link to their projects.
 *
 * @returns home page element.
 */
export function HomePage() {
  const { status } = useSession();

  return (
    <div className={styles.page}>
      <header className={styles.topbar}>
        <Link to="/" className={styles.brand}>
          <span className={styles.brandMark}>
            <Layers size={20} />
          </span>
          <span className={styles.brandName}>NexaDesk</span>
        </Link>
        <nav className={styles.actions}>
          {status === 'authenticated' && (
            <Link to="/projects">
              <Button variant="primary">Open workspace</Button>
            </Link>
          )}
          {status === 'anonymous' && (
            <>
              <Link to="/login">
                <Button variant="ghost">Sign in</Button>
              </Link>
              <Link to="/register">
                <Button variant="primary">Create account</Button>
              </Link>
            </>
          )}
        </nav>
      </header>

      <motion.main
        className={styles.main}
        variants={screenVariants}
        initial="initial"
        animate="animate"
      >
        <section className={styles.hero}>
          <p className={styles.eyebrow}>Collaborative task management</p>
          <h1 className={styles.title}>Projects, tasks and team progress in one workspace</h1>
          <p className={styles.lead}>
            NexaDesk keeps the work of a team on a shared kanban board: break projects into tasks,
            assign them, discuss the details and follow every change in real time.
          </p>
          <div className={styles.heroActions}>
            {status === 'authenticated' ? (
              <Link to="/projects">
                <Button variant="primary" size="lg">
                  Go to projects
                </Button>
              </Link>
            ) : (
              <>
                <Link to="/register">
                  <Button variant="primary" size="lg">
                    Get started
                  </Button>
                </Link>
                <Link to="/login">
                  <Button variant="ghost" size="lg">
                    Sign in
                  </Button>
                </Link>
              </>
            )}
          </div>
        </section>

        <section className={styles.features} aria-label="Features">
          {FEATURES.map(({ icon: Icon, title, text }) => (
            <article key={title} className={styles.feature}>
              <span className={styles.featureIcon}>
                <Icon size={18} />
              </span>
              <h2 className={styles.featureTitle}>{title}</h2>
              <p className={styles.featureText}>{text}</p>
            </article>
          ))}
        </section>
      </motion.main>

      <footer className={styles.footer}>
        <span>NexaDesk</span>
        <span className={styles.footerMuted}>Team task management platform</span>
      </footer>
    </div>
  );
}
