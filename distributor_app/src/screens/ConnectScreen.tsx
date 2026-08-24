import { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import {
  DEFAULT_BASE_URL,
  listParticipants,
  whoami,
  type Participant,
} from "../api/client";
import { Lockup } from "../components/Logo";
import { Button, Field, Notice } from "../components/ui";
import { connectionFor } from "../lib/session";
import { color, font, space, type } from "../theme";

export interface Draft {
  baseUrl: string;
  manufacturerId: string;
  actorId: string;
}

/**
 * First run: binding this scanner to a manufacturer.
 *
 * The device is named rather than the person holding it, because a scanner
 * lives at a loading bay and is used by whoever is on shift. An audit trail
 * that pointed at a name would be pointing at whoever last had the phone,
 * which is worse than useless; one that points at "Bay 2 scanner" points at
 * something a supervisor can walk over to.
 */
export function ConnectScreen({
  onConnected,
}: {
  onConnected: (draft: Draft, participants: Participant[]) => void;
}) {
  const insets = useSafeAreaInsets();
  const [baseUrl, setBaseUrl] = useState(DEFAULT_BASE_URL);
  const [manufacturerId, setManufacturerId] = useState("");
  const [actorId, setActorId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ready = baseUrl.trim() !== "" && manufacturerId.trim() !== "" && actorId.trim() !== "";

  async function connect() {
    setBusy(true);
    setError(null);
    const draft: Draft = {
      baseUrl: baseUrl.trim().replace(/\/+$/, ""),
      manufacturerId: manufacturerId.trim(),
      actorId: actorId.trim(),
    };

    try {
      const connection = connectionFor(draft);
      await whoami(connection);
      const participants = await listParticipants(connection);
      if (participants.length === 0) {
        setError(
          "This manufacturer has no depots, distributors or retailers on record yet. They have to be added in the manufacturer console before a scanner can be bound to one.",
        );
        return;
      }
      onConnected(draft, participants);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Could not connect. Check the address and try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.root}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingTop: insets.top + space.xxl, paddingBottom: insets.bottom + space.xxl },
        ]}
        keyboardShouldPersistTaps="handled"
      >
        <Lockup markSize={34} wordSize={type.title} />

        <View style={styles.intro}>
          <Text style={styles.heading}>Set up this scanner</Text>
          <Text style={styles.blurb}>
            Bind the device once. After that it stays signed in and works
            without a connection, sending what it has recorded when the signal
            comes back.
          </Text>
        </View>

        <View style={styles.form}>
          <Field
            label="Server address"
            value={baseUrl}
            onChangeText={setBaseUrl}
            placeholder="http://192.168.1.3:8000/api/v1"
            keyboardType="url"
            mono
          />
          <Field
            label="Manufacturer ID"
            hint="From the manufacturer console, under the tenant's details."
            value={manufacturerId}
            onChangeText={setManufacturerId}
            placeholder="00000000-0000-0000-0000-000000000000"
            mono
          />
          <Field
            label="Name this device"
            hint="Where the scanner lives, not who is holding it. For example, Bay 2 scanner."
            value={actorId}
            onChangeText={setActorId}
            placeholder="bay-2-scanner"
            onSubmitEditing={ready ? connect : undefined}
          />
        </View>

        {error && <Notice text={error} />}

        <Button label="Connect" onPress={connect} disabled={!ready} busy={busy} />

        <Text style={styles.footnote}>
          This device is granted one permission: recording that a pack moved.
          It cannot register products, issue codes or touch signing keys.
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: color.docket },
  content: { paddingHorizontal: space.xl, gap: space.xl },
  intro: { gap: space.sm },
  heading: {
    fontFamily: font.display,
    fontSize: type.headline,
    letterSpacing: -0.8,
    color: color.ink,
  },
  blurb: {
    fontFamily: font.regular,
    fontSize: type.body,
    lineHeight: 22,
    color: color.muted,
  },
  form: { gap: space.lg },
  footnote: {
    fontFamily: font.regular,
    fontSize: type.caption,
    lineHeight: 19,
    color: color.faint,
    textAlign: "center",
  },
});
