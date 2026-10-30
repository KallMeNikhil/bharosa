import AsyncStorage from "@react-native-async-storage/async-storage";

import type { Connection, Participant } from "../api/client";

const STORAGE_KEY = "bharosa.distributor.device";

export interface Device {
  baseUrl: string;
  // Session token from signing in with the company account.
  token: string;
  manufacturerId: string;
  manufacturerName: string;
  // The account that signed this device in.
  actorId: string;
  participant: Participant;
}

export function connectionFor(device: { baseUrl: string; token: string }): Connection {
  return {
    baseUrl: device.baseUrl.replace(/\/+$/, ""),
    credential: device.token,
  };
}

export async function readDevice(): Promise<Device | null> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const device = JSON.parse(raw) as Partial<Device>;
    // A device set up before sign-in existed has no token and has to be set
    // up again; the server no longer accepts what it used to send.
    return device.token ? (device as Device) : null;
  } catch {
    return null;
  }
}

export async function saveDevice(device: Device): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(device));
}

export async function forgetDevice(): Promise<void> {
  await AsyncStorage.removeItem(STORAGE_KEY);
}
