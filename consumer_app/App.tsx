import {
  PlusJakartaSans_500Medium,
  PlusJakartaSans_600SemiBold,
  PlusJakartaSans_700Bold,
  PlusJakartaSans_800ExtraBold,
  useFonts,
} from "@expo-google-fonts/plus-jakarta-sans";
import * as Haptics from "expo-haptics";
import * as Linking from "expo-linking";
import * as Location from "expo-location";
import { StatusBar } from "expo-status-bar";
import { useCallback, useEffect, useState } from "react";
import { Platform, StyleSheet, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { NetworkUnavailableError, verify, type ScanLocation } from "./src/api/client";
import { BootScreen } from "./src/screens/BootScreen";
import { HelpScreen } from "./src/screens/HelpScreen";
import { HomeScreen } from "./src/screens/HomeScreen";
import { HistoryScreen } from "./src/screens/HistoryScreen";
import { ManualEntryScreen } from "./src/screens/ManualEntryScreen";
import { ResultScreen } from "./src/screens/ResultScreen";
import { ScanScreen } from "./src/screens/ScanScreen";
import { readScannedCode } from "./src/lib/code";
import { clearHistory, readHistory, recordScan, type HistoryEntry } from "./src/lib/history";
import { color, type VerificationState } from "./src/theme";

type Screen = "home" | "scan" | "manual" | "result" | "history" | "help";

interface Outcome {
  state: VerificationState;
  message: string;
  serial: string;
  checkedAt: string;
}

/**
 * Best-effort location for one check.
 *
 * Deliberately never blocks: a cached fix is used if one exists, permission is
 * asked for once, and every failure path returns nothing rather than stalling
 * the answer the person is waiting for.
 */
async function currentLocation(): Promise<ScanLocation | null> {
  try {
    const { granted } = await Location.requestForegroundPermissionsAsync();
    if (!granted) return null;
    const fix =
      (await Location.getLastKnownPositionAsync({ maxAge: 120_000 })) ??
      (await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.Balanced,
      }));
    if (!fix) return null;
    return {
      longitude: fix.coords.longitude,
      latitude: fix.coords.latitude,
      reported_accuracy_m: fix.coords.accuracy ?? undefined,
    };
  } catch {
    return null;
  }
}

function feedback(state: VerificationState) {
  if (Platform.OS === "web") return;
  const style =
    state === "GENUINE"
      ? Haptics.NotificationFeedbackType.Success
      : state === "CAUTION"
        ? Haptics.NotificationFeedbackType.Warning
        : Haptics.NotificationFeedbackType.Error;
  Haptics.notificationAsync(style).catch(() => undefined);
}

export default function App() {
  const [fontsReady] = useFonts({
    PlusJakartaSans_500Medium,
    PlusJakartaSans_600SemiBold,
    PlusJakartaSans_700Bold,
    PlusJakartaSans_800ExtraBold,
  });

  const [screen, setScreen] = useState<Screen>("home");
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    readHistory().then(setHistory);
  }, []);

  const runCheck = useCallback(async (raw: string) => {
    const { payload, serial } = readScannedCode(raw);
    setBusy(true);
    setError(null);
    try {
      const result = await verify(payload, await currentLocation());
      const next: Outcome = {
        state: result.state,
        message: result.message,
        serial,
        checkedAt: result.checked_at,
      };
      setOutcome(next);
      feedback(result.state);
      setHistory(
        await recordScan({
          serial,
          state: result.state,
          checkedAt: result.checked_at,
        }),
      );
      setScreen("result");
    } catch (cause) {
      setError(
        cause instanceof NetworkUnavailableError
          ? cause.message
          : "Something went wrong. Please try again.",
      );
      setScreen("manual");
    } finally {
      setBusy(false);
    }
  }, []);

  // A pack's QR code is an ordinary https URL, so scanning it with the phone's
  // own camera can open this app directly. Treat that exactly like a scan.
  const deepLink = Linking.useURL();
  useEffect(() => {
    if (deepLink && deepLink.includes("bhs=")) {
      runCheck(deepLink);
    }
  }, [deepLink, runCheck]);

  if (!fontsReady) {
    return <BootScreen />;
  }

  return (
    <SafeAreaProvider>
      <StatusBar style={screen === "scan" || screen === "result" ? "light" : "dark"} />
      <View style={styles.root}>
        {screen === "home" && (
          <HomeScreen
            history={history}
            onScan={() => setScreen("scan")}
            onManualEntry={() => {
              setError(null);
              setScreen("manual");
            }}
            onHistory={() => setScreen("history")}
            onHelp={() => setScreen("help")}
          />
        )}

        {screen === "scan" && (
          <ScanScreen
            busy={busy}
            onCode={runCheck}
            onBack={() => setScreen("home")}
            onManualEntry={() => {
              setError(null);
              setScreen("manual");
            }}
            onHistory={() => setScreen("history")}
            onHelp={() => setScreen("help")}
          />
        )}

        {screen === "manual" && (
          <ManualEntryScreen
            busy={busy}
            error={error}
            onCheck={runCheck}
            onBack={() => {
              setError(null);
              setScreen("scan");
            }}
          />
        )}

        {screen === "result" && outcome && (
          <ResultScreen
            {...outcome}
            onScanAnother={() => setScreen("scan")}
            onHelp={() => setScreen("help")}
          />
        )}

        {screen === "history" && (
          <HistoryScreen
            entries={history}
            onBack={() => setScreen("home")}
            onClear={async () => {
              await clearHistory();
              setHistory([]);
            }}
          />
        )}

        {screen === "help" && <HelpScreen onBack={() => setScreen("home")} />}
      </View>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.paper },
});
