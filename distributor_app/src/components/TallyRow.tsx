import { useEffect, useRef } from "react";
import { Animated, Easing, Pressable, StyleSheet, Text, View } from "react-native";

import { StatusGlyph } from "./icons";
import { groupSerial } from "../lib/code";
import { PACK, color, font, radius, space, type } from "../theme";
import type { PackStatus } from "../theme";

/**
 * One line of the tally.
 *
 * A delivery challan numbers its line items, and so does this: the numbers
 * are not decoration but the count itself, growing downward as the lorry is
 * unloaded. They run in the gutter on the left behind a ruled edge, exactly
 * where they sit on the paper docket this replaces, so a storeman comparing
 * the two documents is reading the same column in both.
 *
 * Numbering ascends with the scan order and is never renumbered when a line
 * is removed, because the number is a record of what happened rather than a
 * position in a list.
 */
export function TallyRow({
  index,
  serial,
  status,
  onPress,
  fresh,
}: {
  index: number;
  serial: string;
  status: PackStatus;
  onPress?: () => void;
  /** Animates in. Set only on the line the last scan produced. */
  fresh?: boolean;
}) {
  const enter = useRef(new Animated.Value(fresh ? 0 : 1)).current;
  const presentation = PACK[status];

  useEffect(() => {
    if (!fresh) return;
    Animated.timing(enter, {
      toValue: 1,
      duration: 240,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();
  }, [enter, fresh]);

  return (
    <Animated.View
      style={{
        opacity: enter,
        transform: [
          { translateY: enter.interpolate({ inputRange: [0, 1], outputRange: [-14, 0] }) },
        ],
      }}
    >
      <Pressable
        accessibilityRole={onPress ? "button" : "text"}
        accessibilityLabel={`Line ${index}, ${groupSerial(serial)}, ${presentation.label}`}
        onPress={onPress}
        style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
      >
        <View style={styles.gutter}>
          <Text style={styles.index}>{String(index).padStart(2, "0")}</Text>
        </View>

        <View style={styles.body}>
          <Text style={styles.serial} numberOfLines={1}>
            {groupSerial(serial)}
          </Text>
          <Text style={[styles.status, { color: presentation.tint }]}>
            {presentation.label}
          </Text>
        </View>

        <View style={[styles.badge, { backgroundColor: presentation.tint }]}>
          <StatusGlyph status={status} tint={color.onColor} size={15} />
        </View>
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: color.surface,
    borderBottomWidth: 1,
    borderBottomColor: color.ruleSoft,
    paddingRight: space.lg,
    minHeight: 62,
  },
  rowPressed: { backgroundColor: color.ledgerSoft },
  gutter: {
    width: 46,
    alignSelf: "stretch",
    alignItems: "center",
    justifyContent: "center",
    borderRightWidth: 1,
    borderRightColor: color.ledgerLine,
    backgroundColor: color.ledgerSoft,
  },
  index: {
    fontFamily: font.monoBold,
    fontSize: type.caption,
    color: color.ledger,
    letterSpacing: 0.4,
  },
  body: { flex: 1, paddingHorizontal: space.md, gap: 2 },
  serial: {
    fontFamily: font.mono,
    fontSize: type.caption,
    letterSpacing: 0.7,
    color: color.ink,
  },
  status: {
    fontFamily: font.semi,
    fontSize: type.micro,
    letterSpacing: 0.3,
  },
  badge: {
    width: 26,
    height: 26,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
  },
});
