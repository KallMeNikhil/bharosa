import { useState } from "react";

import { identity } from "../api/endpoints";
import { Badge, Button, Card, Empty, ErrorNote, Field, InfoNote, Loading, Mono, Row, Table, Timestamp } from "../components/ui";
import { useAction, useResource } from "../hooks/useResource";
import { rememberKeyHandle } from "../session/keyHandles";
import { useSession } from "../session/SessionContext";
import { NoTenant } from "./NoTenant";

export function Keys() {
  const { credential, isConfigured, can } = useSession();
  const manageKeys = can("MANAGE_KEYS");

  const keys = useResource(() => identity.listKeys(), [credential], { enabled: isConfigured });
  const [keyVersion, setKeyVersion] = useState(1);
  const [reason, setReason] = useState("");

  const issue = useAction(async () => {
    const issued = await identity.createKey(keyVersion);
    rememberKeyHandle(issued.key.id, issued.key_handle);
    setKeyVersion(keyVersion + 1);
    keys.reload();
  });

  const rotate = useAction(async (keyId: string) => {
    const issued = await identity.rotateKey(keyId, reason || undefined);
    rememberKeyHandle(issued.key.id, issued.key_handle);
    keys.reload();
  });

  const revoke = useAction(async (keyId: string) => {
    await identity.revokeKey(keyId, reason || undefined);
    keys.reload();
  });

  const compromise = useAction(async (keyId: string) => {
    await identity.compromiseKey(keyId, reason || undefined);
    keys.reload();
  });

  if (!isConfigured) return <NoTenant />;

  const rows = keys.data ?? [];

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Signing keys</h1>
          <p>
            Only an ACTIVE key can sign. Rotating a key issues its successor and moves the old
            one to ROTATED; marking one compromised makes every pack it signed verify as CAUTION
            rather than silently continuing to pass.
          </p>
        </div>
      </div>

      <Card
        title="Issue a key"
        subtitle="The handle returned here is the only way to sign with the key afterwards. It is kept in this browser so the Identities screen can use it."
      >
        {!manageKeys && (
          <InfoNote>
            This actor does not hold MANAGE_KEYS. The button below is disabled as a courtesy —
            the server would refuse the request regardless.
          </InfoNote>
        )}
        <Row>
          <Field label="Key version">
            <input
              type="number"
              min={1}
              value={keyVersion}
              onChange={(event) => setKeyVersion(Number(event.target.value))}
            />
          </Field>
          <Button
            variant="primary"
            disabled={!manageKeys}
            pending={issue.pending}
            onClick={() => void issue.run()}
          >
            Issue key
          </Button>
        </Row>
        <ErrorNote>{issue.error}</ErrorNote>
      </Card>

      <Card
        title="Key registry"
        actions={<Button onClick={keys.reload}>Refresh</Button>}
        subtitle="A reason is recorded on the key event log for every status change."
      >
        <Field label="Reason for the next status change">
          <input
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Scheduled rotation"
          />
        </Field>

        <ErrorNote>{keys.error ?? rotate.error ?? revoke.error ?? compromise.error}</ErrorNote>
        {keys.loading && <Loading />}
        {!keys.loading && rows.length === 0 && <Empty>No keys issued yet.</Empty>}

        {rows.length > 0 && (
          <Table
            head={
              <tr>
                <th>Version</th>
                <th>Status</th>
                <th>Valid from</th>
                <th>Valid to</th>
                <th>Key id</th>
                <th>Actions</th>
              </tr>
            }
          >
            {rows.map((key) => (
              <tr key={key.id}>
                <td>{key.key_version}</td>
                <td>
                  <Badge>{key.status}</Badge>
                </td>
                <td>
                  <Timestamp value={key.valid_from} />
                </td>
                <td>
                  <Timestamp value={key.valid_to} />
                </td>
                <td>
                  <Mono value={key.id} short />
                </td>
                <td>
                  <div className="button-row">
                    <Button
                      variant="ghost"
                      disabled={!manageKeys || key.status !== "ACTIVE"}
                      onClick={() => void rotate.run(key.id)}
                    >
                      Rotate
                    </Button>
                    <Button
                      variant="ghost"
                      disabled={!manageKeys || key.status === "REVOKED"}
                      onClick={() => void revoke.run(key.id)}
                    >
                      Revoke
                    </Button>
                    <Button
                      variant="ghost"
                      disabled={!manageKeys || key.status === "COMPROMISED"}
                      onClick={() => void compromise.run(key.id)}
                    >
                      Mark compromised
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  );
}
