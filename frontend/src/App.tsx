import { Route, Routes } from "react-router-dom";

import { AuthShell } from "./components/shell/AuthShell";
import { PublicShell } from "./components/shell/PublicShell";
import { RequireSession } from "./components/shell/RequireSession";
import { Batches } from "./routes/app/Batches";
import { CustodyGraph as WsCustodyGraph } from "./routes/app/CustodyGraph";
import { Help } from "./routes/app/Help";
import { IdentityDetail as WsIdentityDetail } from "./routes/app/IdentityDetail";
import { Identities as WsIdentities } from "./routes/app/Identities";
import { IncidentDetail as WsIncidentDetail } from "./routes/app/IncidentDetail";
import { Investigations as WsInvestigations } from "./routes/app/Investigations";
import { Keys as WsKeys } from "./routes/app/Keys";
import { Login } from "./routes/app/Login";
import { Overview } from "./routes/app/Overview";
import { Products } from "./routes/app/Products";
import { Risk } from "./routes/app/Risk";
import { Settings } from "./routes/app/Settings";
import { Simulation as WsSimulation } from "./routes/app/Simulation";
import { SupplyChain } from "./routes/app/SupplyChain";
import { VerificationActivity } from "./routes/app/VerificationActivity";
import { ApiConsole } from "./routes/dev/ApiConsole";
import { Catalogue } from "./routes/dev/Catalogue";
import { CustodyGraph } from "./routes/dev/CustodyGraph";
import { Dashboard } from "./routes/dev/Dashboard";
import { DevLayout } from "./routes/dev/DevLayout";
import { IdentityDetail } from "./routes/dev/IdentityDetail";
import { Identities } from "./routes/dev/Identities";
import { IncidentDetail } from "./routes/dev/IncidentDetail";
import { Investigations } from "./routes/dev/Investigations";
import { Keys } from "./routes/dev/Keys";
import { SessionRoute } from "./routes/dev/SessionRoute";
import { Simulation } from "./routes/dev/Simulation";
import { SupplyChainRoute } from "./routes/dev/SupplyChainRoute";
import { NotFound } from "./routes/NotFound";
import { About } from "./routes/public/About";
import { Contact } from "./routes/public/Contact";
import { Home } from "./routes/public/Home";
import { HowItWorks } from "./routes/public/HowItWorks";
import { LegalPrivacy } from "./routes/public/LegalPrivacy";
import { LegalTerms } from "./routes/public/LegalTerms";
import { Verify } from "./routes/public/Verify";
import { VerifyResult } from "./routes/public/VerifyResult";
import { SessionProvider } from "./session/SessionContext";

function App() {
  return (
    <SessionProvider>
      <Routes>
        <Route element={<PublicShell />}>
          <Route index element={<Home />} />
          <Route path="how-it-works" element={<HowItWorks />} />
          <Route path="about" element={<About />} />
          <Route path="contact" element={<Contact />} />
          <Route path="legal/privacy" element={<LegalPrivacy />} />
          <Route path="legal/terms" element={<LegalTerms />} />
          <Route path="verify" element={<Verify />} />
          <Route path="verify/result" element={<VerifyResult />} />
        </Route>

        <Route element={<AuthShell />}>
          <Route path="app/login" element={<Login />} />
        </Route>

        <Route path="app" element={<RequireSession />}>
          <Route index element={<Overview />} />
          <Route path="products" element={<Products />} />
          <Route path="batches" element={<Batches />} />
          <Route path="identities" element={<WsIdentities />} />
          <Route path="identities/:identityId" element={<WsIdentityDetail />} />
          <Route path="supply-chain" element={<SupplyChain />} />
          <Route path="custody-graph" element={<WsCustodyGraph />} />
          <Route path="verification-activity" element={<VerificationActivity />} />
          <Route path="risk" element={<Risk />} />
          <Route path="investigations" element={<WsInvestigations />} />
          <Route path="investigations/:incidentId" element={<WsIncidentDetail />} />
          <Route path="keys" element={<WsKeys />} />
          <Route path="simulation" element={<WsSimulation />} />
          <Route path="settings" element={<Settings />} />
          <Route path="help" element={<Help />} />
        </Route>

        <Route path="dev" element={<DevLayout />}>
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
          <Route path="simulation" element={<Simulation />} />
          <Route path="console" element={<ApiConsole />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </SessionProvider>
  );
}

export default App;
