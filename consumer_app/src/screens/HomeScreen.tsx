import Svg, { Path } from "react-native-svg";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Glyph } from "../components/Glyph";
import { Lockup } from "../components/Logo";
import { Serial } from "../components/ui";
import { groupSerial } from "../lib/code";
import type { HistoryEntry } from "../lib/history";
import { STATE, color, font, radius, space, type } from "../theme";

interface HomeScreenProps {
  history: HistoryEntry[];
  onScan: () => void;
  onManualEntry: () => void;
  onHistory: () => void;
  onHelp: () => void;
}

function Chevron({ tint }: { tint: string }) {
  return (
    <Svg width={18} height={18} viewBox="0 0 24 24">
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

function ScanIcon({ tint, size = 30 }: { tint: string; size?: number }) {
  const stroke = {
    stroke: tint,
    strokeWidth: 2.2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    fill: "none",
  };
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M3 8 L3 5.5 A2.5 2.5 0 0 1 5.5 3 L8 3" {...stroke} />
      <Path d="M16 3 L18.5 3 A2.5 2.5 0 0 1 21 5.5 L21 8" {...stroke} />
      <Path d="M21 16 L21 18.5 A2.5 2.5 0 0 1 18.5 21 L16 21" {...stroke} />
      <Path d="M8 21 L5.5 21 A2.5 2.5 0 0 1 3 18.5 L3 16" {...stroke} />
      <Path d="M3.5 12 L20.5 12" {...stroke} />
    </Svg>
  );
}

function KeypadIcon({ tint, size = 24 }: { tint: string; size?: number }) {
  const stroke = { stroke: tint, strokeWidth: 2.2, strokeLinecap: "round" as const, fill: "none" };
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

function ListIcon({ tint, size = 24 }: { tint: string; size?: number }) {
  const stroke = { stroke: tint, strokeWidth: 2.2, strokeLinecap: "round" as const, fill: "none" };
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M4 7 L4 7.01" {...stroke} strokeWidth={3} />
      <Path d="M4 12 L4 12.01" {...stroke} strokeWidth={3} />
      <Path d="M4 17 L4 17.01" {...stroke} strokeWidth={3} />
      <Path d="M9 7 L20 7" {...stroke} />
      <Path d="M9 12 L20 12" {...stroke} />
      <Path d="M9 17 L16 17" {...stroke} />
    </Svg>
  );
}

function HelpIcon({ tint, size = 24 }: { tint: string; size?: number }) {
  const stroke = { stroke: tint, strokeWidth: 2.2, strokeLinecap: "round" as const, fill: "none" };
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M12 3 A9 9 0 1 1 11.99 3" {...stroke} />
      <Path d="M9.4 9.2 A2.7 2.7 0 1 1 12 12.6 L12 14.2" {...stroke} />
      <Path d="M12 17.6 L12 17.61" {...stroke} strokeWidth={3} />
    </Svg>
  );
}

function OptionRow({
  icon,
  title,
  detail,
  onPress,
}: {
  icon: React.ReactNode;
  title: string;
  detail: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
    >
      <View style={styles.rowIcon}>{icon}</View>
      <View style={styles.rowBody}>
        <Text style={styles.rowTitle}>{title}</Text>
        <Text style={styles.rowDetail}>{detail}</Text>
      </View>
      <Chevron tint={color.faint} />
    </Pressable>
  );
}

export function HomeScreen({
  history,
  onScan,
  onManualEntry,
  onHistory,
  onHelp,
}: HomeScreenProps) {
  const insets = useSafeAreaInsets();
  const last = history[0];

  return (
    <View style={styles.root}>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + space.lg, paddingBottom: insets.bottom + space.xxl },
        ]}
      >
        <View style={styles.header}>
          <Lockup markSize={30} wordSize={type.title} />
          <Text style={styles.greeting}>Check a pack before you use it</Text>
        </View>

        <Pressable
          accessibilityRole="button"
          onPress={onScan}
          style={({ pressed }) => [styles.hero, pressed && styles.heroPressed]}
        >
          <View style={styles.heroIcon}>
            <ScanIcon tint={color.onColor} size={34} />
          </View>
          <View style={styles.heroBody}>
            <Text style={styles.heroTitle}>Scan the code</Text>
            <Text style={styles.heroDetail}>
              Point the camera at the QR square printed on the pack
            </Text>
          </View>
          <Chevron tint="rgba(255,255,255,0.7)" />
        </Pressable>

        <View style={styles.group}>
          <OptionRow
            icon={<KeypadIcon tint={color.pine} />}
            title="Enter the code"
            detail="For a torn or unreadable label"
            onPress={onManualEntry}
          />
          <View style={styles.divider} />
          <OptionRow
            icon={<ListIcon tint={color.pine} />}
            title="Packs you checked"
            detail={
              history.length === 0
                ? "Nothing checked yet"
                : `${history.length} on this phone`
            }
            onPress={onHistory}
          />
          <View style={styles.divider} />
          <OptionRow
            icon={<HelpIcon tint={color.pine} />}
            title="What the results mean"
            detail="Registered, Check first, Not confirmed"
            onPress={onHelp}
          />
        </View>

        {last && (
          <Pressable
            accessibilityRole="button"
            onPress={onHistory}
            style={({ pressed }) => [styles.lastCard, pressed && styles.rowPressed]}
          >
            <Text style={styles.lastLabel}>Last checked</Text>
            <View style={styles.lastBody}>
              <View
                style={[styles.lastGlyph, { backgroundColor: STATE[last.state].chip }]}
              >
                <Glyph state={last.state} color={color.onColor} size={22} strokeWidth={9} />
              </View>
              <View style={styles.lastText}>
                <Serial value={groupSerial(last.serial)} tint={color.ink} />
                <Text style={styles.lastVerdict}>
                  {STATE[last.state].verdict} ·{" "}
                  {new Date(last.checkedAt).toLocaleDateString()}
                </Text>
              </View>
            </View>
          </Pressable>
        )}

        <Text style={styles.footnote}>
          Bharosa checks whether a code is registered and how it has behaved since
          it was made. It does not test what is inside the bottle.
        </Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.paper },
  content: { paddingHorizontal: space.xl, gap: space.xl },
  header: { gap: space.md },
  greeting: {
    fontFamily: font.display,
    fontSize: 27,
    lineHeight: 33,
    letterSpacing: -0.7,
    color: color.ink,
    maxWidth: 300,
  },
  hero: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.lg,
    backgroundColor: color.pine,
    borderRadius: radius.lg,
    padding: space.lg + 2,
  },
  heroPressed: { opacity: 0.92, transform: [{ scale: 0.995 }] },
  heroIcon: {
    width: 56,
    height: 56,
    borderRadius: radius.md,
    backgroundColor: "rgba(255,255,255,0.14)",
    alignItems: "center",
    justifyContent: "center",
  },
  heroBody: { flex: 1, gap: 3 },
  heroTitle: {
    fontFamily: font.bold,
    fontSize: type.title,
    color: color.onColor,
    letterSpacing: -0.3,
  },
  heroDetail: {
    fontFamily: font.medium,
    fontSize: type.caption,
    lineHeight: 19,
    color: "rgba(255,255,255,0.75)",
  },
  group: {
    backgroundColor: color.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: color.line,
    overflow: "hidden",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.lg,
    paddingHorizontal: space.lg,
    paddingVertical: space.lg,
    minHeight: 74,
  },
  rowPressed: { backgroundColor: color.pineSoft },
  rowIcon: {
    width: 42,
    height: 42,
    borderRadius: radius.sm,
    backgroundColor: color.pineSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  rowBody: { flex: 1, gap: 2 },
  rowTitle: {
    fontFamily: font.bold,
    fontSize: type.bodyLarge,
    color: color.ink,
  },
  rowDetail: {
    fontFamily: font.medium,
    fontSize: type.caption,
    color: color.muted,
  },
  divider: { height: 1, backgroundColor: color.line, marginLeft: 74 },
  lastCard: {
    backgroundColor: color.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: color.line,
    padding: space.lg,
    gap: space.md,
  },
  lastLabel: {
    fontFamily: font.bold,
    fontSize: 10.5,
    letterSpacing: 1.4,
    textTransform: "uppercase",
    color: color.faint,
  },
  lastBody: { flexDirection: "row", alignItems: "center", gap: space.md },
  lastGlyph: {
    width: 38,
    height: 38,
    borderRadius: radius.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  lastText: { flex: 1, gap: 2 },
  lastVerdict: {
    fontFamily: font.semi,
    fontSize: type.caption,
    color: color.muted,
  },
  footnote: {
    fontFamily: font.medium,
    fontSize: type.caption,
    lineHeight: 19,
    color: color.faint,
    textAlign: "center",
    paddingHorizontal: space.sm,
  },
});
