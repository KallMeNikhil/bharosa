import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Chevron, DirectionIcon, OutboxIcon } from "../components/icons";
import { Lockup } from "../components/Logo";
import { Eyebrow, Rule, Tag } from "../components/ui";
import type { Device } from "../lib/session";
import { MOVEMENT, MOVEMENT_ORDER, color, font, radius, space, type } from "../theme";
import type { MovementKind } from "../theme";

const ROLE_LABEL = {
  DEPOT: "Depot",
  DISTRIBUTOR: "Distributor",
  RETAILER: "Retailer",
} as const;

/**
 * The place a shift starts.
 *
 * Every movement is one tap from here and nothing else competes for the
 * screen. The outbox strip appears only when something is actually waiting,
 * because a permanent "0 pending" row trains people to stop reading the one
 * place that matters when it is not zero.
 */
export function HomeScreen({
  device,
  pending,
  rejected,
  onStart,
  onOutbox,
  onSettings,
}: {
  device: Device;
  pending: number;
  rejected: number;
  onStart: (kind: MovementKind) => void;
  onOutbox: () => void;
  onSettings: () => void;
}) {
  const insets = useSafeAreaInsets();
  const waiting = pending + rejected;

  return (
    <View style={styles.root}>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + space.lg, paddingBottom: insets.bottom + space.xxl },
        ]}
      >
        <View style={styles.header}>
          <Lockup markSize={28} wordSize={type.bodyLarge} />
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Device settings"
            onPress={onSettings}
            hitSlop={12}
            style={({ pressed }) => [styles.place, pressed && { opacity: 0.6 }]}
          >
            <Text style={styles.placeName} numberOfLines={1}>
              {device.participant.name}
            </Text>
            <Tag label={ROLE_LABEL[device.participant.role]} tint={color.ledger} />
          </Pressable>
        </View>

        {waiting > 0 && (
          <Pressable
            accessibilityRole="button"
            onPress={onOutbox}
            style={({ pressed }) => [
              styles.outbox,
              rejected > 0 && styles.outboxAttention,
              pressed && { opacity: 0.9 },
            ]}
          >
            <OutboxIcon tint={rejected > 0 ? color.clay : color.ledger} size={22} />
            <View style={styles.outboxBody}>
              <Text style={styles.outboxTitle}>
                {rejected > 0
                  ? `${rejected} ${rejected === 1 ? "pack needs" : "packs need"} attention`
                  : `${pending} ${pending === 1 ? "pack" : "packs"} not sent yet`}
              </Text>
              <Text style={styles.outboxDetail}>
                {rejected > 0
                  ? "The server would not accept these."
                  : "They will send when there is a signal."}
              </Text>
            </View>
            <Chevron tint={rejected > 0 ? color.clay : color.ledger} />
          </Pressable>
        )}

        <View style={styles.section}>
          <Eyebrow>Start a movement</Eyebrow>

          <View style={styles.group}>
            {MOVEMENT_ORDER.map((kind, position) => {
              const movement = MOVEMENT[kind];
              return (
                <View key={kind}>
                  {position > 0 && <Rule inset={70} />}
                  <Pressable
                    accessibilityRole="button"
                    onPress={() => onStart(kind)}
                    style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
                  >
                    <View style={styles.rowIcon}>
                      <DirectionIcon direction={movement.direction} size={22} />
                    </View>
                    <View style={styles.rowBody}>
                      <Text style={styles.rowTitle}>{movement.label}</Text>
                      <Text style={styles.rowDetail}>{movement.detail}</Text>
                    </View>
                    <Chevron />
                  </Pressable>
                </View>
              );
            })}
          </View>
        </View>

        <Text style={styles.footnote}>
          Bharosa records where a pack has been, not what is inside it. A
          movement recorded here is what lets the platform tell an ordinary
          delivery from a diverted one.
        </Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.docket },
  content: { paddingHorizontal: space.xl, gap: space.xl },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: space.md,
  },
  place: { alignItems: "flex-end", gap: 3, maxWidth: 150 },
  placeName: {
    fontFamily: font.semi,
    fontSize: type.caption,
    color: color.ink,
  },
  outbox: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    padding: space.lg,
    borderRadius: radius.md,
    backgroundColor: color.ledgerSoft,
    borderWidth: 1,
    borderColor: color.ledgerLine,
  },
  outboxAttention: { backgroundColor: "#FAE7E6", borderColor: "#F0C9C7" },
  outboxBody: { flex: 1, gap: 2 },
  outboxTitle: {
    fontFamily: font.semi,
    fontSize: type.body,
    color: color.ink,
  },
  outboxDetail: {
    fontFamily: font.regular,
    fontSize: type.caption,
    color: color.muted,
  },
  section: { gap: space.md },
  group: {
    backgroundColor: color.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.rule,
    overflow: "hidden",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.lg,
    paddingHorizontal: space.lg,
    paddingVertical: space.lg,
    minHeight: 76,
  },
  rowPressed: { backgroundColor: color.ledgerSoft },
  rowIcon: {
    width: 38,
    height: 38,
    borderRadius: radius.sm,
    backgroundColor: color.ledgerSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  rowBody: { flex: 1, gap: 2 },
  rowTitle: {
    fontFamily: font.semi,
    fontSize: type.bodyLarge,
    color: color.ink,
  },
  rowDetail: {
    fontFamily: font.regular,
    fontSize: type.caption,
    lineHeight: 18,
    color: color.muted,
  },
  footnote: {
    fontFamily: font.regular,
    fontSize: type.caption,
    lineHeight: 19,
    color: color.faint,
    textAlign: "center",
  },
});
