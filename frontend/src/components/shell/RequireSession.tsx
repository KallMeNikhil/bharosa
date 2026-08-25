import { Navigate } from "react-router-dom";

import { useSession } from "../../session/SessionContext";
import { WorkspaceShell } from "./WorkspaceShell";

export function RequireSession() {
  const { isConfigured } = useSession();

  if (!isConfigured) {
    return <Navigate to="/app/login" replace />;
  }

  return <WorkspaceShell />;
}
