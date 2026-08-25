import { useState } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Container({ children }: { children: ReactNode }) {
  return <div className="container">{children}</div>;
}

export function BrandMark({ size = 26 }: { size?: number }) {
  return (
    <img
      src="/bharosa.png"
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
      <div>
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
    <div className="disclosure">
      <button
        type="button"
        className="disclosure__trigger"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        {label}
        <span aria-hidden="true">{open ? "\u2212" : "+"}</span>
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
      className={`button button--${variant}${rest.className ? ` ${rest.className}` : ""}`}
      disabled={rest.disabled || pending}
    >
      {pending ? "Working…" : children}
    </button>
  );
}

export function ErrorNote({ children }: { children: ReactNode }) {
  if (!children) return null;
  return <p className="note note--error">{children}</p>;
}

export function InfoNote({ children }: { children: ReactNode }) {
  return <p className="note note--info">{children}</p>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="empty">{children}</p>;
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return <p className="empty">{label}…</p>;
}

export function Mono({ value, short }: { value: string | null | undefined; short?: boolean }) {
  const [copied, setCopied] = useState(false);
  if (!value) return <span className="muted">—</span>;

  const shown = short && value.length > 12 ? `${value.slice(0, 8)}…` : value;

  return (
    <button
      type="button"
      className="mono"
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

export function Stat({ label, value, tone }: { label: string; value: ReactNode; tone?: Tone }) {
  return (
    <div className={`stat${tone ? ` stat--${tone}` : ""}`}>
      <span className="stat__value">{value}</span>
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
