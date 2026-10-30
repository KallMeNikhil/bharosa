import { useState } from "react";
import type { ButtonHTMLAttributes, ElementType, ReactNode } from "react";

import { useCountUp, useInView } from "../hooks/useMotion";
import { Icon } from "./icons";

export function Container({ children }: { children: ReactNode }) {
  return <div className="container">{children}</div>;
}

export function BrandMark({ size = 26 }: { size?: number }) {
  return (
    <img
      src="/bharosa-mark.png"
      alt="Bharosa"
      width={size}
      height={size}
      className="brand-mark"
    />
  );
}

export function Section({
  children,
  tight,
}: {
  children: ReactNode;
  tight?: boolean;
}) {
  return <section className={tight ? "section section--tight" : "section"}>{children}</section>;
}

// Fades and lifts its content in the first time it scrolls into view.
export function Reveal({
  children,
  as: Tag = "div",
  className,
  delay = 0,
}: {
  children: ReactNode;
  as?: ElementType;
  className?: string;
  delay?: 0 | 1 | 2 | 3;
}) {
  const [ref, inView] = useInView<HTMLElement>();
  return (
    <Tag
      ref={ref}
      className={`reveal reveal--d${delay}${inView ? " is-in" : ""}${className ? ` ${className}` : ""}`}
    >
      {children}
    </Tag>
  );
}

export function SectionIntro({
  eyebrow,
  title,
  children,
  level = 2,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  children?: ReactNode;
  level?: 1 | 2;
}) {
  const Heading = level === 1 ? "h1" : "h2";
  return (
    <div className={`section-intro${level === 1 ? " section-intro--page" : ""}`}>
      {eyebrow && <span className="eyebrow">{eyebrow}</span>}
      <Heading>{title}</Heading>
      {children && <div className="section-intro__body">{children}</div>}
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="page-header">
      <div className="page-header__text">
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {actions && <div className="button-row">{actions}</div>}
    </div>
  );
}

export function TechnicalDisclosure({
  label = "Technical detail",
  children,
}: {
  label?: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`disclosure${open ? " is-open" : ""}`}>
      <button
        type="button"
        className="disclosure__trigger"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        {label}
        <span className="disclosure__sign" aria-hidden="true" />
      </button>
      {open && <div className="disclosure__body">{children}</div>}
    </div>
  );
}

export type Tone = "neutral" | "info" | "good" | "warn" | "bad";

const TONE_BY_VALUE: Record<string, Tone> = {
  GENUINE: "good",
  CAUTION: "warn",
  INVALID: "bad",
  ALREADY_REPORTED: "bad",
  UNAVAILABLE: "neutral",

  RESERVED: "neutral",
  SIGNED: "info",
  PRINTED: "info",
  PRINT_VERIFIED: "info",
  RECONCILED: "info",
  ACTIVATED: "good",
  PRINT_REJECTED: "bad",

  ACTIVE: "good",
  ROTATED: "neutral",
  REVOKED: "bad",
  COMPROMISED: "bad",

  OPEN: "warn",
  UNDER_REVIEW: "info",
  SUBSTANTIATED: "bad",
  DISMISSED: "neutral",

  NEGLIGIBLE: "neutral",
  LOW: "info",
  MODERATE: "warn",
  HIGH: "bad",
};

export function toneFor(value: string): Tone {
  return TONE_BY_VALUE[value] ?? "neutral";
}

export function Badge({ children, tone }: { children: ReactNode; tone?: Tone }) {
  const resolved = tone ?? (typeof children === "string" ? toneFor(children) : "neutral");
  return <span className={`badge badge--${resolved}`}>{children}</span>;
}

export function Card({
  title,
  subtitle,
  actions,
  children,
  wide,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <section className={`card${wide ? " card--wide" : ""}`}>
      {(title || actions) && (
        <header className="card__head">
          <div>
            {title && <h2 className="card__title">{title}</h2>}
            {subtitle && <p className="card__subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="card__actions">{actions}</div>}
        </header>
      )}
      <div className="card__body">{children}</div>
    </section>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: ReactNode;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span className="field__label">{label}</span>
      {children}
      {hint && <span className="field__hint">{hint}</span>}
    </label>
  );
}

export function Row({ children }: { children: ReactNode }) {
  return <div className="row">{children}</div>;
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  pending?: boolean;
}

export function Button({ variant = "secondary", pending, children, ...rest }: ButtonProps) {
  return (
    <button
      type={rest.type ?? "button"}
      {...rest}
      className={`button button--${variant}${pending ? " is-pending" : ""}${rest.className ? ` ${rest.className}` : ""}`}
      disabled={rest.disabled || pending}
      aria-busy={pending || undefined}
    >
      {pending ? (
        <>
          <span className="spinner" aria-hidden="true" />
          Working…
        </>
      ) : (
        children
      )}
    </button>
  );
}

export function ErrorNote({ children }: { children: ReactNode }) {
  if (!children) return null;
  return (
    <p className="note note--error" role="alert">
      <Icon name="alert" size={18} />
      <span>{children}</span>
    </p>
  );
}

export function InfoNote({ children }: { children: ReactNode }) {
  return (
    <p className="note note--info">
      <Icon name="info" size={18} />
      <span>{children}</span>
    </p>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty">{children}</p>;
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="skeleton" role="status">
      <span className="sr-only">{label}…</span>
      <span className="skeleton__line" />
      <span className="skeleton__line" />
      <span className="skeleton__line skeleton__line--short" />
    </div>
  );
}

export function Mono({ value, short }: { value: string | null | undefined; short?: boolean }) {
  const [copied, setCopied] = useState(false);
  if (!value) return <span className="muted">—</span>;

  const shown = short && value.length > 12 ? `${value.slice(0, 8)}…` : value;

  return (
    <button
      type="button"
      className={`mono${copied ? " is-copied" : ""}`}
      title={`${value} — click to copy`}
      onClick={() => {
        void navigator.clipboard.writeText(value);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1200);
      }}
    >
      {copied ? "copied" : shown}
    </button>
  );
}

export function CountUp({ value }: { value: number }) {
  return <>{useCountUp(value)}</>;
}

export function Stat({ label, value, tone }: { label: string; value: ReactNode; tone?: Tone }) {
  return (
    <div className={`stat${tone ? ` stat--${tone}` : ""}`}>
      <span className="stat__value">{typeof value === "number" ? <CountUp value={value} /> : value}</span>
      <span className="stat__label">{label}</span>
    </div>
  );
}

export function Timestamp({ value }: { value: string | null | undefined }) {
  if (!value) return <span className="muted">—</span>;
  const parsed = new Date(value);
  return (
    <time className="timestamp" dateTime={value} title={value}>
      {parsed.toLocaleString()}
    </time>
  );
}

export function Table({ head, children }: { head: ReactNode; children: ReactNode }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>{head}</thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}
