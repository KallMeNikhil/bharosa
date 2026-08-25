export const color = {
  ink: "#0B1410",
  inkSoft: "#33453D",
  muted: "#5F7169",
  faint: "#93A29B",

  paper: "#F4F6F1",
  surface: "#FFFFFF",
  line: "#DDE3DA",

  pine: "#123D31",
  pineSoft: "#E4EDE7",

  verdant: "#0F9D63",
  marigold: "#E08715",
  clay: "#C9403D",
  slate: "#5F7169",

  onColor: "#FFFFFF",
} as const;

export const space = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
  huge: 48,
} as const;

export const radius = {
  sm: 8,
  md: 14,
  lg: 22,
  pill: 999,
} as const;

export const font = {
  display: "PlusJakartaSans_800ExtraBold",
  bold: "PlusJakartaSans_700Bold",
  semi: "PlusJakartaSans_600SemiBold",
  medium: "PlusJakartaSans_500Medium",
} as const;

export const type = {
  caption: 13,
  body: 15,
  bodyLarge: 17,
  title: 22,
  headline: 30,
  verdict: 52,
} as const;

export type VerificationState =
  | "GENUINE"
  | "CAUTION"
  | "INVALID"
  | "ALREADY_REPORTED"
  | "UNAVAILABLE";

export interface StatePresentation {
  verdict: string;
  action: string;
  field: string;
  onField: string;
  chip: string;
}

export const STATE: Record<VerificationState, StatePresentation> = {
  GENUINE: {
    verdict: "Registered",
    action: "Nothing unusual in this pack's recent history.",
    field: color.verdant,
    onField: color.onColor,
    chip: color.verdant,
  },
  CAUTION: {
    verdict: "Check first",
    action: "Call the manufacturer's support line before you use this.",
    field: color.marigold,
    onField: color.onColor,
    chip: color.marigold,
  },
  INVALID: {
    verdict: "Not confirmed",
    action: "Call the manufacturer's support line before you use this.",
    field: color.clay,
    onField: color.onColor,
    chip: color.clay,
  },
  ALREADY_REPORTED: {
    verdict: "Reported",
    action: "Someone has already raised this pack with the manufacturer.",
    field: color.clay,
    onField: color.onColor,
    chip: color.clay,
  },
  UNAVAILABLE: {
    verdict: "No answer",
    action: "We could not reach the checking service. Try again shortly.",
    field: color.slate,
    onField: color.onColor,
    chip: color.slate,
  },
};
