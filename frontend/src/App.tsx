import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ApiConsole } from "./routes/ApiConsole";
import { Catalogue } from "./routes/Catalogue";
import { CustodyGraph } from "./routes/CustodyGraph";
import { Dashboard } from "./routes/Dashboard";
import { IdentityDetail } from "./routes/IdentityDetail";
import { Identities } from "./routes/Identities";
import { IncidentDetail } from "./routes/IncidentDetail";
import { Investigations } from "./routes/Investigations";
import { Keys } from "./routes/Keys";
import { SessionRoute } from "./routes/SessionRoute";
import { SupplyChainRoute } from "./routes/SupplyChainRoute";
import { Verify } from "./routes/Verify";
import { SessionProvider } from "./session/SessionContext";

function App() {
  return (
    <SessionProvider>
      <Routes>
        <Route path="/verify" element={<Verify />} />
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="session" element={<SessionRoute />} />
          <Route path="keys" element={<Keys />} />
          <Route path="catalogue" element={<Catalogue />} />
          <Route path="identities" element={<Identities />} />
          <Route path="identities/:identityId" element={<IdentityDetail />} />
          <Route path="supply-chain" element={<SupplyChainRoute />} />
          <Route path="custody-graph" element={<CustodyGraph />} />
          <Route path="investigations" element={<Investigations />} />
          <Route path="investigations/:incidentId" element={<IncidentDetail />} />
          <Route path="console" element={<ApiConsole />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </SessionProvider>
  );
}

export default App;
