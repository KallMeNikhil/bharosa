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
  signIn,
  whoami,
  type Participant,
} from "../api/client";
import { Lockup } from "../components/Logo";
import { Button, Field, Notice } from "../components/ui";
import { connectionFor } from "../lib/session";
import { color, font, space, type } from "../theme";

export interface Draft {
  baseUrl: string;
  token: string;
  manufacturerId: string;
  manufacturerName: string;
  actorId: string;
}

export function ConnectScreen({
  notice,
  onConnected,
}: {
  notice?: string | null;
  onConnected: (draft: Draft, participants: Participant[]) => void;
}) {
  const insets = useSafeAreaInsets();
  const [baseUrl, setBaseUrl] = useState(DEFAULT_BASE_URL);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ready = baseUrl.trim() !== "" && email.trim() !== "" && password !== "";

  async function connect() {
    setBusy(true);
    setError(null);
    const address = baseUrl.trim().replace(/\/+$/, "");

    try {
      const signedIn = await signIn(address, email.trim(), password);
      const draft: Draft = {
        baseUrl: address,
        token: signedIn.token,
        manufacturerId: signedIn.manufacturer.id,
        manufacturerName: signedIn.manufacturer.name,
        actorId: signedIn.account.email,
      };
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
            Sign in with your company's Bharosa account once. After that it
            stays signed in and works without a connection, sending what it has
            recorded when the signal comes back.
          </Text>
        </View>

        {notice && <Notice text={notice} />}

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
            label="Email"
            value={email}
            onChangeText={setEmail}
            placeholder="you@company.com"
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
          />
          <Field
            label="Password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoCapitalize="none"
            autoComplete="password"
            onSubmitEditing={ready ? connect : undefined}
          />
        </View>

        {error && <Notice text={error} />}

        <Button label="Sign in" onPress={connect} disabled={!ready} busy={busy} />

        <Text style={styles.footnote}>
          This device signs in with your company account, so keep it with
          staff you trust. Unbinding it in Settings ends its session.
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
