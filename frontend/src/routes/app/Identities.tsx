import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { identity } from "../../api/endpoints";
import { LIFECYCLE_PATH } from "../../api/types";
import { LifecycleTrack } from "../../components/LifecycleTrack";
import { Button, Card, Empty, ErrorNote, Field, InfoNote, Loading, Mono, PageHeader, Row, Table, Timestamp } from "../../components/ui";
import { useAction, useResource } from "../../hooks/useResource";
import { recallKeyHandle } from "../../session/keyHandles";
import { useSession } from "../../session/SessionContext";

export function Identities() {
  const { credential, can } = useSession();
  const [searchParams, setSearchParams] = useSearchParams();
  const batchFilter = searchParams.get("batch") ?? "";

  const batches = useResource(() => identity.listBatches(), [credential]);
  const identities = useResource(
    () => identity.listIdentities({ batchId: batchFilter || undefined, limit: 200 }),
    [credential, batchFilter],
  );
  const keys = useResource(() => identity.listKeys(), [credential]);

  const [count, setCount] = useState(3);
  const [reserveBatch, setReserveBatch] = useState("");
  const [signingKeyId, setSigningKeyId] = useState("");
  const [keyHandle, setKeyHandle] = useState("");

  const reserve = useAction(async () => {
    await identity.reserveIdentities(reserveBatch, count);
    identities.reload();
  });

  const issueAll = useAction(async () => {
    const rows = identities.data ?? [];
    for (const row of rows) {
      let state = row.lifecycle_state;
      if (state === "RESERVED") {
        await identity.signIdentity(row.id, {
          manufacturer_key_id: signingKeyId,
          key_handle: keyHandle,
        });
        state = "SIGNED";
      }
      const remaining = LIFECYCLE_PATH.slice(LIFECYCLE_PATH.indexOf(state) + 1);
      for (const next of remaining) {
        await identity.transitionIdentity(row.id, next);
      }
    }
    identities.reload();
  });

  const rows = identities.data ?? [];
  const activeKeys = (keys.data ?? []).filter((key) => key.status === "ACTIVE");
  const advanceable = rows.filter((row) => row.lifecycle_state !== "ACTIVATED" && row.lifecycle_state !== "PRINT_REJECTED");

  return (
    <>
      <PageHeader
        eyebrow="Products"
        title="Identities"
        description="Serials are never supplied by a caller. Reservation asks only for a count, and the server generates 128 bits of randomness per pack."
      />

      <div className="grid-2">
        <Card title="Reserve identities">
          {!can("CREATE_PRODUCTION_ORDER") && (
            <InfoNote>This actor does not hold CREATE_PRODUCTION_ORDER.</InfoNote>
          )}
          <Row>
            <Field label="Batch">
              <select
                value={reserveBatch}
                onChange={(event) => setReserveBatch(event.target.value)}
              >
                <option value="">Choose a batch</option>
                {(batches.data ?? []).map((batch) => (
                  <option key={batch.id} value={batch.id}>
                    {batch.batch_ref}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Count">
              <input
                type="number"
                min={1}
                max={1000}
                value={count}
                onChange={(event) => setCount(Number(event.target.value))}
              />
            </Field>
            <Button
              variant="primary"
              disabled={!can("CREATE_PRODUCTION_ORDER") || !reserveBatch}
              pending={reserve.pending}
              onClick={() => void reserve.run()}
            >
              Reserve
            </Button>
          </Row>
          <ErrorNote>{reserve.error}</ErrorNote>
        </Card>

        <Card
          title="Run the issuance pipeline"
          subtitle="Signs, prints, verifies, reconciles and activates every listed identity that is not already finished. Signing and print authority are separate capabilities, and this walks through both."
        >
          <Row>
            <Field label="Signing key">
              <select
                value={signingKeyId}
                onChange={(event) => {
                  setSigningKeyId(event.target.value);
                  setKeyHandle(recallKeyHandle(event.target.value));
                }}
              >
                <option value="">Choose an ACTIVE key</option>
                {activeKeys.map((key) => (
                  <option key={key.id} value={key.id}>
                    version {key.key_version}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Key handle" hint="Remembered from when the key was issued in this browser.">
              <input
                value={keyHandle}
                onChange={(event) => setKeyHandle(event.target.value)}
                placeholder="handle returned by POST /keys"
              />
            </Field>
          </Row>
          <Button
            variant="primary"
            disabled={!signingKeyId || !keyHandle || advanceable.length === 0}
            pending={issueAll.pending}
            onClick={() => void issueAll.run()}
          >
            Advance {advanceable.length} identities to ACTIVATED
          </Button>
          <ErrorNote>{issueAll.error}</ErrorNote>
        </Card>
      </div>

      <Card
        title="Identity register"
        actions={<Button onClick={identities.reload}>Refresh</Button>}
      >
        <Row>
          <Field label="Filter by batch">
            <select
              value={batchFilter}
              onChange={(event) => {
                const value = event.target.value;
                setSearchParams(value ? { batch: value } : {});
              }}
            >
              <option value="">Every batch</option>
              {(batches.data ?? []).map((batch) => (
                <option key={batch.id} value={batch.id}>
                  {batch.batch_ref}
                </option>
              ))}
            </select>
          </Field>
        </Row>

        <ErrorNote>{identities.error}</ErrorNote>
        {identities.loading && <Loading />}
        {!identities.loading && rows.length === 0 && <Empty>No identities match.</Empty>}

        {rows.length > 0 && (
          <Table
            head={
              <tr>
                <th>Serial</th>
                <th>State</th>
                <th>Signed</th>
                <th>Activated</th>
                <th />
              </tr>
            }
          >
            {rows.map((row) => (
              <tr key={row.id}>
                <td>
                  <Mono value={row.serial} />
                </td>
                <td>
                  <LifecycleTrack state={row.lifecycle_state} />
                </td>
                <td>
                  <Timestamp value={row.signed_at} />
                </td>
                <td>
                  <Timestamp value={row.activated_at} />
                </td>
                <td>
                  <Link to={`/app/identities/${row.id}`}>Open</Link>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  );
}
