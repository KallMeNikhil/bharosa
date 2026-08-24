import { useEffect, useRef } from "react";
import { Animated, Easing, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { StatusGlyph } from "../components/icons";
import { Button, Eyebrow } from "../components/ui";
import { MOVEMENT, color, font, radius, space, type } from "../theme";
import type { MovementKind } from "../theme";

export interface RecordedSummary {
  kind: MovementKind;
  counterpartyName: string | null;
  total: number;
  sent: number;
  queued: number;
  rejected: number;
}

/**
 * The receipt.
 *
 * A storeman who has just scanned forty packs needs to know the count landed
 * before they walk away from the bay, and needs it in the same units they
 * were counting in. Queued packs are stated plainly rather than dressed up as
 * success: the device is holding them, that is normal, and saying so is what
 * makes the outbox understandable later.
 */
export function RecordedScreen({
  summary,
  onDone,
  onOutbox,
}: {
  summary: RecordedSummary;
  onDone: () => void;
  onOutbox: () => void;
}) {
  const insets = useSafeAreaInsets();
  const enter = useRef(new Animated.Value(0)).current;
  const movement = MOVEMENT[summary.kind];
  const clean = summary.rejected === 0;

  useEffect(() => {
    Animated.timing(enter, {
      toValue: 1,
      duration: 420,
      easing: Easing.out(Easing.back(1.4)),
      useNativeDriver: true,
    }).start();
  }, [enter]);

  return (
    <View style={[styles.root, { paddingTop: insets.top + space.huge }]}>
      <Animated.View
        style={[
          styles.badge,
          {
            backgroundColor: clean ? color.verdant : color.marigold,
            opacity: enter,
            transform: [
              { scale: enter.interpolate({ inputRange: [0, 1], outputRange: [0.6, 1] }) },
            ],
          },
        ]}
      >
        <StatusGlyph
          status={clean ? "known" : "held"}
          tint={color.onColor}
          size={40}
        />
      </Animated.View>

      <View style={styles.text}>
        <Eyebrow>{movement.running}</Eyebrow>
        <Text style={styles.title}>
          {summary.total} {summary.total === 1 ? "pack" : "packs"} recorded
        </Text>
        {summary.counterpartyName && (
          <Text style={styles.subtitle}>{summary.counterpartyName}</Text>
        )}
      </View>

      <View style={styles.lines}>
        {summary.sent > 0 && (
          <Line label="Sent to the platform" value={summary.sent} tint={color.verdant} />
        )}
        {summary.queued > 0 && (
          <Line
            label="Held on this device until there is a signal"
            value={summary.queued}
            tint={color.slate}
          />
        )}
        {summary.rejected > 0 && (
          <Line label="Refused by the server" value={summary.rejected} tint={color.clay} />
        )}
      </View>

      <View style={[styles.footer, { paddingBottom: insets.bottom + space.lg }]}>
        {summary.rejected > 0 || summary.queued > 0 ? (
          <>
            <Button label="Look at the outbox" onPress={onOutbox} />
            <Button label="Start another movement" onPress={onDone} tone="quiet" />
          </>
        ) : (
          <Button label="Start another movement" onPress={onDone} />
        )}
      </View>
    </View>
  );
}

function Line({ label, value, tint }: { label: string; value: number; tint: string }) {
  return (
    <View style={styles.line}>
      <View style={[styles.pip, { backgroundColor: tint }]} />
      <Text style={styles.lineValue}>{value}</Text>
      <Text style={styles.lineLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: color.docket,
    alignItems: "center",
    paddingHorizontal: space.xl,
    gap: space.xl,
  },
  badge: {
    width: 84,
    height: 84,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
  },
  text: { alignItems: "center", gap: 4 },
  title: {
    fontFamily: font.display,
    fontSize: type.headline,
    letterSpacing: -0.9,
    color: color.ink,
    textAlign: "center",
  },
  subtitle: {
    fontFamily: font.regular,
    fontSize: type.body,
    color: color.muted,
  },
  lines: { alignSelf: "stretch", gap: space.md },
  line: { flexDirection: "row", alignItems: "center", gap: space.md },
  pip: { width: 8, height: 8, borderRadius: radius.pill },
  lineValue: {
    fontFamily: font.monoBold,
    fontSize: type.bodyLarge,
    color: color.ink,
    minWidth: 26,
  },
  lineLabel: {
    flex: 1,
    fontFamily: font.regular,
    fontSize: type.caption,
    lineHeight: 19,
    color: color.muted,
  },
  footer: {
    marginTop: "auto",
    alignSelf: "stretch",
    gap: space.sm,
  },
});
