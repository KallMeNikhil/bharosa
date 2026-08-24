import AsyncStorage from "@react-native-async-storage/async-storage";

import { buildCredential, type Connection, type Participant } from "../api/client";

const STORAGE_KEY = "bharosa.distributor.device";

/**
 * What this device has been told about itself.
 *
 * A scanner is issued once and then used by whoever is on shift, so the
 * binding is to a place rather than a person: this device belongs to North
 * Depot, and every movement it records is North Depot's. `actorId` names the
 * device, not its operator, so an audit trail points at a physical scanner
 * that can be found and taken away.
 */
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

/**
 * Unbinds the device.
 *
 * Deliberately leaves the outbox alone. Movements that have been recorded but
 * not yet sent are the depot's record of work already done, and handing the
 * scanner to another branch must not be a way to make them disappear.
 */
export async function forgetDevice(): Promise<void> {
  await AsyncStorage.removeItem(STORAGE_KEY);
}
