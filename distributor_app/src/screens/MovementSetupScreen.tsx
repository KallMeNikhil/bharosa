import { useMemo, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import type { Participant } from "../api/client";
import { Button, Header, Mono, Notice, Tag } from "../components/ui";
import { MOVEMENT, color, font, radius, space, type } from "../theme";
import type { MovementKind } from "../theme";

const ROLE_LABEL = {
  DEPOT: "Depot",
  DISTRIBUTOR: "Distributor",
  RETAILER: "Retailer",
} as const;

/**
 * Naming the other end of the movement.
 *
 * The device's own place is filtered out of the list: a movement from a depot
 * to itself is not a movement, and offering it as a choice only creates a way
 * to record nonsense. The filter is on identity rather than on name, so two
 * branches that happen to share a name stay distinct.
 */
export function MovementSetupScreen({
  kind,
  participants,
  selfId,
  onStart,
  onBack,
}: {
  kind: MovementKind;
  participants: Participant[];
  selfId: string;
  onStart: (counterparty: Participant) => void;
  onBack: () => void;
}) {
  const insets = useSafeAreaInsets();
  const movement = MOVEMENT[kind];
  const [query, setQuery] = useState("");
  const [chosenId, setChosenId] = useState<string | null>(null);

  const options = useMemo(() => {
    const others = participants.filter((p) => p.id !== selfId);
    const needle = query.trim().toLowerCase();
    if (!needle) return others;
    return others.filter(
      (p) =>
        p.name.toLowerCase().includes(needle) ||
        p.participant_ref.toLowerCase().includes(needle),
    );
  }, [participants, selfId, query]);

  const chosen = options.find((p) => p.id === chosenId) ?? null;

  return (
    <View style={styles.root}>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + space.lg, paddingBottom: space.xxl },
        ]}
        keyboardShouldPersistTaps="handled"
      >
        <Header title={movement.label} caption={movement.running} onBack={onBack} />

        <Text style={styles.prompt}>{movement.counterparty}</Text>

        {participants.length > 1 && (
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder="Search by name or code"
            placeholderTextColor={color.faint}
            autoCorrect={false}
            style={styles.search}
          />
        )}

        {options.length === 0 ? (
          <Notice
            tint={color.marigold}
            text={
              query.trim()
                ? "No place matches that."
                : "There is nowhere else on record to move stock to. Other depots, distributors and retailers are added in the manufacturer console."
            }
          />
        ) : (
          <View style={styles.list}>
            {options.map((participant) => {
              const active = participant.id === chosenId;
              return (
                <Pressable
                  key={participant.id}
                  accessibilityRole="radio"
                  accessibilityState={{ selected: active }}
                  onPress={() => setChosenId(participant.id)}
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
        )}
      </ScrollView>

      <View style={[styles.footer, { paddingBottom: insets.bottom + space.lg }]}>
        <Button
          label="Start scanning"
          onPress={() => chosen && onStart(chosen)}
          disabled={!chosen}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.docket },
  content: { paddingHorizontal: space.xl, gap: space.lg },
  prompt: {
    fontFamily: font.display,
    fontSize: type.title,
    letterSpacing: -0.4,
    color: color.ink,
  },
  search: {
    minHeight: 50,
    borderRadius: radius.sm,
    borderWidth: 1.5,
    borderColor: color.rule,
    backgroundColor: color.surface,
    paddingHorizontal: space.md,
    fontFamily: font.regular,
    fontSize: type.body,
    color: color.ink,
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
    backgroundColor: color.surface,
    borderTopWidth: 1,
    borderTopColor: color.rule,
  },
});
