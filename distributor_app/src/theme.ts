export const color = {
  ink: "#101A1E",
  inkSoft: "#34464D",
  muted: "#5E7178",
  faint: "#93A5AB",

  docket: "#E8EDEE",
  surface: "#FFFFFF",
  rule: "#D3DCDE",
  ruleSoft: "#E5EBEC",

  ledger: "#0E3A45",
  ledgerSoft: "#DBE7EA",
  ledgerLine: "#C3D6DB",

  verdant: "#0F9D63",
  marigold: "#E08715",
  clay: "#C9403D",
  slate: "#5E7178",

  onColor: "#FFFFFF",
} as const;

export const space = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  huge: 44,
} as const;

export const radius = {
  sm: 6,
  md: 12,
  lg: 18,
  pill: 999,
} as const;

export const font = {
  display: "IBMPlexSans_700Bold",
  semi: "IBMPlexSans_600SemiBold",
  medium: "IBMPlexSans_500Medium",
  regular: "IBMPlexSans_400Regular",
  mono: "IBMPlexMono_500Medium",
  monoBold: "IBMPlexMono_600SemiBold",
  monoRegular: "IBMPlexMono_400Regular",
} as const;

export const type = {
  micro: 11,
  caption: 13,
  body: 15,
  bodyLarge: 17,
  title: 21,
  headline: 28,
  tally: 46,
} as const;

export type MovementKind =
  | "RECEIPT"
  | "DISPATCH"
  | "TRANSFER"
  | "RETURN"
  | "RETAIL_PLACEMENT";

export interface MovementPresentation {
  label: string;
  running: string;
  detail: string;
  counterparty: string | null;
  needs: "source" | "destination" | "none";
  direction: "in" | "out" | "flat";
}

export const MOVEMENT: Record<MovementKind, MovementPresentation> = {
  RECEIPT: {
    label: "Receive stock",
    running: "Receiving",
    detail: "A load has arrived and you are taking it in",
    counterparty: "Received from",
    needs: "source",
    direction: "in",
  },
  DISPATCH: {
    label: "Send stock out",
    running: "Sending",
    detail: "A load is leaving for somewhere else",
    counterparty: "Sending to",
    needs: "destination",
    direction: "out",
  },
  RETAIL_PLACEMENT: {
    label: "Put on the shelf",
    running: "Shelving",
    detail: "Stock is going out for sale here",
    counterparty: null,
    needs: "none",
    direction: "flat",
  },
  TRANSFER: {
    label: "Move between our places",
    running: "Moving",
    detail: "Stock is going to another of your own locations",
    counterparty: "Moving to",
    needs: "destination",
    direction: "out",
  },
  RETURN: {
    label: "Send back",
    running: "Returning",
    detail: "Stock is going back where it came from",
    counterparty: "Returning to",
    needs: "destination",
    direction: "out",
  },
};

export const MOVEMENT_ORDER: MovementKind[] = [
  "RECEIPT",
  "DISPATCH",
  "RETAIL_PLACEMENT",
  "TRANSFER",
  "RETURN",
];

export type PackStatus = "known" | "held" | "unknown" | "pending";

export interface PackPresentation {
  label: string;
  detail: string;
  tint: string;
}

export const PACK: Record<PackStatus, PackPresentation> = {
  known: {
    label: "On record",
    detail: "This pack is registered and where the record expects it to be.",
    tint: color.verdant,
  },
  held: {
    label: "Held elsewhere",
    detail:
      "The record says someone else has this pack. It will still be recorded, and the mismatch is worth a word with your supervisor.",
    tint: color.marigold,
  },
  unknown: {
    label: "Not on record",
    detail:
      "No pack with this code is registered. Set it aside and tell your supervisor before it goes any further.",
    tint: color.clay,
  },
  pending: {
    label: "Not checked yet",
    detail: "The device is offline. This pack will be checked when it sends.",
    tint: color.slate,
  },
};
