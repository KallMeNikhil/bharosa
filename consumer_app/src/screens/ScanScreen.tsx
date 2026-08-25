import { CameraView, useCameraPermissions } from "expo-camera";
import { useCallback, useRef, useState } from "react";
import {
  Platform,
  Pressable,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ScanFrame } from "../components/Glyph";
import { Button, Eyebrow, TextLink } from "../components/ui";
import { color, font, radius, space, type } from "../theme";

interface ScanScreenProps {
  onCode: (raw: string) => void;
  onBack: () => void;
  onManualEntry: () => void;
  onHistory: () => void;
  onHelp: () => void;
  busy: boolean;
}

export function ScanScreen({
  onCode,
  onBack,
  onManualEntry,
  onHistory,
  onHelp,
  busy,
}: ScanScreenProps) {
  const insets = useSafeAreaInsets();
  const { width, height } = useWindowDimensions();
  const [permission, requestPermission] = useCameraPermissions();
  const [torch, setTorch] = useState(false);
  const claimed = useRef(false);

  const frameSize = Math.min(width * 0.74, height * 0.42);

  const handleBarcode = useCallback(
    ({ data }: { data: string }) => {
      // The camera fires continuously while a code is in view; the first read
      // wins and the rest are dropped until the screen is shown again.
      if (claimed.current || busy) return;
      claimed.current = true;
      onCode(data);
      setTimeout(() => {
        claimed.current = false;
      }, 1500);
    },
    [busy, onCode],
  );

  const cameraUsable = permission?.granted && Platform.OS !== "web";

  return (
    <View style={styles.root}>
      {cameraUsable ? (
        <CameraView
          style={StyleSheet.absoluteFill}
          facing="back"
          enableTorch={torch}
          barcodeScannerSettings={{ barcodeTypes: ["qr", "datamatrix"] }}
          onBarcodeScanned={handleBarcode}
        />
      ) : (
        <View style={[StyleSheet.absoluteFill, styles.cameraFallback]} />
      )}

      <View style={[styles.scrim, { paddingTop: insets.top + space.lg }]}>
        <View style={styles.header}>
          <View>
            <Eyebrow tint="rgba(255,255,255,0.65)">Bharosa</Eyebrow>
            <Text style={styles.title}>Check a pack</Text>
          </View>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Close scanner"
            onPress={onBack}
            hitSlop={12}
            style={styles.headerAction}
          >
            <Text style={styles.headerActionLabel}>Close</Text>
          </Pressable>
        </View>
      </View>

      <View style={styles.frameArea} pointerEvents="none">
        <ScanFrame size={frameSize} color="#FFFFFF" />
      </View>

      <View style={[styles.footer, { paddingBottom: insets.bottom + space.xl }]}>
        {!permission?.granted && Platform.OS !== "web" ? (
          <>
            <Text style={styles.instruction}>
              Bharosa needs the camera to read the code printed on the pack.
            </Text>
            <Button label="Allow camera" onPress={requestPermission} tone="onField" />
          </>
        ) : (
          <Text style={styles.instruction}>
            {Platform.OS === "web"
              ? "Camera scanning needs the phone app. Enter the code instead."
              : "Point the camera at the QR code on the pack."}
          </Text>
        )}

        <View style={styles.footerActions}>
          {cameraUsable && (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={torch ? "Turn torch off" : "Turn torch on"}
              onPress={() => setTorch((on) => !on)}
              style={[styles.torch, torch && styles.torchOn]}
            >
              <Text style={[styles.torchLabel, torch && { color: color.ink }]}>
                {torch ? "Light on" : "Light"}
              </Text>
            </Pressable>
          )}
          <TextLink
            label="Enter the code instead"
            onPress={onManualEntry}
            color="#FFFFFF"
          />
        </View>

        <TextLink label="What do the results mean?" onPress={onHelp} color="rgba(255,255,255,0.75)" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.ink },
  cameraFallback: { backgroundColor: "#0A1712" },
  scrim: {
    paddingHorizontal: space.xl,
    paddingBottom: space.lg,
    backgroundColor: "rgba(11,20,16,0.55)",
  },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
  },
  title: {
    fontFamily: font.display,
    fontSize: type.headline,
    color: color.onColor,
    marginTop: 2,
    letterSpacing: -0.6,
  },
  headerAction: {
    paddingVertical: space.sm,
    paddingHorizontal: space.md,
    borderRadius: radius.pill,
    backgroundColor: "rgba(255,255,255,0.16)",
  },
  headerActionLabel: {
    fontFamily: font.semi,
    fontSize: type.caption,
    color: color.onColor,
  },
  frameArea: { flex: 1, alignItems: "center", justifyContent: "center" },
  footer: {
    paddingHorizontal: space.xl,
    paddingTop: space.xl,
    gap: space.lg,
    alignItems: "center",
    backgroundColor: "rgba(11,20,16,0.72)",
  },
  instruction: {
    fontFamily: font.medium,
    fontSize: type.bodyLarge,
    lineHeight: 24,
    color: "rgba(255,255,255,0.92)",
    textAlign: "center",
  },
  footerActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.lg,
    flexWrap: "wrap",
    justifyContent: "center",
  },
  torch: {
    paddingVertical: space.sm + 2,
    paddingHorizontal: space.lg,
    borderRadius: radius.pill,
    borderWidth: 2,
    borderColor: "rgba(255,255,255,0.4)",
  },
  torchOn: { backgroundColor: color.onColor, borderColor: color.onColor },
  torchLabel: {
    fontFamily: font.semi,
    fontSize: type.caption,
    color: color.onColor,
  },
});
