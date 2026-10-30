import { useCallback } from "react";
import { useNavigate } from "react-router-dom";

import { identity } from "../api/endpoints";
import type { SessionView } from "../api/types";
import { useSession } from "./SessionContext";

// Turns a successful sign-in or registration into a workspace session: the
// capabilities come from the server rather than being assumed.
export function useStartSession() {
  const { update } = useSession();
  const navigate = useNavigate();

  return useCallback(
    async (view: SessionView) => {
      const actor = await identity.me(view.token);
      update({
        token: view.token,
        manufacturerId: view.manufacturer.id,
        manufacturerName: view.manufacturer.name,
        actorId: view.account.email,
        capabilities: actor.capabilities,
      });
      navigate("/app");
    },
    [navigate, update],
  );
}
