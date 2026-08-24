import { FlatList, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Glyph } from "../components/Glyph";
import { Button, Chip, Eyebrow, Serial, TextLink } from "../components/ui";
import { groupSerial } from "../lib/code";
import type { HistoryEntry } from "../lib/history";
import { STATE, color, font, radius, space, type } from "../theme";

interface HistoryScreenProps {
  entries: HistoryEntry[];
  onBack: () => void;
  onClear: () => void;
}

export function HistoryScreen({ entries, onBack, onClear }: HistoryScreenProps) {
  const insets = useSafeAreaInsets();

  return (
    <View style={styles.root}>
      <FlatList
        data={entries}
        keyExtractor={(item) => item.id}
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + space.xl, paddingBottom: insets.bottom + space.xxl },
        ]}
        ListHeaderComponent={
          <View style={styles.header}>
            <Eyebrow>Bharosa</Eyebrow>
            <Text style={styles.title}>Packs you checked</Text>
            <Text style={styles.lede}>
              Kept on this phone only. Nothing here is sent anywhere.
            </Text>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyTitle}>Nothing checked yet</Text>
            <Text style={styles.emptyBody}>
              Scan the QR code on a pack and the result will appear here.
            </Text>
          </View>
        }
        renderItem={({ item }) => {
          const presentation = STATE[item.state];
          return (
            <View style={styles.row}>
              <View style={[styles.rowGlyph, { backgroundColor: presentation.chip }]}>
                <Glyph state={item.state} color={color.onColor} size={26} strokeWidth={9} />
              </View>
              <View style={styles.rowBody}>
                <Serial value={groupSerial(item.serial)} tint={color.ink} />
                <Text style={styles.rowTime}>
                  {new Date(item.checkedAt).toLocaleString()}
                </Text>
              </View>
              <Chip label={presentation.verdict} tint={presentation.chip} />
            </View>
          );
        }}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        ListFooterComponent={
          <View style={styles.footer}>
            <Button label="Back to scanning" onPress={onBack} style={styles.stretch} />
            {entries.length > 0 && (
              <TextLink label="Clear this list" onPress={onClear} color={color.clay} />
            )}
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.paper },
  content: { paddingHorizontal: space.xl, gap: 0 },
  header: { gap: space.xs, marginBottom: space.xl },
  title: {
    fontFamily: font.display,
    fontSize: type.headline,
    color: color.ink,
    letterSpacing: -0.7,
    marginTop: 2,
  },
  lede: {
    fontFamily: font.medium,
    fontSize: type.body,
    lineHeight: 22,
    color: color.muted,
    marginTop: space.sm,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    paddingVertical: space.md,
  },
  rowGlyph: {
    width: 44,
    height: 44,
    borderRadius: radius.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  rowBody: { flex: 1, gap: 3 },
  rowTime: {
    fontFamily: font.medium,
    fontSize: type.caption,
    color: color.faint,
  },
  separator: { height: 1, backgroundColor: color.line },
  empty: {
    paddingVertical: space.huge,
    alignItems: "center",
    gap: space.sm,
  },
  emptyTitle: {
    fontFamily: font.bold,
    fontSize: type.title,
    color: color.ink,
  },
  emptyBody: {
    fontFamily: font.medium,
    fontSize: type.body,
    lineHeight: 22,
    color: color.muted,
    textAlign: "center",
    maxWidth: 280,
  },
  footer: { marginTop: space.xxl, gap: space.lg, alignItems: "center" },
  stretch: { alignSelf: "stretch" },
});
