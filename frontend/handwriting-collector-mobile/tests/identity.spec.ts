import { expect, test } from "@playwright/test";
import {
  completedTestCountKey,
  createParticipantId,
  formatTestNumber,
  getNextTestNumber,
  getOrCreateParticipantId,
  markTestCompleted,
} from "../src/identity";

class MemoryStorage {
  private readonly values = new Map<string, string>();
  getItem(key: string) { return this.values.get(key) ?? null; }
  setItem(key: string, value: string) { this.values.set(key, value); }
}

test("participant IDs have a readable enrollment date and stable suffix", () => {
  expect(createParticipantId(new Date(2026, 9, 16), "ABC234")).toBe("MT-20261016-ABC234");
});

test("the same local installation reuses its participant ID", () => {
  const storage = new MemoryStorage();
  const first = getOrCreateParticipantId(storage);
  const second = getOrCreateParticipantId(storage);
  expect(first).toBe(second);
  expect(first).toMatch(/^MT-\d{8}-[A-HJ-NP-Z2-9]{6}$/);
});

test("test numbers advance only after a completed save", () => {
  const storage = new MemoryStorage();
  const participantId = "MT-20261016-ABC234";
  expect(getNextTestNumber(participantId, storage)).toBe(1);
  markTestCompleted(participantId, 1, storage);
  expect(storage.getItem(completedTestCountKey(participantId))).toBe("1");
  expect(getNextTestNumber(participantId, storage)).toBe(2);
  markTestCompleted(participantId, 1, storage);
  expect(getNextTestNumber(participantId, storage)).toBe(2);
  expect(formatTestNumber(2)).toBe("T002");
});
