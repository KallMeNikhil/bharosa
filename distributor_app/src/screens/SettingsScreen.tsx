import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button, Card, Eyebrow, Header, Mono, Notice, Rule } from "../components/ui";
import type { Device } from "../lib/session";
import { color, font, space, type } from "../theme";

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
          <Row label="Signed in as" value={device.actorId} mono />
          <Rule />
          <Row label="Company" value={device.manufacturerName} />
          <Rule />
          <Row label="Server" value={device.baseUrl} mono small />
        </Card>

        <View style={styles.section}>
          <Eyebrow>Keep this device safe</Eyebrow>
          <Text style={styles.blurb}>
            It is signed in with your company account, which can do more than
            record movements. If it goes missing, unbind it from here if you
            still can; otherwise its session ends on its own within two weeks.
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
