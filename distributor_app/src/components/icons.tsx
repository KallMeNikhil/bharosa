import Svg, { Circle, Path } from "react-native-svg";

import { color, type PackStatus } from "../theme";

export function StatusGlyph({
  status,
  size = 20,
  tint,
}: {
  status: PackStatus;
  size?: number;
  tint: string;
}) {
  const stroke = {
    stroke: tint,
    strokeWidth: 9,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    fill: "none",
  };

  return (
    <Svg width={size} height={size} viewBox="0 0 100 100">
      {status === "known" && <Path d="M22 52 L41 71 L78 32" {...stroke} />}

      {status === "held" && (
        <>
          <Path d="M50 18 L50 60" {...stroke} />
          <Path d="M50 80 L50 80.5" {...stroke} strokeWidth={13} />
        </>
      )}

      {status === "unknown" && (
        <>
          <Path d="M28 28 L72 72" {...stroke} />
          <Path d="M72 28 L28 72" {...stroke} />
        </>
      )}

      {status === "pending" && (
        <>
          <Circle cx={50} cy={50} r={32} {...stroke} strokeDasharray="14 12" />
          <Path d="M50 32 L50 52 L64 60" {...stroke} strokeWidth={8} />
        </>
      )}
    </Svg>
  );
}

export function DirectionIcon({
  direction,
  size = 24,
  tint = color.ledger,
}: {
  direction: "in" | "out" | "flat";
  size?: number;
  tint?: string;
}) {
  const stroke = {
    stroke: tint,
    strokeWidth: 2.2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    fill: "none",
  };

  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      {direction === "in" && (
        <>
          <Path d="M12 3 L12 15" {...stroke} />
          <Path d="M7 10 L12 15 L17 10" {...stroke} />
          <Path d="M4 19 L20 19" {...stroke} />
        </>
      )}
      {direction === "out" && (
        <>
          <Path d="M12 16 L12 4" {...stroke} />
          <Path d="M7 9 L12 4 L17 9" {...stroke} />
          <Path d="M4 20 L20 20" {...stroke} />
        </>
      )}
      {direction === "flat" && (
        <>
          <Path d="M4 7 L20 7" {...stroke} />
          <Path d="M4 13 L20 13" {...stroke} />
          <Path d="M4 19 L14 19" {...stroke} />
        </>
      )}
    </Svg>
  );
}

export function Chevron({ tint = color.faint, size = 18 }: { tint?: string; size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path
        d="M9 5 L16 12 L9 19"
        stroke={tint}
        strokeWidth={2.4}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </Svg>
  );
}

export function OutboxIcon({ tint = color.ledger, size = 24 }: { tint?: string; size?: number }) {
  const stroke = {
    stroke: tint,
    strokeWidth: 2.2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    fill: "none",
  };
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M3 13 L8 13 L9.5 16 L14.5 16 L16 13 L21 13" {...stroke} />
      <Path d="M3 13 L5.5 5 L18.5 5 L21 13 L21 19 L3 19 Z" {...stroke} />
    </Svg>
  );
}

export function KeypadIcon({ tint = color.ledger, size = 24 }: { tint?: string; size?: number }) {
  const stroke = {
    stroke: tint,
    strokeWidth: 2.2,
    strokeLinecap: "round" as const,
    fill: "none",
  };
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M6 8 L6 8.01" {...stroke} strokeWidth={3} />
      <Path d="M12 8 L12 8.01" {...stroke} strokeWidth={3} />
      <Path d="M18 8 L18 8.01" {...stroke} strokeWidth={3} />
      <Path d="M6 13 L6 13.01" {...stroke} strokeWidth={3} />
      <Path d="M12 13 L12 13.01" {...stroke} strokeWidth={3} />
      <Path d="M18 13 L18 13.01" {...stroke} strokeWidth={3} />
      <Path d="M8 18 L16 18" {...stroke} />
    </Svg>
  );
}

export function ScanFrame({ size, tint = "#FFFFFF" }: { size: number; tint?: string }) {
  const stroke = {
    stroke: tint,
    strokeWidth: 3,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    fill: "none",
  };
  return (
    <Svg width={size} height={size} viewBox="0 0 100 100">
      <Path d="M4 26 L4 14 A10 10 0 0 1 14 4 L26 4" {...stroke} />
      <Path d="M74 4 L86 4 A10 10 0 0 1 96 14 L96 26" {...stroke} />
      <Path d="M96 74 L96 86 A10 10 0 0 1 86 96 L74 96" {...stroke} />
      <Path d="M26 96 L14 96 A10 10 0 0 1 4 86 L4 74" {...stroke} />
    </Svg>
  );
}
