import type { ReactNode } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from "react-native";

import { color, font, radius, space, type } from "../theme";

const MIN_TARGET = 58;

interface ButtonProps {
  label: string;
  onPress: () => void;
  tone?: "primary" | "onField" | "quiet";
  busy?: boolean;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
}

export function Button({
  label,
  onPress,
  tone = "primary",
  busy,
  disabled,
  style,
}: ButtonProps) {
  const inactive = disabled || busy;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: Boolean(inactive) }}
      onPress={onPress}
      disabled={inactive}
      style={({ pressed }) => [
        styles.button,
        tone === "primary" && styles.buttonPrimary,
        tone === "onField" && styles.buttonOnField,
        tone === "quiet" && styles.buttonQuiet,
        pressed && styles.buttonPressed,
        inactive && styles.buttonInactive,
        style,
      ]}
    >
      {busy ? (
        <ActivityIndicator color={tone === "primary" ? color.onColor : color.ink} />
      ) : (
        <Text
          style={[
            styles.buttonLabel,
            tone === "primary" && { color: color.onColor },
            tone === "onField" && { color: color.ink },
            tone === "quiet" && { color: color.pine },
          ]}
        >
          {label}
        </Text>
      )}
    </Pressable>
  );
}

export function TextLink({
  label,
  onPress,
  color: tint = color.pine,
  style,
}: {
  label: string;
  onPress: () => void;
  color?: string;
  style?: StyleProp<TextStyle>;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      hitSlop={14}
      style={({ pressed }) => [{ opacity: pressed ? 0.55 : 1 }]}
    >
      <Text style={[styles.link, { color: tint }, style]}>{label}</Text>
    </Pressable>
  );
}

export function Chip({ label, tint }: { label: string; tint: string }) {
  return (
    <View style={[styles.chip, { backgroundColor: tint }]}>
      <Text style={styles.chipLabel}>{label}</Text>
    </View>
  );
}

export function Eyebrow({ children, tint = color.faint }: { children: ReactNode; tint?: string }) {
  return <Text style={[styles.eyebrow, { color: tint }]}>{children}</Text>;
}

export function Serial({ value, tint = color.muted }: { value: string; tint?: string }) {
  return (
    <Text selectable style={[styles.serial, { color: tint }]}>
      {value}
    </Text>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: MIN_TARGET,
    borderRadius: radius.md,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: space.xl,
  },
  buttonPrimary: { backgroundColor: color.pine },
  buttonOnField: { backgroundColor: color.onColor },
  buttonQuiet: {
    backgroundColor: "transparent",
    borderWidth: 2,
    borderColor: color.line,
  },
  buttonPressed: { transform: [{ scale: 0.98 }], opacity: 0.9 },
  buttonInactive: { opacity: 0.45 },
  buttonLabel: {
    fontFamily: font.bold,
    fontSize: type.bodyLarge,
    letterSpacing: 0.1,
  },
  link: {
    fontFamily: font.semi,
    fontSize: type.body,
    textDecorationLine: "underline",
  },
  chip: {
    paddingHorizontal: space.md,
    paddingVertical: 5,
    borderRadius: radius.pill,
    alignSelf: "flex-start",
  },
  chipLabel: {
    fontFamily: font.bold,
    fontSize: 11.5,
    letterSpacing: 0.6,
    color: color.onColor,
  },
  eyebrow: {
    fontFamily: font.bold,
    fontSize: 11.5,
    letterSpacing: 1.5,
    textTransform: "uppercase",
  },
  serial: {
    fontFamily: "monospace",
    fontSize: type.body,
    letterSpacing: 1.4,
  },
});
