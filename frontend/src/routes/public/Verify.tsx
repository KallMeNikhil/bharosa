import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { publicSurface } from "../../api/endpoints";
import { Button, Container, ErrorNote, Field, InfoNote, Section } from "../../components/ui";
import { useAction } from "../../hooks/useResource";

export function Verify() {
  const [code, setCode] = useState("");
  const navigate = useNavigate();

  const check = useAction(async () => {
    const trimmed = code.trim();
    let location: { longitude?: number; latitude?: number } = {};
    try {
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        if (!navigator.geolocation) {
          reject(new Error("unavailable"));
          return;
        }
        navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 2500 });
      });
      location = { longitude: position.coords.longitude, latitude: position.coords.latitude };
    } catch {
      location = {};
    }

    const result = await publicSurface.verify({
      ...(trimmed.includes("://") ? { digital_link: trimmed } : { serial: trimmed }),
      ...location,
      channel: "WEB",
    });

    navigate("/verify/result", { state: { result } });
  });

  return (
    <Container>
      <div className="verify-page">
        <div className="stack" style={{ gap: "var(--space-2)" }}>
          <span className="eyebrow">Verify a product</span>
          <h1>Check the pack in your hand</h1>
          <p className="muted">
            No account needed. Scan or type the code printed on the product to see whether it's
            registered.
          </p>
        </div>

        <div>
          <p className="eyebrow" style={{ marginBottom: "var(--space-2)" }}>
            What checking does
          </p>
          <div className="verify-steps">
            {["Code", "Signature", "Physical", "Behavior"].map((step, index) => (
              <span key={step} style={{ display: "flex", alignItems: "center", flex: 1 }}>
                {index > 0 && <span className="verify-steps__link" />}
                <span className="verify-steps__step">
                  <span className="verify-steps__dot">{index + 1}</span>
                  <span className="verify-steps__label">{step}</span>
                </span>
              </span>
            ))}
          </div>
        </div>

        <Field label="Serial or QR code">
          <input
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="Paste or type the code from the pack"
            autoFocus
          />
        </Field>

        <Button
          variant="primary"
          className="button--block"
          disabled={!code.trim()}
          pending={check.pending}
          onClick={() => void check.run()}
        >
          Check this product
        </Button>

        <ErrorNote>{check.error}</ErrorNote>

        <Section tight>
          <InfoNote>
            Checking the same pack more than once is normal and is never treated as suspicious.
            Declining location access never blocks a check.
          </InfoNote>
        </Section>
      </div>
    </Container>
  );
}
