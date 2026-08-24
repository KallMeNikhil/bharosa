import AsyncStorage from "@react-native-async-storage/async-storage";

import type { VerificationState } from "../theme";

const STORAGE_KEY = "bharosa.scanHistory";
const MAX_ENTRIES = 60;

export interface HistoryEntry {
  id: string;
  serial: string;
  state: VerificationState;
  checkedAt: string;
}

/**
 * Scan history is kept on the device and never uploaded.
 *
 * The platform already records a verification event server-side when a code
 * resolves; this copy exists so a person can look back at what they checked
 * without the app needing to ask the server anything about them.
 */
export async function readHistory(): Promise<HistoryEntry[]> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as HistoryEntry[]) : [];
  } catch {
    return [];
  }
}

export async function recordScan(
  entry: Omit<HistoryEntry, "id">,
): Promise<HistoryEntry[]> {
  const existing = await readHistory();
  const next = [
    { ...entry, id: `${entry.checkedAt}-${entry.serial}` },
    ...existing,
  ].slice(0, MAX_ENTRIES);
  try {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // A full disk must not lose the person the result they just asked for.
  }
  return next;
}

export async function clearHistory(): Promise<void> {
  await AsyncStorage.removeItem(STORAGE_KEY);
}
