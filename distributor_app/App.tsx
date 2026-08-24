import {
  IBMPlexMono_400Regular,
  IBMPlexMono_500Medium,
  IBMPlexMono_600SemiBold,
} from "@expo-google-fonts/ibm-plex-mono";
import {
  IBMPlexSans_400Regular,
  IBMPlexSans_500Medium,
  IBMPlexSans_600SemiBold,
  IBMPlexSans_700Bold,
  useFonts,
} from "@expo-google-fonts/ibm-plex-sans";
import * as Haptics from "expo-haptics";
import { StatusBar } from "expo-status-bar";
import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Platform, StyleSheet, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import {
  currentCustodian,
  listParticipants,
  resolveSerial,
  type Participant,
} from "./src/api/client";
import { readScannedCode } from "./src/lib/code";
import {
  containsSerial,
  newConsignment,
  statusFor,
  type Consignment,
} from "./src/lib/consignment";
import {
  discard,
  enqueue,
  flush,
  pendingCount,
  readOutbox,
  rejectedCount,
  type OutboxEntry,
} from "./src/lib/outbox";
import {
  connectionFor,
  forgetDevice,
  readDevice,
  saveDevice,
  type Device,
} from "./src/lib/session";
import { BootScreen } from "./src/screens/BootScreen";
import { ConnectScreen, type Draft } from "./src/screens/ConnectScreen";
import { HomeScreen } from "./src/screens/HomeScreen";
import { IdentifyScreen } from "./src/screens/IdentifyScreen";
import { ManualEntryScreen } from "./src/screens/ManualEntryScreen";
import { MovementSetupScreen } from "./src/screens/MovementSetupScreen";
import { OutboxScreen } from "./src/screens/OutboxScreen";
import { RecordedScreen, type RecordedSummary } from "./src/screens/RecordedScreen";
import { ReviewScreen } from "./src/screens/ReviewScreen";
import { ScanScreen, type ScanOutcome } from "./src/screens/ScanScreen";
import { SettingsScreen } from "./src/screens/SettingsScreen";
import { MOVEMENT, color, type MovementKind } from "./src/theme";

type Screen =
  | "connect"
  | "identify"
  | "home"
  | "setup"
  | "scan"
  | "manual"
  | "review"
  | "recorded"
  | "outbox"
  | "settings";

function tap(style: Haptics.ImpactFeedbackStyle) {
  if (Platform.OS === "web") return;
  Haptics.impactAsync(style).catch(() => undefined);
}

function notify(style: Haptics.NotificationFeedbackType) {
  if (Platform.OS === "web") return;
  Haptics.notificationAsync(style).catch(() => undefined);
}

export default function App() {
  const [fontsReady] = useFonts({
    IBMPlexSans_400Regular,
    IBMPlexSans_500Medium,
    IBMPlexSans_600SemiBold,
    IBMPlexSans_700Bold,
    IBMPlexMono_400Regular,
    IBMPlexMono_500Medium,
    IBMPlexMono_600SemiBold,
  });

  const [restored, setRestored] = useState(false);
  const [device, setDevice] = useState<Device | null>(null);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);

  const [screen, setScreen] = useState<Screen>("connect");
  const [kind, setKind] = useState<MovementKind>("RECEIPT");
  const [consignment, setConsignment] = useState<Consignment | null>(null);
  const [outbox, setOutbox] = useState<OutboxEntry[]>([]);
  const [summary, setSummary] = useState<RecordedSummary | null>(null);
  const [busy, setBusy] = useState(false);

  // Scan resolution is asynchronous and a storeman scans faster than a round
  // trip completes, so dedupe reads this rather than the state a closure
  // happened to capture.
  const consignmentRef = useRef<Consignment | null>(null);
  consignmentRef.current = consignment;

  useEffect(() => {
    (async () => {
      const [stored, entries] = await Promise.all([readDevice(), readOutbox()]);
      setDevice(stored);
      setOutbox(entries);
      setScreen(stored ? "home" : "connect");
      setRestored(true);

      // Anything left over from the last shift goes out as soon as the app is
      // opened somewhere with a signal, without anyone having to remember.
      if (stored && pendingCount(entries) > 0) {
        await flush(connectionFor(stored));
        setOutbox(await readOutbox());
      }
    })();
  }, []);

  // The participant list is fetched once per launch so the setup screen has
  // somewhere to send stock even if the depot loses signal mid-shift.
  useEffect(() => {
    if (!device) return;
    listParticipants(connectionFor(device))
      .then(setParticipants)
      .catch(() => undefined);
  }, [device]);

  const updatePack = useCallback(
    (serial: string, patch: Partial<Consignment["packs"][number]>) => {
      setConsignment((current) =>
        current
          ? {
              ...current,
              packs: current.packs.map((pack) =>
                pack.serial === serial ? { ...pack, ...patch } : pack,
              ),
            }
          : current,
      );
    },
    [],
  );

  /**
   * Adds one scanned pack, then works out what the platform knows about it.
   *
   * The line appears immediately and is corrected a moment later, rather than
   * the storeman waiting on two round trips per pack with a lorry running. A
   * device with no signal simply never gets past the first state, which is
   * why `pending` is a status a pack can legitimately be recorded in.
   */
  const handleCode = useCallback(
    async (raw: string): Promise<ScanOutcome> => {
      const open = consignmentRef.current;
      if (!device || !open) return "unreadable";

      const serial = readScannedCode(raw);
      if (!serial) {
        notify(Haptics.NotificationFeedbackType.Error);
        return "unreadable";
      }
      if (containsSerial(open, serial)) {
        notify(Haptics.NotificationFeedbackType.Warning);
        return "duplicate";
      }

      const pack = {
        serial,
        identityId: null,
        status: "pending" as const,
        scannedAt: new Date().toISOString(),
      };
      const next = { ...open, packs: [...open.packs, pack] };
      consignmentRef.current = next;
      setConsignment(next);
      tap(Haptics.ImpactFeedbackStyle.Medium);

      try {
        const connection = connectionFor(device);
        const identity = await resolveSerial(connection, serial);
        if (!identity) {
          updatePack(serial, { status: "unknown" });
          notify(Haptics.NotificationFeedbackType.Error);
          return "added";
        }

        const { custodian_id } = await currentCustodian(connection, identity.id);
        const status = statusFor(next, custodian_id);
        updatePack(serial, { identityId: identity.id, status });
        if (status === "held") notify(Haptics.NotificationFeedbackType.Warning);
      } catch {
        // Offline, or the server refused the lookup. The pack stays pending
        // and is resolved again when the outbox drains.
      }

      return "added";
    },
    [device, updatePack],
  );

  const removePack = useCallback((serial: string) => {
    Alert.alert("Remove this pack?", "It will not be recorded as part of this movement.", [
      { text: "Keep it", style: "cancel" },
      {
        text: "Remove",
        style: "destructive",
        onPress: () =>
          setConsignment((current) =>
            current
              ? { ...current, packs: current.packs.filter((p) => p.serial !== serial) }
              : current,
          ),
      },
    ]);
  }, []);

  function startMovement(next: MovementKind) {
    if (!device) return;
    setKind(next);
    if (MOVEMENT[next].needs === "none") {
      setConsignment(newConsignment(next, device.participant.id, null));
      setScreen("scan");
      return;
    }
    setScreen("setup");
  }

  async function commit() {
    if (!device || !consignment) return;
    setBusy(true);
    try {
      const connection = connectionFor(device);
      await enqueue(consignment);
      await flush(connection);

      const entries = await readOutbox();
      setOutbox(entries);

      // An entry every event of which was accepted is dropped by the flush, so
      // its absence here is what "all sent" looks like.
      const remaining = entries.find((entry) => entry.id === consignment.id);
      const total = consignment.packs.length;
      const queued = remaining?.events.filter((e) => e.state === "queued").length ?? 0;
      const rejected = remaining?.events.filter((e) => e.state === "rejected").length ?? 0;

      setSummary({
        kind: consignment.kind,
        counterpartyName: consignment.counterpartyName,
        total,
        sent: total - queued - rejected,
        queued,
        rejected,
      });
      notify(
        rejected > 0
          ? Haptics.NotificationFeedbackType.Warning
          : Haptics.NotificationFeedbackType.Success,
      );
      setConsignment(null);
      setScreen("recorded");
    } finally {
      setBusy(false);
    }
  }

  async function sendOutbox() {
    if (!device) return;
    setBusy(true);
    try {
      await flush(connectionFor(device));
      setOutbox(await readOutbox());
    } finally {
      setBusy(false);
    }
  }

  function unbind() {
    Alert.alert(
      "Unbind this device?",
      "You will have to set it up again before it can record anything. Movements it has not sent stay on the device.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Unbind",
          style: "destructive",
          onPress: async () => {
            await forgetDevice();
            setDevice(null);
            setParticipants([]);
            setDraft(null);
            setScreen("connect");
          },
        },
      ],
    );
  }

  if (!fontsReady || !restored) return <BootScreen />;

  const pending = pendingCount(outbox);
  const rejected = rejectedCount(outbox);
  const dark = screen === "scan";

  return (
    <SafeAreaProvider>
      <StatusBar style={dark ? "light" : "dark"} />
      <View style={styles.root}>
        {screen === "connect" && (
          <ConnectScreen
            onConnected={(nextDraft, found) => {
              setDraft(nextDraft);
              setParticipants(found);
              setScreen("identify");
            }}
          />
        )}

        {screen === "identify" && draft && (
          <IdentifyScreen
            participants={participants}
            onBack={() => setScreen("connect")}
            onChoose={async (participant) => {
              const next: Device = { ...draft, participant };
              await saveDevice(next);
              setDevice(next);
              setScreen("home");
            }}
          />
        )}

        {screen === "home" && device && (
          <HomeScreen
            device={device}
            pending={pending}
            rejected={rejected}
            onStart={startMovement}
            onOutbox={() => setScreen("outbox")}
            onSettings={() => setScreen("settings")}
          />
        )}

        {screen === "setup" && device && (
          <MovementSetupScreen
            kind={kind}
            participants={participants}
            selfId={device.participant.id}
            onBack={() => setScreen("home")}
            onStart={(counterparty) => {
              setConsignment(
                newConsignment(kind, device.participant.id, {
                  id: counterparty.id,
                  name: counterparty.name,
                }),
              );
              setScreen("scan");
            }}
          />
        )}

        {screen === "scan" && consignment && (
          <ScanScreen
            consignment={consignment}
            onCode={handleCode}
            onRemove={removePack}
            onManualEntry={() => setScreen("manual")}
            onFinish={() => setScreen("review")}
            onBack={() => {
              if (consignment.packs.length === 0) {
                setConsignment(null);
                setScreen("home");
                return;
              }
              Alert.alert(
                "Leave this consignment?",
                `${consignment.packs.length} scanned ${
                  consignment.packs.length === 1 ? "pack" : "packs"
                } will be discarded. Nothing has been recorded yet.`,
                [
                  { text: "Keep scanning", style: "cancel" },
                  {
                    text: "Discard",
                    style: "destructive",
                    onPress: () => {
                      setConsignment(null);
                      setScreen("home");
                    },
                  },
                ],
              );
            }}
          />
        )}

        {screen === "manual" && (
          <ManualEntryScreen onSubmit={handleCode} onBack={() => setScreen("scan")} />
        )}

        {screen === "review" && consignment && (
          <ReviewScreen
            consignment={consignment}
            busy={busy}
            onCommit={commit}
            onBack={() => setScreen("scan")}
          />
        )}

        {screen === "recorded" && summary && (
          <RecordedScreen
            summary={summary}
            onDone={() => setScreen("home")}
            onOutbox={() => setScreen("outbox")}
          />
        )}

        {screen === "outbox" && (
          <OutboxScreen
            entries={outbox}
            busy={busy}
            onSend={sendOutbox}
            onDiscard={async (entryId) => setOutbox(await discard(entryId))}
            onBack={() => setScreen("home")}
          />
        )}

        {screen === "settings" && device && (
          <SettingsScreen
            device={device}
            pending={pending}
            onUnbind={unbind}
            onBack={() => setScreen("home")}
          />
        )}
      </View>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.docket },
});
