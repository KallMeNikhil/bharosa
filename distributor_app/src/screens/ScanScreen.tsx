import { CameraView, useCameraPermissions } from "expo-camera";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Animated,
  Easing,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ScanFrame } from "../components/icons";
import { TallyRow } from "../components/TallyRow";
import { Button, Eyebrow } from "../components/ui";
import { countByStatus, type Consignment } from "../lib/consignment";
import { MOVEMENT, PACK, color, font, radius, space, type } from "../theme";

export type ScanOutcome = "added" | "duplicate" | "unreadable";

export function ScanScreen({
  consignment,
  onCode,
  onRemove,
  onManualEntry,
  onFinish,
  onBack,
}: {
  consignment: Consignment;
  onCode: (serial: string) => Promise<ScanOutcome>;
  onRemove: (serial: string) => void;
  onManualEntry: () => void;
  onFinish: () => void;
  onBack: () => void;
}) {
  const insets = useSafeAreaInsets();
  const { height } = useWindowDimensions();
  const [permission, requestPermission] = useCameraPermissions();
  const [torch, setTorch] = useState(false);
  const [flash, setFlash] = useState<{ text: string; tint: string } | null>(null);
  const claimed = useRef(false);
  const flashOpacity = useRef(new Animated.Value(0)).current;
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const movement = MOVEMENT[consignment.kind];
  const counts = countByStatus(consignment.packs);
  const total = consignment.packs.length;
  const cameraUsable = permission?.granted && Platform.OS !== "web";

  const showFlash = useCallback(
    (text: string, tint: string) => {
      setFlash({ text, tint });
      flashOpacity.setValue(1);
      if (flashTimer.current) clearTimeout(flashTimer.current);
      flashTimer.current = setTimeout(() => {
        Animated.timing(flashOpacity, {
          toValue: 0,
          duration: 260,
          easing: Easing.in(Easing.quad),
          useNativeDriver: true,
        }).start(() => setFlash(null));
      }, 1400);
    },
    [flashOpacity],
  );

  useEffect(
    () => () => {
      if (flashTimer.current) clearTimeout(flashTimer.current);
    },
    [],
  );

  const handleBarcode = useCallback(
    async ({ data }: { data: string }) => {
      if (claimed.current) return;
      claimed.current = true;

      const outcome = await onCode(data);
      if (outcome === "duplicate") {
        showFlash("Already counted", color.marigold);
      } else if (outcome === "unreadable") {
        showFlash("Not a Bharosa code", color.clay);
      }

      setTimeout(() => {
        claimed.current = false;
      }, 1200);
    },
    [onCode, showFlash],
  );

  const cameraHeight = Math.max(200, Math.min(height * 0.34, 300));

  return (
    <View style={styles.root}>
      <View style={[styles.head, { paddingTop: insets.top + space.md }]}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Leave this consignment"
          onPress={onBack}
          hitSlop={16}
          style={({ pressed }) => [styles.back, pressed && { opacity: 0.6 }]}
        >
          <Text style={styles.backLabel}>←</Text>
        </Pressable>
        <View style={styles.headText}>
          <Eyebrow tint="rgba(255,255,255,0.6)">{movement.running}</Eyebrow>
          <Text style={styles.headTitle} numberOfLines={1}>
            {consignment.counterpartyName ?? movement.label}
          </Text>
        </View>
      </View>

      <View style={[styles.camera, { height: cameraHeight }]}>
        {cameraUsable ? (
          <CameraView
            style={StyleSheet.absoluteFill}
            facing="back"
            enableTorch={torch}
            barcodeScannerSettings={{ barcodeTypes: ["qr", "datamatrix"] }}
            onBarcodeScanned={handleBarcode}
          />
        ) : (
          <View style={[StyleSheet.absoluteFill, styles.cameraOff]}>
            <Text style={styles.cameraOffLabel}>
              {Platform.OS === "web"
                ? "Scanning needs the phone app. Type codes in instead."
                : "Bharosa needs the camera to read pack codes."}
            </Text>
            {Platform.OS !== "web" && (
              <Button label="Allow camera" onPress={requestPermission} tone="onDark" />
            )}
          </View>
        )}

        {cameraUsable && (
          <>
            <View style={styles.frameArea} pointerEvents="none">
              <ScanFrame size={cameraHeight * 0.56} />
            </View>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={torch ? "Turn light off" : "Turn light on"}
              onPress={() => setTorch((on) => !on)}
              style={[styles.torch, torch && styles.torchOn]}
            >
              <Text style={[styles.torchLabel, torch && { color: color.ink }]}>
                {torch ? "Light on" : "Light"}
              </Text>
            </Pressable>
          </>
        )}

        {flash && (
          <Animated.View
            style={[styles.flash, { opacity: flashOpacity, backgroundColor: flash.tint }]}
            pointerEvents="none"
          >
            <Text style={styles.flashLabel}>{flash.text}</Text>
          </Animated.View>
        )}
      </View>

      <View style={styles.tally}>
        {total === 0 ? (
          <View style={styles.empty}>
            <Text style={styles.emptyTitle}>Nothing counted yet</Text>
            <Text style={styles.emptyDetail}>
              Point the camera at a pack. Every one you scan lands here.
            </Text>
          </View>
        ) : (
          <ScrollView contentContainerStyle={styles.tallyList}>
            {consignment.packs
              .map((pack, position) => ({ pack, line: position + 1 }))
              .reverse()
              .map(({ pack, line }, position) => (
                <TallyRow
                  key={pack.serial}
                  index={line}
                  serial={pack.serial}
                  status={pack.status}
                  fresh={position === 0}
                  onPress={() => onRemove(pack.serial)}
                />
              ))}
          </ScrollView>
        )}
      </View>

      <View style={[styles.footer, { paddingBottom: insets.bottom + space.md }]}>
        <View style={styles.summary}>
          <View style={styles.countBlock}>
            <Text style={styles.count}>{total}</Text>
            <Text style={styles.countLabel}>
              {total === 1 ? "pack" : "packs"}
            </Text>
          </View>

          <View style={styles.breakdown}>
            {(["known", "held", "unknown", "pending"] as const)
              .filter((status) => counts[status] > 0)
              .map((status) => (
                <View key={status} style={styles.breakdownRow}>
                  <View style={[styles.pip, { backgroundColor: PACK[status].tint }]} />
                  <Text style={styles.breakdownCount}>{counts[status]}</Text>
                  <Text style={styles.breakdownLabel}>{PACK[status].label}</Text>
                </View>
              ))}
          </View>
        </View>

        <View style={styles.actions}>
          <Button
            label="Type a code"
            onPress={onManualEntry}
            tone="quiet"
            style={styles.actionSecondary}
          />
          <Button
            label="Done"
            onPress={onFinish}
            disabled={total === 0}
            style={styles.actionPrimary}
          />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.docket },
  head: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    paddingHorizontal: space.lg,
    paddingBottom: space.md,
    backgroundColor: color.ledger,
  },
  back: {
    width: 38,
    height: 38,
    borderRadius: radius.sm,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(255,255,255,0.14)",
  },
  backLabel: { fontFamily: font.medium, fontSize: 19, color: color.onColor },
  headText: { flex: 1, gap: 1 },
  headTitle: {
    fontFamily: font.display,
    fontSize: type.bodyLarge,
    color: color.onColor,
    letterSpacing: -0.3,
  },
  camera: { backgroundColor: "#08222A", overflow: "hidden" },
  cameraOff: {
    alignItems: "center",
    justifyContent: "center",
    gap: space.lg,
    paddingHorizontal: space.xl,
  },
  cameraOffLabel: {
    fontFamily: font.medium,
    fontSize: type.body,
    lineHeight: 22,
    color: "rgba(255,255,255,0.9)",
    textAlign: "center",
  },
  frameArea: {
    ...StyleSheet.absoluteFillObject,
    alignItems: "center",
    justifyContent: "center",
  },
  torch: {
    position: "absolute",
    right: space.lg,
    bottom: space.lg,
    paddingVertical: space.sm,
    paddingHorizontal: space.lg,
    borderRadius: radius.pill,
    borderWidth: 1.5,
    borderColor: "rgba(255,255,255,0.45)",
  },
  torchOn: { backgroundColor: color.onColor, borderColor: color.onColor },
  torchLabel: {
    fontFamily: font.semi,
    fontSize: type.caption,
    color: color.onColor,
  },
  flash: {
    position: "absolute",
    left: space.lg,
    right: space.lg,
    top: space.lg,
    paddingVertical: space.md,
    borderRadius: radius.sm,
    alignItems: "center",
  },
  flashLabel: {
    fontFamily: font.semi,
    fontSize: type.body,
    color: color.onColor,
    letterSpacing: 0.2,
  },
  tally: { flex: 1, backgroundColor: color.surface },
  tallyList: { paddingBottom: space.lg },
  empty: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: space.sm,
    paddingHorizontal: space.xxl,
  },
  emptyTitle: {
    fontFamily: font.semi,
    fontSize: type.bodyLarge,
    color: color.inkSoft,
  },
  emptyDetail: {
    fontFamily: font.regular,
    fontSize: type.caption,
    lineHeight: 19,
    color: color.faint,
    textAlign: "center",
  },
  footer: {
    paddingHorizontal: space.lg,
    paddingTop: space.md,
    gap: space.md,
    backgroundColor: color.docket,
    borderTopWidth: 1,
    borderTopColor: color.rule,
  },
  summary: { flexDirection: "row", alignItems: "center", gap: space.lg },
  countBlock: { flexDirection: "row", alignItems: "baseline", gap: 6 },
  count: {
    fontFamily: font.monoBold,
    fontSize: type.tally,
    color: color.ink,
    letterSpacing: -1.5,
  },
  countLabel: {
    fontFamily: font.regular,
    fontSize: type.caption,
    color: color.muted,
  },
  breakdown: { flex: 1, gap: 2 },
  breakdownRow: { flexDirection: "row", alignItems: "center", gap: 7 },
  pip: { width: 7, height: 7, borderRadius: radius.pill },
  breakdownCount: {
    fontFamily: font.monoBold,
    fontSize: type.caption,
    color: color.ink,
    minWidth: 18,
  },
  breakdownLabel: {
    fontFamily: font.regular,
    fontSize: type.caption,
    color: color.muted,
  },
  actions: { flexDirection: "row", gap: space.sm },
  actionSecondary: { flex: 1 },
  actionPrimary: { flex: 1.4 },
});
