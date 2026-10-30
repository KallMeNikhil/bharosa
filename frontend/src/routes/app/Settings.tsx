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
          <div className="detail-list">
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
          <div className="stack stack--md">
            <div className="cluster">
              {session.capabilities.length === 0 && <span className="muted">No capabilities granted.</span>}
              {session.capabilities.map((capability) => (
                <Badge key={capability} tone="info">
                  {capability}
                </Badge>
              ))}
            </div>
            <Link to="/app/keys">Manage signing keys →</Link>
          </div>
        </Card>

        <Card title="Authentication" wide>
          <p className="muted">
            {session.token
              ? "You are signed in with your account. Each session lasts two weeks, and signing out ends it on the server as well as on this device. Every capability check is enforced server-side."
              : "This development session acts as a manufacturer without an account. Development sessions are refused by the public deployment."}
          </p>
        </Card>
      </div>
    </>
  );
}
