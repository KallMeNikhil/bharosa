import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button, Field, Header, Notice } from "../components/ui";
import { looksLikeSerial } from "../lib/code";
import { color, font, space, type } from "../theme";
import type { ScanOutcome } from "./ScanScreen";

/**
 * Typing a code the camera cannot read.
 *
 * Labels get torn, soaked and scuffed in a way that a code printed on a
 * datasheet never does, and a pack whose QR will not decode is still a pack
 * that physically moved. Refusing to record it would put a hole in the
 * custody chain exactly where the damage is, which is where the chain matters
 * most.
 */
export function ManualEntryScreen({
  onSubmit,
  onBack,
}: {
  onSubmit: (serial: string) => Promise<ScanOutcome>;
  onBack: () => void;
}) {
  const insets = useSafeAreaInsets();
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; tint: string } | null>(null);

  const trimmed = value.trim().toUpperCase();

  async function submit() {
    if (!trimmed) return;
    setBusy(true);
    setMessage(null);
    try {
      const outcome = await onSubmit(trimmed);
      if (outcome === "duplicate") {
        setMessage({
          text: "That pack is already on this consignment.",
          tint: color.marigold,
        });
      } else if (outcome === "unreadable") {
        setMessage({ text: "That is not a Bharosa code.", tint: color.clay });
      } else {
        setMessage({ text: `Added ${trimmed}.`, tint: color.verdant });
        setValue("");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + space.lg, paddingBottom: insets.bottom + space.xxl },
        ]}
        keyboardShouldPersistTaps="handled"
      >
        <Header title="Type a code" caption="Damaged label" onBack={onBack} />

        <Text style={styles.blurb}>
          The code runs under the QR square on the pack. Letters and digits
          only, no spaces.
        </Text>

        <Field
          label="Pack code"
          value={value}
          onChangeText={setValue}
          placeholder="K7X4QP2MW3RB5NZ6YT8HC2FDJQ"
          autoCapitalize="characters"
          mono
          onSubmitEditing={submit}
          hint={
            trimmed && !looksLikeSerial(trimmed)
              ? "That does not look like a full pack code, but you can still add it."
              : undefined
          }
        />

        {message && <Notice text={message.text} tint={message.tint} />}

        <Button label="Add to the count" onPress={submit} disabled={!trimmed} busy={busy} />

        <Button label="Back to scanning" onPress={onBack} tone="quiet" />
      </ScrollView>
    </KeyboardAvoidingView>
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
});
