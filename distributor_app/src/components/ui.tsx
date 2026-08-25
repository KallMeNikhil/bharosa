import type { ReactNode } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type StyleProp,
  type TextStyle,
  type ViewStyle,
} from "react-native";

import { color, font, radius, space, type } from "../theme";

const MIN_TARGET = 56;

export function Button({
  label,
  onPress,
  tone = "primary",
  busy,
  disabled,
  count,
  style,
}: {
  label: string;
  onPress: () => void;
  tone?: "primary" | "onDark" | "quiet" | "danger";
  busy?: boolean;
  disabled?: boolean;
  count?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const inactive = disabled || busy;
  const labelTint =
    tone === "primary" || tone === "danger"
      ? color.onColor
      : tone === "onDark"
        ? color.ink
        : color.ledger;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: Boolean(inactive) }}
      onPress={onPress}
      disabled={inactive}
      style={({ pressed }) => [
        styles.button,
        tone === "primary" && styles.buttonPrimary,
        tone === "onDark" && styles.buttonOnDark,
        tone === "quiet" && styles.buttonQuiet,
        tone === "danger" && styles.buttonDanger,
        pressed && styles.buttonPressed,
        inactive && styles.buttonInactive,
        style,
      ]}
    >
      {busy ? (
        <ActivityIndicator color={labelTint} />
      ) : (
        <View style={styles.buttonInner}>
          <Text style={[styles.buttonLabel, { color: labelTint }]}>{label}</Text>
          {count != null && (
            <View
              style={[
                styles.buttonCount,
                tone === "quiet" && { backgroundColor: color.ledgerSoft },
              ]}
            >
              <Text style={[styles.buttonCountLabel, { color: labelTint }]}>
                {count}
              </Text>
            </View>
          )}
        </View>
      )}
    </Pressable>
  );
}

export function TextLink({
  label,
  onPress,
  tint = color.ledger,
  style,
}: {
  label: string;
  onPress: () => void;
  tint?: string;
  style?: StyleProp<TextStyle>;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      hitSlop={14}
      style={({ pressed }) => ({ opacity: pressed ? 0.55 : 1 })}
    >
      <Text style={[styles.link, { color: tint }, style]}>{label}</Text>
    </Pressable>
  );
}

export function Field({
  label,
  hint,
  value,
  onChangeText,
  placeholder,
  autoCapitalize = "none",
  mono,
  keyboardType,
  onSubmitEditing,
}: {
  label: string;
  hint?: string;
  value: string;
  onChangeText: (next: string) => void;
  placeholder?: string;
  autoCapitalize?: "none" | "characters";
  mono?: boolean;
  keyboardType?: "default" | "url";
  onSubmitEditing?: () => void;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={color.faint}
        autoCapitalize={autoCapitalize}
        autoCorrect={false}
        keyboardType={keyboardType}
        onSubmitEditing={onSubmitEditing}
        returnKeyType="done"
        style={[styles.input, mono && styles.inputMono]}
      />
      {hint && <Text style={styles.fieldHint}>{hint}</Text>}
    </View>
  );
}

export function Eyebrow({
  children,
  tint = color.faint,
}: {
  children: ReactNode;
  tint?: string;
}) {
  return <Text style={[styles.eyebrow, { color: tint }]}>{children}</Text>;
}

export function Tag({
  label,
  tint,
  filled,
}: {
  label: string;
  tint: string;
  filled?: boolean;
}) {
  return (
    <View
      style={[
        styles.tag,
        filled ? { backgroundColor: tint } : { borderColor: tint, borderWidth: 1.5 },
      ]}
    >
      <Text style={[styles.tagLabel, { color: filled ? color.onColor : tint }]}>
        {label}
      </Text>
    </View>
  );
}

export function Mono({
  children,
  size = type.body,
  tint = color.ink,
  bold,
  style,
}: {
  children: ReactNode;
  size?: number;
  tint?: string;
  bold?: boolean;
  style?: StyleProp<TextStyle>;
}) {
  return (
    <Text
      selectable
      style={[
        {
          fontFamily: bold ? font.monoBold : font.mono,
          fontSize: size,
          color: tint,
          letterSpacing: 0.6,
        },
        style,
      ]}
    >
      {children}
    </Text>
  );
}

export function Card({
  children,
  style,
}: {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
}) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function Rule({ inset = 0 }: { inset?: number }) {
  return <View style={[styles.rule, { marginLeft: inset }]} />;
}

export function Header({
  title,
  caption,
  onBack,
  trailing,
}: {
  title: string;
  caption?: string;
  onBack?: () => void;
  trailing?: ReactNode;
}) {
  return (
    <View style={styles.header}>
      {onBack && (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Go back"
          onPress={onBack}
          hitSlop={16}
          style={({ pressed }) => [styles.back, pressed && { opacity: 0.5 }]}
        >
          <Text style={styles.backLabel}>←</Text>
        </Pressable>
      )}
      <View style={styles.headerText}>
        {caption && <Eyebrow>{caption}</Eyebrow>}
        <Text style={styles.headerTitle}>{title}</Text>
      </View>
      {trailing}
    </View>
  );
}

export function Notice({
  text,
  tint = color.clay,
}: {
  text: string;
  tint?: string;
}) {
  return (
    <View style={[styles.notice, { borderLeftColor: tint }]}>
      <Text style={styles.noticeLabel}>{text}</Text>
    </View>
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
  buttonInner: { flexDirection: "row", alignItems: "center", gap: space.md },
  buttonPrimary: { backgroundColor: color.ledger },
  buttonOnDark: { backgroundColor: color.onColor },
  buttonQuiet: {
    backgroundColor: "transparent",
    borderWidth: 1.5,
    borderColor: color.rule,
  },
  buttonDanger: { backgroundColor: color.clay },
  buttonPressed: { transform: [{ scale: 0.985 }], opacity: 0.9 },
  buttonInactive: { opacity: 0.4 },
  buttonLabel: {
    fontFamily: font.semi,
    fontSize: type.bodyLarge,
    letterSpacing: -0.1,
  },
  buttonCount: {
    minWidth: 30,
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: radius.sm,
    backgroundColor: "rgba(255,255,255,0.18)",
    alignItems: "center",
  },
  buttonCountLabel: {
    fontFamily: font.monoBold,
    fontSize: type.body,
  },
  link: {
    fontFamily: font.semi,
    fontSize: type.body,
    textDecorationLine: "underline",
  },
  field: { gap: 7 },
  fieldLabel: {
    fontFamily: font.semi,
    fontSize: type.caption,
    color: color.inkSoft,
  },
  input: {
    minHeight: 52,
    borderRadius: radius.sm,
    borderWidth: 1.5,
    borderColor: color.rule,
    backgroundColor: color.surface,
    paddingHorizontal: space.md,
    fontFamily: font.regular,
    fontSize: type.body,
    color: color.ink,
  },
  inputMono: { fontFamily: font.mono, letterSpacing: 0.6 },
  fieldHint: {
    fontFamily: font.regular,
    fontSize: type.caption,
    lineHeight: 18,
    color: color.muted,
  },
  eyebrow: {
    fontFamily: font.semi,
    fontSize: type.micro,
    letterSpacing: 1.4,
    textTransform: "uppercase",
  },
  tag: {
    paddingHorizontal: 9,
    paddingVertical: 3,
    borderRadius: radius.sm,
    alignSelf: "flex-start",
  },
  tagLabel: {
    fontFamily: font.semi,
    fontSize: type.micro,
    letterSpacing: 0.5,
  },
  card: {
    backgroundColor: color.surface,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.rule,
  },
  rule: { height: 1, backgroundColor: color.ruleSoft },
  header: { flexDirection: "row", alignItems: "center", gap: space.md },
  back: {
    width: 40,
    height: 40,
    borderRadius: radius.sm,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: color.surface,
    borderWidth: 1,
    borderColor: color.rule,
  },
  backLabel: { fontFamily: font.medium, fontSize: 20, color: color.ink },
  headerText: { flex: 1, gap: 2 },
  headerTitle: {
    fontFamily: font.display,
    fontSize: type.title,
    color: color.ink,
    letterSpacing: -0.4,
  },
  notice: {
    borderLeftWidth: 3,
    paddingLeft: space.md,
    paddingVertical: space.sm,
  },
  noticeLabel: {
    fontFamily: font.medium,
    fontSize: type.caption,
    lineHeight: 19,
    color: color.inkSoft,
  },
});
