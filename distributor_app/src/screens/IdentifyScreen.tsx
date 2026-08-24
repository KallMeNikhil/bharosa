import { useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import type { Participant } from "../api/client";
import { Button, Eyebrow, Header, Mono, Tag } from "../components/ui";
import { color, font, radius, space, type } from "../theme";

const ROLE_LABEL: Record<Participant["role"], string> = {
  DEPOT: "Depot",
  DISTRIBUTOR: "Distributor",
  RETAILER: "Retailer",
};

/**
 * Which place this scanner belongs to.
 *
 * Every movement the device records names this participant on one end, so
 * getting it wrong quietly poisons the custody chain for as long as nobody
 * notices. It is therefore a deliberate, one-time choice on its own screen
 * rather than a dropdown buried in settings.
 */
export function IdentifyScreen({
  participants,
  onChoose,
  onBack,
  busy,
}: {
  participants: Participant[];
  onChoose: (participant: Participant) => void;
  onBack: () => void;
  busy?: boolean;
}) {
  const insets = useSafeAreaInsets();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = participants.find((p) => p.id === selectedId) ?? null;

  return (
    <View style={styles.root}>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + space.lg, paddingBottom: space.xxl },
        ]}
      >
        <Header
          title="Where is this scanner?"
          caption="Step 2 of 2"
          onBack={onBack}
        />

        <Text style={styles.blurb}>
          Pick the place this device belongs to. Everything it records will be
          filed under this name.
        </Text>

        <View style={styles.list}>
          {participants.map((participant) => {
            const active = participant.id === selectedId;
            return (
              <Pressable
                key={participant.id}
                accessibilityRole="radio"
                accessibilityState={{ selected: active }}
                onPress={() => setSelectedId(participant.id)}
                style={({ pressed }) => [
                  styles.option,
                  active && styles.optionActive,
                  pressed && !active && styles.optionPressed,
                ]}
              >
                <View style={[styles.dot, active && styles.dotActive]}>
                  {active && <View style={styles.dotCore} />}
                </View>
                <View style={styles.optionBody}>
                  <Text style={styles.optionName}>{participant.name}</Text>
                  <Mono size={type.micro} tint={color.faint}>
                    {participant.participant_ref}
                  </Mono>
                </View>
                <Tag label={ROLE_LABEL[participant.role]} tint={color.ledger} />
              </Pressable>
            );
          })}
        </View>
      </ScrollView>

      <View style={[styles.footer, { paddingBottom: insets.bottom + space.lg }]}>
        <Eyebrow>
          {selected ? `Binding to ${selected.name}` : "Nothing selected yet"}
        </Eyebrow>
        <Button
          label="Finish setup"
          onPress={() => selected && onChoose(selected)}
          disabled={!selected}
          busy={busy}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.docket },
  content: { paddingHorizontal: space.xl, gap: space.lg },
  blurb: {
    fontFamily: font.regular,
    fontSize: type.body,
    lineHeight: 22,
    color: color.muted,
  },
  list: { gap: space.sm },
  option: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    minHeight: 68,
    paddingHorizontal: space.lg,
    backgroundColor: color.surface,
    borderRadius: radius.md,
    borderWidth: 1.5,
    borderColor: color.rule,
  },
  optionActive: { borderColor: color.ledger, backgroundColor: color.ledgerSoft },
  optionPressed: { backgroundColor: color.ledgerSoft },
  dot: {
    width: 22,
    height: 22,
    borderRadius: radius.pill,
    borderWidth: 2,
    borderColor: color.rule,
    alignItems: "center",
    justifyContent: "center",
  },
  dotActive: { borderColor: color.ledger },
  dotCore: {
    width: 11,
    height: 11,
    borderRadius: radius.pill,
    backgroundColor: color.ledger,
  },
  optionBody: { flex: 1, gap: 2 },
  optionName: {
    fontFamily: font.semi,
    fontSize: type.bodyLarge,
    color: color.ink,
  },
  footer: {
    paddingHorizontal: space.xl,
    paddingTop: space.lg,
    gap: space.md,
    backgroundColor: color.surface,
    borderTopWidth: 1,
    borderTopColor: color.rule,
  },
});
