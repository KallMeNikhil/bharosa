import { useState } from "react";
import { Link } from "react-router-dom";

import { auth } from "../../api/endpoints";
import { Button, ErrorNote, Field } from "../../components/ui";
import { useAction } from "../../hooks/useResource";
import { useStartSession } from "../../session/useAccountSession";

const MIN_PASSWORD_LENGTH = 10;

export function Register() {
  const startSession = useStartSession();
  const [companyName, setCompanyName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");

  const tooShort = password.length > 0 && password.length < MIN_PASSWORD_LENGTH;
  const mismatch = confirm.length > 0 && confirm !== password;
  const ready =
    companyName.trim().length >= 2 &&
    email.trim().length > 3 &&
    password.length >= MIN_PASSWORD_LENGTH &&
    confirm === password;

  const register = useAction(async () => {
    await startSession(
      await auth.register({
        company_name: companyName.trim(),
        display_name: displayName.trim() || undefined,
        email: email.trim(),
        password,
      }),
    );
  });

  return (
    <div className="auth-form">
      <div className="auth-form__intro">
        <h1>Create your company's account</h1>
        <p className="muted">
          This sets up a workspace for your company and makes you its owner. You can register
          products and issue pack identities straight away.
        </p>
      </div>

      <form
        className="card"
        onSubmit={(event) => {
          event.preventDefault();
          if (ready && !register.pending) void register.run();
        }}
      >
        <div className="card__body">
          <Field label="Company name">
            <input
              autoComplete="organization"
              value={companyName}
              onChange={(event) => setCompanyName(event.target.value)}
              placeholder="Kisan Crop Sciences"
            />
          </Field>
          <Field label="Your name" hint="Optional.">
            <input
              autoComplete="name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
            />
          </Field>
          <Field label="Work email">
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@company.com"
            />
          </Field>
          <Field
            label="Password"
            hint={tooShort ? `At least ${MIN_PASSWORD_LENGTH} characters.` : undefined}
          >
            <input
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </Field>
          <Field label="Confirm password" hint={mismatch ? "The passwords do not match." : undefined}>
            <input
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
            />
          </Field>
          <Button
            type="submit"
            variant="primary"
            className="button--block"
            disabled={!ready}
            pending={register.pending}
          >
            Create account
          </Button>
          <ErrorNote>{register.error}</ErrorNote>
        </div>
      </form>

      <p className="auth-form__switch">
        Already have an account? <Link to="/app/login">Sign in</Link>
      </p>
    </div>
  );
}
