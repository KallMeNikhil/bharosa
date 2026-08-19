import { Link } from "react-router-dom";

import { Card } from "../components/ui";

export function NoTenant() {
  return (
    <Card title="No tenant selected">
      <p>
        Internal endpoints answer only for an actor scoped to a manufacturer. Choose one, or
        seed a demonstration tenant, from <Link to="/session">Tenant and actor</Link>.
      </p>
    </Card>
  );
}
