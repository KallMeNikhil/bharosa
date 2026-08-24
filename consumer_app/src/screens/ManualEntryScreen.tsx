import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button, Eyebrow, TextLink } from "../components/ui";
import { looksLikeSerial } from "../lib/code";
import { color, font, radius, space, type } from "../theme";

interface ManualEntryScreenProps {
  onCheck: (code: string) => void;
  onBack: () => void;
  busy: boolean;
  error: string | null;
}

const SERIAL_LENGTH = 26;

/**
 * The way in when the camera cannot help: a torn label, a scratched code, a
 * phone whose camera has given up. Typing 26 characters is unpleasant, so the
 * field shows progress and never rejects what has been typed.
 */
export function ManualEntryScreen({
  onCheck,
  onBack,
  busy,
  error,
}: ManualEntryScreenProps) {
  const insets = useSafeAreaInsets();
  const [value, setValue] = useState("");

  const cleaned = value.replace(/\s+/g, "").toUpperCase();
  const ready = cleaned.length > 0;

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + space.xl, paddingBottom: insets.bottom + space.xl },
        ]}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.header}>
          <Eyebrow>Bharosa</Eyebrow>
          <Text style={styles.title}>Enter the code</Text>
          <Text style={styles.lede}>
            The code is printed beside the QR square on the pack. Letters and
            numbers only.
          </Text>
        </View>

        <View style={styles.field}>
          <TextInput
            value={cleaned}
            onChangeText={setValue}
            autoCapitalize="characters"
            autoCorrect={false}
            spellCheck={false}
            maxLength={64}
            placeholder="XXXXXXXXXXXXXXXXXXXXXXXXXX"
            placeholderTextColor={color.faint}
            style={styles.input}
            accessibilityLabel="Pack code"
            returnKeyType="go"
            onSubmitEditing={() => ready && onCheck(cleaned)}
          />
          <View style={styles.meter}>
            <Text style={styles.meterText}>
              {cleaned.length} of {SERIAL_LENGTH}
            </Text>
            {cleaned.length > 0 && !looksLikeSerial(cleaned) && (
              <Text style={styles.meterHint}>
                {cleaned.length < SERIAL_LENGTH
                  ? "Keep going"
                  : "Check for a mistyped character"}
              </Text>
            )}
          </View>
        </View>

        {error && <Text style={styles.error}>{error}</Text>}

        <View style={styles.actions}>
          <Button
            label="Check this code"
            onPress={() => onCheck(cleaned)}
            disabled={!ready}
            busy={busy}
            style={styles.stretch}
          />
          <TextLink label="Use the camera instead" onPress={onBack} />
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.paper },
  content: {
    flexGrow: 1,
    paddingHorizontal: space.xl,
    gap: space.xxl,
  },
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
    lineHeight: 24,
    color: color.muted,
    marginTop: space.sm,
  },
  field: { gap: space.sm },
  input: {
    fontFamily: "monospace",
    fontSize: 19,
    letterSpacing: 2.4,
    color: color.ink,
    backgroundColor: color.surface,
    borderWidth: 2,
    borderColor: color.line,
    borderRadius: radius.md,
    paddingHorizontal: space.lg,
    paddingVertical: space.lg,
    minHeight: 66,
  },
  meter: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  meterText: {
    fontFamily: font.semi,
    fontSize: type.caption,
    color: color.faint,
  },
  meterHint: {
    fontFamily: font.medium,
    fontSize: type.caption,
    color: color.marigold,
  },
  error: {
    fontFamily: font.medium,
    fontSize: type.body,
    lineHeight: 22,
    color: color.clay,
    backgroundColor: "#FBEAEA",
    borderRadius: radius.sm,
    padding: space.lg,
  },
  actions: { gap: space.lg, alignItems: "center", marginTop: "auto" },
  stretch: { alignSelf: "stretch" },
});
