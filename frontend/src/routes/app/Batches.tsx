import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { identity } from "../../api/endpoints";
import {
  Badge,
  Button,
  Card,
  Empty,
  ErrorNote,
  Field,
  InfoNote,
  Loading,
  PageHeader,
  Row,
  Table,
} from "../../components/ui";
import { useAction, useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";

function today(offsetDays = 0): string {
  return new Date(Date.now() + offsetDays * 86_400_000).toISOString().slice(0, 10);
}

export function Batches() {
  const { credential, can } = useSession();
  const canProduce = can("CREATE_PRODUCTION_ORDER");
  const [searchParams] = useSearchParams();

  const products = useResource(() => identity.listProducts(), [credential]);
  const batches = useResource(() => identity.listBatches(), [credential]);

  const [form, setForm] = useState({
    product_id: searchParams.get("product") ?? "",
    batch_ref: "",
    manufacturing_date: today(-30),
    expiry_date: today(700),
  });

  const createBatch = useAction(async () => {
    await identity.createBatch({
      product_id: form.product_id,
      batch_ref: form.batch_ref.trim(),
      manufacturing_date: form.manufacturing_date,
      expiry_date: form.expiry_date || null,
    });
    setForm({ ...form, batch_ref: "" });
    batches.reload();
  });

  const productRows = products.data ?? [];
  const batchRows = batches.data ?? [];
  const productName = (productId: string) =>
    productRows.find((row) => row.id === productId)?.product_ref ?? productId.slice(0, 8);

  return (
    <>
      <PageHeader
        eyebrow="Products"
        title="Batches"
        description="A batch needs a manufacturing date before anything in it can be signed."
      />

      {!canProduce && (
        <InfoNote>
          This actor does not hold CREATE_PRODUCTION_ORDER, so batch creation is disabled. The
          server enforces this independently.
        </InfoNote>
      )}

      <Card title="Open a batch">
        <Row>
          <Field label="Product">
            <select
              value={form.product_id}
              onChange={(event) => setForm({ ...form, product_id: event.target.value })}
            >
              <option value="">Choose a product</option>
              {productRows.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.product_ref} — {product.name}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Batch reference">
            <input
              value={form.batch_ref}
              onChange={(event) => setForm({ ...form, batch_ref: event.target.value })}
              placeholder="B-2026-04"
            />
          </Field>
        </Row>
        <Row>
          <Field label="Manufactured">
            <input
              type="date"
              value={form.manufacturing_date}
              onChange={(event) => setForm({ ...form, manufacturing_date: event.target.value })}
            />
          </Field>
          <Field label="Expires">
            <input
              type="date"
              value={form.expiry_date}
              onChange={(event) => setForm({ ...form, expiry_date: event.target.value })}
            />
          </Field>
          <Button
            variant="primary"
            disabled={!canProduce || !form.product_id || !form.batch_ref.trim()}
            pending={createBatch.pending}
            onClick={() => void createBatch.run()}
          >
            Open batch
          </Button>
        </Row>
        <ErrorNote>{createBatch.error}</ErrorNote>
      </Card>

      <Card title="Batches" actions={<Button onClick={batches.reload}>Refresh</Button>} wide>
        <ErrorNote>{batches.error}</ErrorNote>
        {batches.loading && <Loading />}
        {!batches.loading && batchRows.length === 0 && <Empty>No batches yet.</Empty>}
        {batchRows.length > 0 && (
          <Table
            head={
              <tr>
                <th>Batch</th>
                <th>Product</th>
                <th>Manufactured</th>
                <th>Expires</th>
                <th>Status</th>
                <th />
              </tr>
            }
          >
            {batchRows.map((batch) => (
              <tr key={batch.id}>
                <td>{batch.batch_ref}</td>
                <td>{productName(batch.product_id)}</td>
                <td>{batch.manufacturing_date ?? <span className="muted">—</span>}</td>
                <td>{batch.expiry_date ?? <span className="muted">—</span>}</td>
                <td>
                  <Badge>{batch.status}</Badge>
                </td>
                <td>
                  <Link to={`/app/identities?batch=${batch.id}`}>Identities</Link>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  );
}
