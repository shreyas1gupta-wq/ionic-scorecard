/**
 * Form and layout primitives.
 *
 * Hand-written rather than pulled in through the shadcn CLI, which is
 * interactive. shadcn is copy-in-and-own by design anyway, so components can be
 * dropped in later alongside these without a migration.
 *
 * Everything here is a server component: no state, no effects. Interactivity
 * lives in the small number of files that actually need it.
 */

import type { ReactNode } from 'react';

const INPUT_BASE =
  'w-full rounded-md border border-[var(--border)] bg-[var(--bg)] px-3 py-2 text-sm ' +
  'text-[var(--text)] outline-none placeholder:text-[var(--muted)] ' +
  'focus-visible:border-[var(--accent)] focus-visible:ring-2 focus-visible:ring-[var(--accent)]/30 ' +
  'disabled:opacity-60';

export function Field({
  label,
  htmlFor,
  hint,
  required,
  children,
}: {
  label: string;
  htmlFor: string;
  hint?: string;
  required?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-sm font-medium">
        {label}
        {required && (
          <span className="ml-1 text-[var(--danger)]" aria-hidden="true">
            *
          </span>
        )}
      </label>
      {children}
      {hint && (
        <p id={`${htmlFor}-hint`} className="text-xs text-[var(--muted)]">
          {hint}
        </p>
      )}
    </div>
  );
}

export function TextInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${INPUT_BASE} ${props.className ?? ''}`} />;
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${INPUT_BASE} min-h-24 ${props.className ?? ''}`} />;
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${INPUT_BASE} ${props.className ?? ''}`} />;
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' }) {
  const tone =
    variant === 'primary'
      ? 'bg-[var(--accent)] text-white border-transparent hover:opacity-90'
      : 'bg-transparent text-[var(--text)] border-[var(--border)] hover:border-[var(--muted)]';
  return (
    <button
      {...props}
      className={
        'inline-flex items-center justify-center rounded-md border px-3.5 py-2 text-sm font-medium ' +
        'transition-opacity disabled:cursor-not-allowed disabled:opacity-60 ' +
        `${tone} ${className}`
      }
    />
  );
}

/**
 * A validation failure.
 *
 * `role="alert"` so a screen reader announces it when it appears after a
 * submission, rather than the user wondering why nothing happened.
 */
export function ErrorText({ children }: { children: ReactNode }) {
  if (!children) return null;
  return (
    <p role="alert" className="text-sm text-[var(--danger)]">
      {children}
    </p>
  );
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-md border border-[var(--border)] bg-[var(--surface)] p-4 ${className}`}
    >
      {children}
    </div>
  );
}

export function PageHeading({ title, meta }: { title: string; meta?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-3">
      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      {meta && <div className="text-sm text-[var(--muted)] tnum">{meta}</div>}
    </div>
  );
}
