import Svg, { Path } from "react-native-svg";

import { color, font, type } from "../theme";
import { Text, View, StyleSheet } from "react-native";

export function Mark({
  size = 64,
  tint = color.pine,
  accent,
}: {
  size?: number;
  tint?: string;
  accent?: string;
}) {
  const bracket = {
    stroke: tint,
    strokeWidth: 8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    fill: "none",
  };

  return (
    <Svg width={size} height={size} viewBox="0 0 100 100">
      <Path d="M8 32 L8 20 A12 12 0 0 1 20 8 L32 8" {...bracket} />
      <Path d="M68 8 L80 8 A12 12 0 0 1 92 20 L92 32" {...bracket} />
      <Path d="M92 68 L92 80 A12 12 0 0 1 80 92 L68 92" {...bracket} />
      <Path d="M32 92 L20 92 A12 12 0 0 1 8 80 L8 68" {...bracket} />
      <Path
        d="M31 51 L44 64 L69 37"
        stroke={accent ?? tint}
        strokeWidth={10}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </Svg>
  );
}

export function Wordmark({
  size = type.title,
  tint = color.ink,
}: {
  size?: number;
  tint?: string;
}) {
  return <Text style={[styles.wordmark, { fontSize: size, color: tint }]}>Bharosa</Text>;
}

export function Lockup({
  markSize = 34,
  wordSize = type.title,
  tint = color.ink,
  markTint = color.pine,
  accent,
}: {
  markSize?: number;
  wordSize?: number;
  tint?: string;
  markTint?: string;
  accent?: string;
}) {
  return (
    <View style={styles.lockup}>
      <Mark size={markSize} tint={markTint} accent={accent} />
      <Wordmark size={wordSize} tint={tint} />
    </View>
  );
}

const styles = StyleSheet.create({
  lockup: { flexDirection: "row", alignItems: "center", gap: 10 },
  wordmark: {
    fontFamily: font.display,
    letterSpacing: -0.8,
  },
});
