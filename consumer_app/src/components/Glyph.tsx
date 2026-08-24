import Svg, { Circle, Path, Rect } from "react-native-svg";

import type { VerificationState } from "../theme";

interface GlyphProps {
  state: VerificationState;
  size?: number;
  color: string;
  strokeWidth?: number;
}

/**
 * The mark that carries the result.
 *
 * Each state has a distinct silhouette, not just a distinct colour, so the
 * answer survives a colour-blind reader, a monochrome screenshot, and a phone
 * with the brightness crushed by direct sun.
 */
export function Glyph({ state, size = 96, color, strokeWidth = 6 }: GlyphProps) {
  const common = {
    stroke: color,
    strokeWidth,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    fill: "none",
  };

  return (
    <Svg width={size} height={size} viewBox="0 0 100 100">
      {state === "GENUINE" && (
        <>
          <Circle cx={50} cy={50} r={38} {...common} />
          <Path d="M32 51 L45 64 L69 38" {...common} />
        </>
      )}

      {state === "CAUTION" && (
        <>
          <Path d="M50 14 L88 78 A6 6 0 0 1 83 87 L17 87 A6 6 0 0 1 12 78 Z" {...common} />
          <Path d="M50 40 L50 60" {...common} />
          <Path d="M50 72 L50 72.5" {...common} strokeWidth={strokeWidth * 1.4} />
        </>
      )}

      {state === "INVALID" && (
        <>
          <Circle cx={50} cy={50} r={38} {...common} />
          <Path d="M36 36 L64 64" {...common} />
          <Path d="M64 36 L36 64" {...common} />
        </>
      )}

      {state === "ALREADY_REPORTED" && (
        <>
          <Path d="M28 88 L28 16" {...common} />
          <Path d="M28 20 L74 20 L64 38 L74 56 L28 56" {...common} />
        </>
      )}

      {state === "UNAVAILABLE" && (
        <>
          <Circle cx={50} cy={50} r={38} {...common} strokeDasharray="10 9" />
          <Path d="M34 50 L66 50" {...common} />
        </>
      )}
    </Svg>
  );
}

/** The viewfinder frame. Corners only, so the pack stays visible inside it. */
export function ScanFrame({ size, color }: { size: number; color: string }) {
  const arm = size * 0.22;
  const inset = 3;
  const far = size - inset;
  const stroke = {
    stroke: color,
    strokeWidth: 5,
    strokeLinecap: "round" as const,
    fill: "none",
  };

  return (
    <Svg width={size} height={size}>
      <Rect
        x={inset}
        y={inset}
        width={far - inset}
        height={far - inset}
        rx={26}
        stroke={color}
        strokeWidth={1.5}
        strokeOpacity={0.35}
        fill="none"
      />
      <Path d={`M${inset} ${inset + arm} L${inset} ${inset + 26} A26 26 0 0 1 ${inset + 26} ${inset} L${inset + arm} ${inset}`} {...stroke} />
      <Path d={`M${far - arm} ${inset} L${far - 26} ${inset} A26 26 0 0 1 ${far} ${inset + 26} L${far} ${inset + arm}`} {...stroke} />
      <Path d={`M${far} ${far - arm} L${far} ${far - 26} A26 26 0 0 1 ${far - 26} ${far} L${far - arm} ${far}`} {...stroke} />
      <Path d={`M${inset + arm} ${far} L${inset + 26} ${far} A26 26 0 0 1 ${inset} ${far - 26} L${inset} ${far - arm}`} {...stroke} />
    </Svg>
  );
}
