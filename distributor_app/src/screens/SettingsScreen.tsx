import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button, Card, Eyebrow, Header, Mono, Notice, Rule } from "../components/ui";
import type { Device } from "../lib/session";
import { color, font, space, type } from "../theme";

/**
 * What this device is, and how to unbind it.
 *
 * Unbinding is deliberately not destructive: anything the scanner has
 * recorded but not sent stays on it. Handing a phone to another branch must
 * never be a way to make a shift's movements disappear, so the outbox has to
 * be emptied on purpose before the binding can be cleared.
 */
export function SettingsScreen({
  device,
  pending,
  onUnbind,
  onBack,
}: {
  device: Device;
  pending: number;
  onUnbind: () => void;
  onBack: () => void;
}) {
  const insets = useSafeAreaInsets();

  return (
    <View style={styles.root}>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + space.lg, paddingBottom: insets.bottom + space.xxl },
        ]}
      >
        <Header title="This device" caption="Settings" onBack={onBack} />

        <Card>
          <Row label="Bound to" value={device.participant.name} />
          <Rule />
          <Row label="Place code" value={device.participant.participant_ref} mono />
          <Rule />
          <Row label="Device name" value={device.actorId} mono />
          <Rule />
          <Row label="Manufacturer" value={device.manufacturerId} mono small />
          <Rule />
          <Row label="Server" value={device.baseUrl} mono small />
        </Card>

        <View style={styles.section}>
          <Eyebrow>What this device may do</Eyebrow>
          <Text style={styles.blurb}>
            Record that a pack moved. Nothing else. It cannot create products,
            issue pack codes, or reach signing keys, so a scanner taken from a
            loading bay is worth no more than the movements it can fake.
          </Text>
        </View>

        {pending > 0 && (
          <Notice
            tint={color.marigold}
            text={`${pending} ${pending === 1 ? "pack has" : "packs have"} not been sent yet. Send them before unbinding, or they stay on this device.`}
          />
        )}

        <Button label="Unbind this device" onPress={onUnbind} tone="danger" />
      </ScrollView>
    </View>
  );
}

function Row({
  label,
  value,
  mono,
  small,
}: {
  label: string;
  value: string;
  mono?: boolean;
  small?: boolean;
}) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      {mono ? (
        <Mono size={small ? type.micro : type.caption} tint={color.ink} style={styles.rowValue}>
          {value}
        </Mono>
      ) : (
        <Text style={[styles.rowValue, styles.rowValueText]}>{value}</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.docket },
  content: { paddingHorizontal: space.xl, gap: space.lg },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.lg,
    paddingHorizontal: space.lg,
    paddingVertical: space.md,
    minHeight: 52,
  },
  rowLabel: {
    fontFamily: font.regular,
    fontSize: type.caption,
    color: color.muted,
    width: 104,
  },
  rowValue: { flex: 1, textAlign: "right" },
  rowValueText: {
    fontFamily: font.semi,
    fontSize: type.body,
    color: color.ink,
  },
  section: { gap: space.sm },
  blurb: {
    fontFamily: font.regular,
    fontSize: type.body,
    lineHeight: 22,
    color: color.muted,
  },
});
