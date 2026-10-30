import type { IconName } from "../icons";

export interface NavLinkItem {
  to: string;
  label: string;
  icon: IconName;
  end?: boolean;
}

export interface NavGroup {
  label: string;
  links: NavLinkItem[];
}

export const NAV_GROUPS: NavGroup[] = [
  { label: "Overview", links: [{ to: "/app", label: "Overview", icon: "overview", end: true }] },
  {
    label: "Products",
    links: [
      { to: "/app/products", label: "Products", icon: "product" },
      { to: "/app/batches", label: "Batches", icon: "batch" },
      { to: "/app/identities", label: "Identities", icon: "identity" },
    ],
  },
  {
    label: "Supply chain",
    links: [
      { to: "/app/supply-chain", label: "Supply chain", icon: "supply" },
      { to: "/app/custody-graph", label: "Custody graph", icon: "graph" },
    ],
  },
  {
    label: "Trust & verification",
    links: [{ to: "/app/verification-activity", label: "Verification activity", icon: "verify" }],
  },
  {
    label: "Intelligence",
    links: [
      { to: "/app/risk", label: "Risk", icon: "risk" },
      { to: "/app/investigations", label: "Investigations", icon: "investigate" },
    ],
  },
  { label: "Simulation", links: [{ to: "/app/simulation", label: "Simulation", icon: "simulation" }] },
  {
    label: "Settings",
    links: [
      { to: "/app/settings", label: "Settings", icon: "settings" },
      { to: "/app/keys", label: "Signing keys", icon: "key" },
      { to: "/app/help", label: "Help", icon: "help" },
    ],
  },
];

export const ALL_LINKS: (NavLinkItem & { group: string })[] = NAV_GROUPS.flatMap((group) =>
  group.links.map((link) => ({ ...link, group: group.label })),
);

export const BOTTOM_LINKS: NavLinkItem[] = [
  { to: "/app", label: "Overview", icon: "overview", end: true },
  { to: "/app/products", label: "Products", icon: "product" },
  { to: "/app/supply-chain", label: "Supply chain", icon: "supply" },
  { to: "/app/risk", label: "Intelligence", icon: "risk" },
];

export const MORE_LINKS: NavLinkItem[] = [
  { to: "/app/verification-activity", label: "Verification activity", icon: "verify" },
  { to: "/app/investigations", label: "Investigations", icon: "investigate" },
  { to: "/app/custody-graph", label: "Custody graph", icon: "graph" },
  { to: "/app/simulation", label: "Simulation", icon: "simulation" },
  { to: "/app/settings", label: "Settings", icon: "settings" },
  { to: "/app/keys", label: "Signing keys", icon: "key" },
  { to: "/app/help", label: "Help", icon: "help" },
];
