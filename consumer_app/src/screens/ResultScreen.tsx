import { useEffect, useRef, useState } from "react";
import {
  AccessibilityInfo,
  Animated,
  Easing,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Glyph } from "../components/Glyph";
import { Button, Eyebrow, Serial, TextLink } from "../components/ui";
import { groupSerial } from "../lib/code";
import { STATE, color, font, radius, space, type, type VerificationState } from "../theme";

interface ResultScreenProps {
  state: VerificationState;
  message: string;
  serial: string;
  checkedAt: string;
  onScanAnother: () => void;
  onHelp: () => void;
}

export function ResultScreen({
  state,
  message,
  serial,
  checkedAt,
  onScanAnother,
  onHelp,
}: ResultScreenProps) {
  const insets = useSafeAreaInsets();
  const presentation = STATE[state];
  const [expanded, setExpanded] = useState(false);

  const enter = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    let cancelled = false;
    AccessibilityInfo.isReduceMotionEnabled().then((reduced) => {
      if (cancelled) return;
      if (reduced) {
        enter.setValue(1);
        return;
      }
      Animated.timing(enter, {
        toValue: 1,
        duration: 420,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }).start();
    });
    return () => {
      cancelled = true;
    };
  }, [enter]);

  const rise = enter.interpolate({ inputRange: [0, 1], outputRange: [22, 0] });
  const swell = enter.interpolate({ inputRange: [0, 1], outputRange: [0.86, 1] });

  return (
    <View style={[styles.root, { backgroundColor: presentation.field }]}>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + space.xxl, paddingBottom: insets.bottom + space.xl },
        ]}
      >
        <Animated.View style={{ transform: [{ scale: swell }], opacity: enter }}>
          <Glyph state={state} color={presentation.onField} size={104} />
        </Animated.View>

        <Animated.View
          style={[styles.verdictBlock, { opacity: enter, transform: [{ translateY: rise }] }]}
        >
          <Eyebrow tint="rgba(255,255,255,0.72)">This pack</Eyebrow>
          <Text style={styles.verdict} accessibilityRole="header">
            {presentation.verdict}
          </Text>
          <Text style={styles.message}>{message}</Text>
        </Animated.View>

        <Animated.View style={[styles.card, { opacity: enter }]}>
          <Text style={styles.cardLabel}>Code checked</Text>
          <Serial value={groupSerial(serial)} tint="rgba(255,255,255,0.95)" />
          <Text style={styles.timestamp}>
            {new Date(checkedAt).toLocaleString()}
          </Text>
        </Animated.View>

        {expanded && (
          <View style={styles.explainer}>
            <Text style={styles.explainerText}>{presentation.action}</Text>
            <Text style={styles.explainerText}>
              {state === "GENUINE"
                ? "This means the code on the pack is registered and nothing has been " +
                  "flagged against it. It is not a test of what is inside the bottle."
                : "A result like this is a reason to ask, not proof that anyone did " +
                  "anything wrong. The manufacturer can tell you more."}
            </Text>
            <Text style={styles.explainerText}>
              Checking the same pack more than once is normal and counts against nobody.
            </Text>
          </View>
        )}

        <View style={styles.actions}>
          <Button
            label="Scan another pack"
            onPress={onScanAnother}
            tone="onField"
            style={styles.stretch}
          />
          <TextLink
            label={expanded ? "Show less" : "What does this mean?"}
            onPress={() => setExpanded((open) => !open)}
            color="rgba(255,255,255,0.9)"
          />
          <TextLink label="All results explained" onPress={onHelp} color="rgba(255,255,255,0.7)" />
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  content: {
    flexGrow: 1,
    paddingHorizontal: space.xl,
    alignItems: "center",
    gap: space.xl,
  },
  verdictBlock: { alignItems: "center", gap: space.xs },
  verdict: {
    fontFamily: font.display,
    fontSize: type.verdict,
    lineHeight: type.verdict * 1.04,
    color: color.onColor,
    letterSpacing: -1.6,
    textAlign: "center",
  },
  message: {
    fontFamily: font.medium,
    fontSize: type.bodyLarge,
    lineHeight: 25,
    color: "rgba(255,255,255,0.94)",
    textAlign: "center",
    marginTop: space.sm,
    maxWidth: 340,
  },
  card: {
    width: "100%",
    maxWidth: 380,
    borderRadius: radius.md,
    backgroundColor: "rgba(0,0,0,0.16)",
    padding: space.lg,
    gap: 6,
    alignItems: "center",
  },
  cardLabel: {
    fontFamily: font.bold,
    fontSize: 11,
    letterSpacing: 1.4,
    textTransform: "uppercase",
    color: "rgba(255,255,255,0.66)",
  },
  timestamp: {
    fontFamily: font.medium,
    fontSize: type.caption,
    color: "rgba(255,255,255,0.7)",
  },
  explainer: {
    width: "100%",
    maxWidth: 380,
    gap: space.md,
    borderRadius: radius.md,
    backgroundColor: "rgba(255,255,255,0.14)",
    padding: space.lg,
  },
  explainerText: {
    fontFamily: font.medium,
    fontSize: type.body,
    lineHeight: 22,
    color: color.onColor,
  },
  stretch: { alignSelf: "stretch" },
  actions: {
    width: "100%",
    maxWidth: 380,
    gap: space.lg,
    alignItems: "center",
    marginTop: "auto",
  },
});
