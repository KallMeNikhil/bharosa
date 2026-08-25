import AsyncStorage from "@react-native-async-storage/async-storage";

import { buildCredential, type Connection, type Participant } from "../api/client";

const STORAGE_KEY = "bharosa.distributor.device";

export interface Device {
  baseUrl: string;
  manufacturerId: string;
  actorId: string;
  participant: Participant;
}

export function connectionFor(device: {
  baseUrl: string;
  manufacturerId: string;
  actorId: string;
}): Connection {
  return {
    baseUrl: device.baseUrl.replace(/\/+$/, ""),
    credential: buildCredential(device.manufacturerId, device.actorId),
  };
}

export async function readDevice(): Promise<Device | null> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Device) : null;
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
