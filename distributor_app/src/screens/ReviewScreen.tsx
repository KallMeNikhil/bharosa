import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { DirectionIcon, StatusGlyph } from "../components/icons";
import { TallyRow } from "../components/TallyRow";
import { Button, Card, Eyebrow, Header, Rule } from "../components/ui";
import { countByStatus, type Consignment } from "../lib/consignment";
import { MOVEMENT, PACK, color, font, radius, space, type } from "../theme";

export function ReviewScreen({
  consignment,
  busy,
  onCommit,
  onBack,
}: {
  consignment: Consignment;
  busy: boolean;
  onCommit: () => void;
  onBack: () => void;
}) {
  const insets = useSafeAreaInsets();
  const movement = MOVEMENT[consignment.kind];
  const counts = countByStatus(consignment.packs);
  const total = consignment.packs.length;
  const flagged = counts.unknown + counts.held;

  return (
    <View style={styles.root}>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + space.lg, paddingBottom: space.xxl },
        ]}
      >
        <Header title="Check the count" caption="Before recording" onBack={onBack} />

        <Card style={styles.docket}>
          <View style={styles.docketHead}>
            <View style={styles.docketIcon}>
              <DirectionIcon direction={movement.direction} size={20} />
            </View>
            <View style={styles.docketText}>
              <Eyebrow>{movement.running}</Eyebrow>
              <Text style={styles.docketTitle}>
                {consignment.counterpartyName ?? movement.label}
              </Text>
            </View>
            <View style={styles.docketCount}>
              <Text style={styles.docketCountValue}>{total}</Text>
              <Text style={styles.docketCountLabel}>
                {total === 1 ? "pack" : "packs"}
              </Text>
            </View>
          </View>

          <Rule />

          <View style={styles.statuses}>
            {(["known", "held", "unknown", "pending"] as const)
              .filter((status) => counts[status] > 0)
              .map((status) => (
                <View key={status} style={styles.statusRow}>
                  <View style={[styles.statusBadge, { backgroundColor: PACK[status].tint }]}>
                    <StatusGlyph status={status} tint={color.onColor} size={14} />
                  </View>
                  <Text style={styles.statusCount}>{counts[status]}</Text>
                  <View style={styles.statusText}>
                    <Text style={styles.statusLabel}>{PACK[status].label}</Text>
                    <Text style={styles.statusDetail}>{PACK[status].detail}</Text>
                  </View>
                </View>
              ))}
          </View>
        </Card>

        <View style={styles.section}>
          <Eyebrow>Every pack, in the order you scanned it</Eyebrow>
          <View style={styles.list}>
            {consignment.packs.map((pack, position) => (
              <TallyRow
                key={pack.serial}
                index={position + 1}
                serial={pack.serial}
                status={pack.status}
              />
            ))}
          </View>
        </View>
      </ScrollView>

      <View style={[styles.footer, { paddingBottom: insets.bottom + space.lg }]}>
        {flagged > 0 && (
          <Text style={styles.warning}>
            {flagged === 1 ? "One pack is" : `${flagged} packs are`} flagged.
            Recording them is still the right thing to do; the flag travels
            with the record.
          </Text>
        )}
        <Button
          label="Record this movement"
          count={total}
          onPress={onCommit}
          busy={busy}
          disabled={total === 0}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.docket },
  content: { paddingHorizontal: space.xl, gap: space.xl },
  docket: { overflow: "hidden" },
  docketHead: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    padding: space.lg,
  },
  docketIcon: {
    width: 36,
    height: 36,
    borderRadius: radius.sm,
    backgroundColor: color.ledgerSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  docketText: { flex: 1, gap: 2 },
  docketTitle: {
    fontFamily: font.semi,
    fontSize: type.bodyLarge,
    color: color.ink,
  },
  docketCount: { alignItems: "flex-end" },
  docketCountValue: {
    fontFamily: font.monoBold,
    fontSize: type.headline,
    color: color.ink,
    letterSpacing: -1,
  },
  docketCountLabel: {
    fontFamily: font.regular,
    fontSize: type.micro,
    color: color.muted,
  },
  statuses: { padding: space.lg, gap: space.md },
  statusRow: { flexDirection: "row", alignItems: "flex-start", gap: space.md },
  statusBadge: {
    width: 24,
    height: 24,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 1,
  },
  statusCount: {
    fontFamily: font.monoBold,
    fontSize: type.body,
    color: color.ink,
    minWidth: 22,
    marginTop: 2,
  },
  statusText: { flex: 1, gap: 2 },
  statusLabel: {
    fontFamily: font.semi,
    fontSize: type.body,
    color: color.ink,
  },
  statusDetail: {
    fontFamily: font.regular,
    fontSize: type.caption,
    lineHeight: 19,
    color: color.muted,
  },
  section: { gap: space.md },
  list: {
    backgroundColor: color.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.rule,
    overflow: "hidden",
  },
  footer: {
    paddingHorizontal: space.xl,
    paddingTop: space.lg,
    gap: space.md,
    backgroundColor: color.surface,
    borderTopWidth: 1,
    borderTopColor: color.rule,
  },
  warning: {
    fontFamily: font.regular,
    fontSize: type.caption,
    lineHeight: 19,
    color: color.muted,
  },
});
