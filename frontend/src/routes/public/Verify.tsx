import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button, Container, Field, InfoNote } from "../../components/ui";
import { useAction } from "../../hooks/useResource";
import { checkCode, looksLikeSerial, prepareCode } from "../../lib/verification";

const SERIAL_LENGTH = 26;

const STEPS = [
  { label: "Code", detail: "Is it a code Bharosa issued?" },
  { label: "Signature", detail: "Was it signed by a trusted key?" },
  { label: "Physical", detail: "Does the pack carry its hidden feature?" },
  { label: "Behavior", detail: "Has it acted like one genuine object?" },
];

export function Verify() {
  const [code, setCode] = useState("");
  const navigate = useNavigate();

  const prepared = prepareCode(code);
  const typedSerial = prepared.serial ?? "";
  const showMeter = Boolean(prepared.serial) && typedSerial.length > 0;

  const check = useAction(async () => {
    const outcome = await checkCode(code);
    navigate("/verify/result", { state: outcome });
  });

  return (
    <Container>
      <div className="verify-layout">
        <div className="verify-intro">
          <span className="eyebrow">Verify a product</span>
          <h1 className="page-title">Check the pack in your hand</h1>
          <p className="lede">
            No account needed. Scan or type the code printed on the product to see whether it's
            registered.
          </p>

          <div className="verify-steps-block">
            <p className="eyebrow">What checking does</p>
            <ol className={`verify-steps${check.pending ? " is-checking" : ""}`}>
              {STEPS.map((step, index) => (
                <li key={step.label} className="verify-steps__step">
                  <span className="verify-steps__dot">{index + 1}</span>
                  <span className="verify-steps__text">
                    <span className="verify-steps__label">{step.label}</span>
                    <span className="verify-steps__detail">{step.detail}</span>
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </div>

        <form
          className="verify-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (code.trim() && !check.pending) void check.run();
          }}
        >
          <Field label="Serial or QR code">
            <input
              className="input--code"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder="Paste or type the code from the pack"
              autoComplete="off"
              autoCapitalize="characters"
              spellCheck={false}
              maxLength={512}
              autoFocus
            />
          </Field>

          <div className="verify-meter" aria-live="polite">
            {showMeter && (
              <>
                <span>
                  {typedSerial.length} of {SERIAL_LENGTH}
                </span>
                {!looksLikeSerial(typedSerial) && (
                  <span className="verify-meter__hint">
                    {typedSerial.length < SERIAL_LENGTH ? "Keep going" : "Check for a mistyped character"}
                  </span>
                )}
              </>
            )}
          </div>

          <Button
            type="submit"
            variant="primary"
            className="button--block button--lg"
            disabled={!code.trim()}
            pending={check.pending}
          >
            Check this product
          </Button>

          <InfoNote>
            Checking the same pack more than once is normal and is never treated as suspicious.
            Declining location access never blocks a check.
          </InfoNote>
        </form>
      </div>
    </Container>
  );
}
