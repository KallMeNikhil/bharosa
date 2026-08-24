import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Glyph } from "../components/Glyph";
import { Button, Eyebrow } from "../components/ui";
import { STATE, color, font, radius, space, type, type VerificationState } from "../theme";

const ORDER: VerificationState[] = [
  "GENUINE",
  "CAUTION",
  "INVALID",
  "ALREADY_REPORTED",
  "UNAVAILABLE",
];

const MEANING: Record<VerificationState, string> = {
  GENUINE:
    "The code is registered with the manufacturer and nothing has been flagged " +
    "against this pack.",
  CAUTION:
    "The code is registered, but something about how this pack has been used " +
    "is worth a second look.",
  INVALID:
    "We could not confirm this code. That can mean it was never registered, or " +
    "that the pack was made before the manufacturer joined Bharosa.",
  ALREADY_REPORTED:
    "This pack has already been raised with the manufacturer by someone else.",
  UNAVAILABLE:
    "We could not reach the checking service, or too many checks came from this " +
    "connection at once.",
};

/**
 * Written to be read by someone deciding whether to spray a field today.
 *
 * The honesty here is deliberate: a registered code is not a laboratory test
 * of the liquid, and an unconfirmed one is not an accusation. Saying so
 * plainly is the difference between a tool people trust and one they learn to
 * ignore.
 */
export function HelpScreen({ onBack }: { onBack: () => void }) {
  const insets = useSafeAreaInsets();

  return (
    <View style={styles.root}>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + space.xl, paddingBottom: insets.bottom + space.xxl },
        ]}
      >
        <View style={styles.header}>
          <Eyebrow>Bharosa</Eyebrow>
          <Text style={styles.title}>What the results mean</Text>
          <Text style={styles.lede}>
            Bharosa checks whether a pack&apos;s code is registered and how that
            code has behaved since it was made. It does not test what is inside
            the bottle.
          </Text>
        </View>

        <View style={styles.list}>
          {ORDER.map((state) => {
            const presentation = STATE[state];
            return (
              <View key={state} style={styles.entry}>
                <View style={[styles.mark, { backgroundColor: presentation.chip }]}>
                  <Glyph state={state} color={color.onColor} size={30} strokeWidth={8} />
                </View>
                <View style={styles.entryBody}>
                  <Text style={styles.entryTitle}>{presentation.verdict}</Text>
                  <Text style={styles.entryText}>{MEANING[state]}</Text>
                  <Text style={styles.entryAction}>{presentation.action}</Text>
                </View>
              </View>
            );
          })}
        </View>

        <View style={styles.notes}>
          <Text style={styles.noteTitle}>Two things worth knowing</Text>
          <Text style={styles.noteText}>
            Checking the same pack several times is completely normal. It is not
            recorded against you and it does not make a result worse.
          </Text>
          <Text style={styles.noteText}>
            Sharing your location makes the check more accurate, but declining
            never blocks it and never counts against the pack.
          </Text>
        </View>

        <Button label="Back to scanning" onPress={onBack} style={styles.stretch} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.paper },
  content: { paddingHorizontal: space.xl, gap: space.xxl },
  header: { gap: space.xs },
  title: {
    fontFamily: font.display,
    fontSize: type.headline,
    color: color.ink,
    letterSpacing: -0.7,
    marginTop: 2,
  },
  lede: {
    fontFamily: font.medium,
    fontSize: type.bodyLarge,
    lineHeight: 25,
    color: color.muted,
    marginTop: space.sm,
  },
  list: { gap: space.xl },
  entry: { flexDirection: "row", gap: space.lg },
  mark: {
    width: 50,
    height: 50,
    borderRadius: radius.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  entryBody: { flex: 1, gap: 5 },
  entryTitle: {
    fontFamily: font.bold,
    fontSize: type.bodyLarge,
    color: color.ink,
  },
  entryText: {
    fontFamily: font.medium,
    fontSize: type.body,
    lineHeight: 22,
    color: color.inkSoft,
  },
  entryAction: {
    fontFamily: font.semi,
    fontSize: type.caption,
    lineHeight: 20,
    color: color.muted,
  },
  notes: {
    gap: space.md,
    backgroundColor: color.pineSoft,
    borderRadius: radius.md,
    padding: space.lg,
  },
  noteTitle: {
    fontFamily: font.bold,
    fontSize: type.body,
    color: color.pine,
  },
  noteText: {
    fontFamily: font.medium,
    fontSize: type.body,
    lineHeight: 22,
    color: color.inkSoft,
  },
  stretch: { alignSelf: "stretch" },
});
