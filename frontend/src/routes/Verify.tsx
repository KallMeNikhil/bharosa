import { useState } from "react";
import { Link } from "react-router-dom";

import { publicSurface } from "../api/endpoints";
import { VERIFICATION_CHANNELS } from "../api/types";
import type { VerificationChannel, VerifyResponse } from "../api/types";
import { Button, ErrorNote, Field, InfoNote, Row, toneFor } from "../components/ui";
import { useAction } from "../hooks/useResource";

const HEADLINE: Record<string, string> = {
  GENUINE: "Registered",
  CAUTION: "Check before you use this",
  INVALID: "Could not be confirmed",
  ALREADY_REPORTED: "Already reported",
  UNAVAILABLE: "Cannot check right now",
};

export function Verify() {
  const [code, setCode] = useState("");
  const [channel, setChannel] = useState<VerificationChannel>("WEB");
  const [longitude, setLongitude] = useState("");
  const [latitude, setLatitude] = useState("");
  const [result, setResult] = useState<VerifyResponse | null>(null);

  const check = useAction(async () => {
    const trimmed = code.trim();
    const location =
      longitude && latitude
        ? { longitude: Number(longitude), latitude: Number(latitude) }
        : {};
    setResult(
      await publicSurface.verify({
        ...(trimmed.includes("://") ? { digital_link: trimmed } : { serial: trimmed }),
        ...location,
        channel,
      }),
    );
  });

  const useBrowserLocation = () => {
    navigator.geolocation?.getCurrentPosition((position) => {
      setLongitude(position.coords.longitude.toFixed(4));
      setLatitude(position.coords.latitude.toFixed(4));
    });
  };

  return (
    <div className="verify-page">
      <div>
        <h1>Check a pack</h1>
        <p className="empty">
          This is the public surface. It needs no account, runs under a database role that can
          read almost nothing, and answers in the same shape every time.
        </p>
      </div>

      <Field label="Serial or GS1 Digital Link">
        <input
          value={code}
          onChange={(event) => setCode(event.target.value)}
          placeholder="Paste the code from the pack"
        />
      </Field>

      <Row>
        <Field label="Longitude">
          <input
            value={longitude}
            onChange={(event) => setLongitude(event.target.value)}
            placeholder="optional"
          />
        </Field>
        <Field label="Latitude">
          <input
            value={latitude}
            onChange={(event) => setLatitude(event.target.value)}
            placeholder="optional"
          />
        </Field>
        <Button onClick={useBrowserLocation}>Use my location</Button>
      </Row>

      <Row>
        <Field label="Channel">
          <select
            value={channel}
            onChange={(event) => setChannel(event.target.value as VerificationChannel)}
          >
            {VERIFICATION_CHANNELS.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </Field>
        <Button
          variant="primary"
          disabled={!code.trim()}
          pending={check.pending}
          onClick={() => void check.run()}
        >
          Check
        </Button>
      </Row>

      <ErrorNote>{check.error}</ErrorNote>

      {result && (
        <div className={`verify-result verify-result--${toneFor(result.state)}`}>
          <span className="verify-result__state">{HEADLINE[result.state] ?? result.state}</span>
          <p className="verify-result__message">{result.message}</p>
          <span className="verify-result__meta">
            Checked {new Date(result.checked_at).toLocaleString()}
          </span>
        </div>
      )}

      <InfoNote>
        Declining location never blocks a check. Checking the same pack several times is normal
        and is not treated as suspicious. A registered pack means the code verified and nothing
        has been flagged against it — it is not a guarantee about the contents of the bottle in
        your hand.
      </InfoNote>

      <Link to="/">Back to the manufacturer console</Link>
    </div>
  );
}
