import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { DirectionIcon } from "../components/icons";
import { Button, Card, Eyebrow, Header, Mono, Rule, TextLink } from "../components/ui";
import { groupSerial } from "../lib/code";
import { pendingCount, rejectedCount, type OutboxEntry } from "../lib/outbox";
import { MOVEMENT, color, font, radius, space, type } from "../theme";

/**
 * What the device is still holding.
 *
 * A rejection is not a failure to send, it is the platform declining to
 * believe something, and the difference matters to the person reading this
 * screen. Queued packs need patience; rejected ones need a supervisor. They
 * are therefore counted separately and worded differently, and a rejected
 * entry stays here until somebody actively dismisses it.
 */
export function OutboxScreen({
  entries,
  busy,
  onSend,
  onDiscard,
  onBack,
}: {
  entries: OutboxEntry[];
  busy: boolean;
  onSend: () => void;
  onDiscard: (entryId: string) => void;
  onBack: () => void;
}) {
  const insets = useSafeAreaInsets();
  const queued = pendingCount(entries);
  const rejected = rejectedCount(entries);

  return (
    <View style={styles.root}>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + space.lg, paddingBottom: space.xxl },
        ]}
      >
        <Header title="Not sent yet" caption="Outbox" onBack={onBack} />

        {entries.length === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyTitle}>Everything has been sent</Text>
            <Text style={styles.emptyDetail}>
              Movements recorded on this device are with the platform.
            </Text>
          </View>
        ) : (
          <>
            <Text style={styles.summary}>
              {queued > 0 &&
                `${queued} ${queued === 1 ? "pack is" : "packs are"} waiting for a signal. `}
              {rejected > 0 &&
                `${rejected} ${rejected === 1 ? "was" : "were"} refused by the server.`}
            </Text>

            {entries.map((entry) => {
              const movement = MOVEMENT[entry.kind];
              const refused = entry.events.filter((e) => e.state === "rejected");
              const waiting = entry.events.filter((e) => e.state === "queued");

              return (
                <Card key={entry.id}>
                  <View style={styles.entryHead}>
                    <View style={styles.entryIcon}>
                      <DirectionIcon direction={movement.direction} size={19} />
                    </View>
                    <View style={styles.entryText}>
                      <Eyebrow>{movement.running}</Eyebrow>
                      <Text style={styles.entryTitle}>
                        {entry.counterpartyName ?? movement.label}
                      </Text>
                    </View>
                    <Text style={styles.entryTime}>
                      {new Date(entry.occurredAt).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </Text>
                  </View>

                  <Rule />

                  <View style={styles.entryBody}>
                    {waiting.length > 0 && (
                      <Text style={styles.waiting}>
                        {waiting.length} {waiting.length === 1 ? "pack" : "packs"} waiting
                        to send
                      </Text>
                    )}

                    {refused.map((event) => (
                      <View key={event.serial} style={styles.refused}>
                        <Mono size={type.micro} tint={color.ink}>
                          {groupSerial(event.serial)}
                        </Mono>
                        <Text style={styles.refusedReason}>{event.error}</Text>
                      </View>
                    ))}

                    {refused.length > 0 && (
                      <TextLink
                        label="Remove this from the device"
                        tint={color.clay}
                        onPress={() => onDiscard(entry.id)}
                      />
                    )}
                  </View>
                </Card>
              );
            })}
          </>
        )}
      </ScrollView>

      {queued > 0 && (
        <View style={[styles.footer, { paddingBottom: insets.bottom + space.lg }]}>
          <Button label="Send now" count={queued} onPress={onSend} busy={busy} />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.docket },
  content: { paddingHorizontal: space.xl, gap: space.lg },
  summary: {
    fontFamily: font.regular,
    fontSize: type.body,
    lineHeight: 22,
    color: color.muted,
  },
  empty: { paddingVertical: space.huge, alignItems: "center", gap: space.sm },
  emptyTitle: {
    fontFamily: font.semi,
    fontSize: type.bodyLarge,
    color: color.inkSoft,
  },
  emptyDetail: {
    fontFamily: font.regular,
    fontSize: type.caption,
    color: color.faint,
    textAlign: "center",
  },
  entryHead: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    padding: space.lg,
  },
  entryIcon: {
    width: 34,
    height: 34,
    borderRadius: radius.sm,
    backgroundColor: color.ledgerSoft,
    alignItems: "center",
    justifyContent: "center",
  },
  entryText: { flex: 1, gap: 2 },
  entryTitle: {
    fontFamily: font.semi,
    fontSize: type.body,
    color: color.ink,
  },
  entryTime: {
    fontFamily: font.mono,
    fontSize: type.micro,
    color: color.faint,
  },
  entryBody: { padding: space.lg, gap: space.md },
  waiting: {
    fontFamily: font.regular,
    fontSize: type.caption,
    color: color.muted,
  },
  refused: { gap: 3 },
  refusedReason: {
    fontFamily: font.regular,
    fontSize: type.caption,
    lineHeight: 18,
    color: color.clay,
  },
  footer: {
    paddingHorizontal: space.xl,
    paddingTop: space.lg,
    backgroundColor: color.surface,
    borderTopWidth: 1,
    borderTopColor: color.rule,
  },
});
