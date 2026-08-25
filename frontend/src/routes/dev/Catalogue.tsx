import { useState } from "react";
import { Link } from "react-router-dom";

import { identity } from "../../api/endpoints";
import { Badge, Button, Card, Empty, ErrorNote, Field, InfoNote, Loading, Mono, Row, Table } from "../../components/ui";
import { useAction, useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";
import { NoTenant } from "./NoTenant";

function today(offsetDays = 0): string {
  return new Date(Date.now() + offsetDays * 86_400_000).toISOString().slice(0, 10);
}

export function Catalogue() {
  const { credential, isConfigured, can } = useSession();
  const canProduce = can("CREATE_PRODUCTION_ORDER");

  const products = useResource(() => identity.listProducts(), [credential], {
    enabled: isConfigured,
  });
  const batches = useResource(() => identity.listBatches(), [credential], {
    enabled: isConfigured,
  });

  const [productForm, setProductForm] = useState({
    product_ref: "",
    name: "",
    gtin: "",
  });
  const [batchForm, setBatchForm] = useState({
    product_id: "",
    batch_ref: "",
    manufacturing_date: today(-30),
    expiry_date: today(700),
  });

  const createProduct = useAction(async () => {
    await identity.createProduct({
      product_ref: productForm.product_ref.trim(),
      name: productForm.name.trim(),
      gtin: productForm.gtin.trim() || null,
    });
    setProductForm({ product_ref: "", name: "", gtin: "" });
    products.reload();
  });

  const createBatch = useAction(async () => {
    await identity.createBatch({
      product_id: batchForm.product_id,
      batch_ref: batchForm.batch_ref.trim(),
      manufacturing_date: batchForm.manufacturing_date,
      expiry_date: batchForm.expiry_date || null,
    });
    setBatchForm({ ...batchForm, batch_ref: "" });
    batches.reload();
  });

  if (!isConfigured) return <NoTenant />;

  const productRows = products.data ?? [];
  const batchRows = batches.data ?? [];
  const productName = (productId: string) =>
    productRows.find((row) => row.id === productId)?.product_ref ?? productId.slice(0, 8);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Products and batches</h1>
          <p>
            A GTIN is optional, but without one no GS1 Digital Link can be built for that
            product&apos;s identities. A batch needs a manufacturing date before anything in it
            can be signed.
          </p>
        </div>
      </div>

      {!canProduce && (
        <InfoNote>
          This actor does not hold CREATE_PRODUCTION_ORDER, so the creation forms are disabled.
          The server enforces this independently.
        </InfoNote>
      )}

      <div className="grid-2">
        <Card title="Register a product">
          <Row>
            <Field label="Product reference">
              <input
                value={productForm.product_ref}
                onChange={(event) =>
                  setProductForm({ ...productForm, product_ref: event.target.value })
                }
                placeholder="URJA-500ML"
              />
            </Field>
          </Row>
          <Row>
            <Field label="Name">
              <input
                value={productForm.name}
                onChange={(event) => setProductForm({ ...productForm, name: event.target.value })}
                placeholder="Urja 500ml systemic fungicide"
              />
            </Field>
          </Row>
          <Row>
            <Field label="GTIN" hint="14 digits, or leave empty.">
              <input
                value={productForm.gtin}
                onChange={(event) => setProductForm({ ...productForm, gtin: event.target.value })}
                placeholder="09520123456788"
              />
            </Field>
            <Button
              variant="primary"
              disabled={!canProduce || !productForm.product_ref.trim() || !productForm.name.trim()}
              pending={createProduct.pending}
              onClick={() => void createProduct.run()}
            >
              Create product
            </Button>
          </Row>
          <ErrorNote>{createProduct.error}</ErrorNote>
        </Card>

        <Card title="Open a batch">
          <Row>
            <Field label="Product">
              <select
                value={batchForm.product_id}
                onChange={(event) =>
                  setBatchForm({ ...batchForm, product_id: event.target.value })
                }
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
                value={batchForm.batch_ref}
                onChange={(event) => setBatchForm({ ...batchForm, batch_ref: event.target.value })}
                placeholder="B-2026-04"
              />
            </Field>
          </Row>
          <Row>
            <Field label="Manufactured">
              <input
                type="date"
                value={batchForm.manufacturing_date}
                onChange={(event) =>
                  setBatchForm({ ...batchForm, manufacturing_date: event.target.value })
                }
              />
            </Field>
            <Field label="Expires">
              <input
                type="date"
                value={batchForm.expiry_date}
                onChange={(event) =>
                  setBatchForm({ ...batchForm, expiry_date: event.target.value })
                }
              />
            </Field>
            <Button
              variant="primary"
              disabled={!canProduce || !batchForm.product_id || !batchForm.batch_ref.trim()}
              pending={createBatch.pending}
              onClick={() => void createBatch.run()}
            >
              Open batch
            </Button>
          </Row>
          <ErrorNote>{createBatch.error}</ErrorNote>
        </Card>

        <Card title="Products" actions={<Button onClick={products.reload}>Refresh</Button>} wide>
          <ErrorNote>{products.error}</ErrorNote>
          {products.loading && <Loading />}
          {!products.loading && productRows.length === 0 && <Empty>No products yet.</Empty>}
          {productRows.length > 0 && (
            <Table
              head={
                <tr>
                  <th>Reference</th>
                  <th>Name</th>
                  <th>GTIN</th>
                  <th>Status</th>
                </tr>
              }
            >
              {productRows.map((product) => (
                <tr key={product.id}>
                  <td>{product.product_ref}</td>
                  <td>{product.name}</td>
                  <td>
                    {product.gtin ? <Mono value={product.gtin} /> : <span className="muted">none</span>}
                  </td>
                  <td>
                    <Badge>{product.status}</Badge>
                  </td>
                </tr>
              ))}
            </Table>
          )}
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
                    <Link to={`/identities?batch=${batch.id}`}>Identities</Link>
                  </td>
                </tr>
              ))}
            </Table>
          )}
        </Card>
      </div>
    </>
  );
}
