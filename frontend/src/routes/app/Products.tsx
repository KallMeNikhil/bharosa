import { useState } from "react";
import { Link } from "react-router-dom";

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
  Mono,
  PageHeader,
  Row,
  Table,
} from "../../components/ui";
import { useAction, useResource } from "../../hooks/useResource";
import { useSession } from "../../session/SessionContext";

export function Products() {
  const { credential, can } = useSession();
  const canProduce = can("CREATE_PRODUCTION_ORDER");

  const products = useResource(() => identity.listProducts(), [credential]);

  const [form, setForm] = useState({ product_ref: "", name: "", gtin: "" });

  const createProduct = useAction(async () => {
    await identity.createProduct({
      product_ref: form.product_ref.trim(),
      name: form.name.trim(),
      gtin: form.gtin.trim() || null,
    });
    setForm({ product_ref: "", name: "", gtin: "" });
    products.reload();
  });

  const rows = products.data ?? [];

  return (
    <>
      <PageHeader
        eyebrow="Products"
        title="Products"
        description="A GTIN is optional, but without one no GS1 Digital Link can be built for that product's identities."
      />

      {!canProduce && (
        <InfoNote>
          This actor does not hold CREATE_PRODUCTION_ORDER, so product creation is disabled. The
          server enforces this independently.
        </InfoNote>
      )}

      <Card title="Register a product">
        <Row>
          <Field label="Product reference">
            <input
              value={form.product_ref}
              onChange={(event) => setForm({ ...form, product_ref: event.target.value })}
              placeholder="URJA-500ML"
            />
          </Field>
          <Field label="Name">
            <input
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              placeholder="Urja 500ml systemic fungicide"
            />
          </Field>
        </Row>
        <Row>
          <Field label="GTIN" hint="14 digits, or leave empty.">
            <input
              value={form.gtin}
              onChange={(event) => setForm({ ...form, gtin: event.target.value })}
              placeholder="09520123456788"
            />
          </Field>
          <Button
            variant="primary"
            disabled={!canProduce || !form.product_ref.trim() || !form.name.trim()}
            pending={createProduct.pending}
            onClick={() => void createProduct.run()}
          >
            Create product
          </Button>
        </Row>
        <ErrorNote>{createProduct.error}</ErrorNote>
      </Card>

      <Card title="Catalogue" actions={<Button onClick={products.reload}>Refresh</Button>} wide>
        <ErrorNote>{products.error}</ErrorNote>
        {products.loading && <Loading />}
        {!products.loading && rows.length === 0 && <Empty>No products yet.</Empty>}
        {rows.length > 0 && (
          <Table
            head={
              <tr>
                <th>Reference</th>
                <th>Name</th>
                <th>GTIN</th>
                <th>Status</th>
                <th />
              </tr>
            }
          >
            {rows.map((product) => (
              <tr key={product.id}>
                <td>{product.product_ref}</td>
                <td>{product.name}</td>
                <td>{product.gtin ? <Mono value={product.gtin} /> : <span className="muted">none</span>}</td>
                <td>
                  <Badge>{product.status}</Badge>
                </td>
                <td>
                  <Link to={`/app/batches?product=${product.id}`}>Batches</Link>
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </>
  );
}
