import { useCallback } from "react";
import { useNavigate } from "react-router-dom";

import { identity } from "../api/endpoints";
import type { SessionView } from "../api/types";
import { useSession } from "./SessionContext";

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
