import { Link } from "react-router-dom";

import { Badge, Card, Mono, PageHeader } from "../../components/ui";
import { useSession } from "../../session/SessionContext";

export function Settings() {
  const { session } = useSession();

  return (
    <>
      <PageHeader
        eyebrow="Workspace"
        title="Settings"
        description="Organization identity and access."
      />

      <div className="grid-2">
        <Card title="Organization">
          <div className="stack" style={{ gap: "var(--space-2)" }}>
            <div>
              <span className="field__label">Name</span>
              <div>{session.manufacturerName || "\u2014"}</div>
            </div>
            <div>
              <span className="field__label">Manufacturer id</span>
              <div>
                <Mono value={session.manufacturerId} />
              </div>
            </div>
            <div>
              <span className="field__label">Acting as</span>
              <div>{session.actorId || "\u2014"}</div>
            </div>
          </div>
        </Card>

        <Card title="Access">
          <div className="stack" style={{ gap: "var(--space-3)" }}>
            <div className="cluster">
              {session.capabilities.length === 0 && <span className="muted">No capabilities granted.</span>}
              {session.capabilities.map((capability) => (
                <Badge key={capability} tone="info">
                  {capability}
                </Badge>
              ))}
            </div>
            <Link to="/app/keys">Manage signing keys \u2192</Link>
          </div>
        </Card>

        <Card title="Authentication" wide>
          <p className="muted">
            This workspace currently uses development credential resolution as a stand-in for
            authentication \u2014 the server verifies nothing about who you claim to be, but
            capability checks are real and enforced server-side. A production authentication
            provider replaces this in a later milestone.
          </p>
        </Card>
      </div>
    </>
  );
}
