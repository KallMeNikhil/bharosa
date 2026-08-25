import { StyleSheet, Text, View } from "react-native";
import Svg, { Path } from "react-native-svg";

import { color, font, type } from "../theme";

export function Mark({
  size = 64,
  tint = color.ledger,
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
        d="M28 50 L68 50"
        stroke={accent ?? tint}
        strokeWidth={10}
        strokeLinecap="round"
        fill="none"
      />
      <Path
        d="M55 36 L69 50 L55 64"
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
  roleTint = color.muted,
}: {
  size?: number;
  tint?: string;
  roleTint?: string;
}) {
  return (
    <View style={styles.words}>
      <Text style={[styles.wordmark, { fontSize: size, color: tint }]}>Bharosa</Text>
      <Text style={[styles.role, { fontSize: size * 0.86, color: roleTint }]}>
        Consign
      </Text>
    </View>
  );
}

export function Lockup({
  markSize = 30,
  wordSize = type.title,
  tint = color.ink,
  markTint = color.ledger,
  roleTint = color.muted,
  accent,
}: {
  markSize?: number;
  wordSize?: number;
  tint?: string;
  markTint?: string;
  roleTint?: string;
  accent?: string;
}) {
  return (
    <View style={styles.lockup}>
      <Mark size={markSize} tint={markTint} accent={accent} />
      <Wordmark size={wordSize} tint={tint} roleTint={roleTint} />
    </View>
  );
}

const styles = StyleSheet.create({
  lockup: { flexDirection: "row", alignItems: "center", gap: 10 },
  words: { flexDirection: "row", alignItems: "baseline", gap: 6 },
  wordmark: { fontFamily: font.display, letterSpacing: -0.6 },
  role: { fontFamily: font.regular, letterSpacing: -0.2 },
});
