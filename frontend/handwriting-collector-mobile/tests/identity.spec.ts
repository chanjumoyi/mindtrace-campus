import { expect, test } from "@playwright/test";
import {
  ADMIN_TEST_ID,
  buildExportFilename,
  buildFollowUpParticipantId,
  completedTestCountKey,
  createInitialParticipantId,
  formatExportTimestamp,
  formatTestNumber,
  getNextTestNumber,
  isAdministratorTestId,
  loadParticipantProfile,
  markTestCompleted,
  saveParticipantProfile,
  type ParticipantProfile,
} from "../src/identity";

class MemoryStorage {
  private readonly values = new Map<string, string>();
  getItem(key: string) { return this.values.get(key) ?? null; }
  setItem(key: string, value: string) { this.values.set(key, value); }
}

test("initial participant IDs use grade and a four-character suffix", () => {
  expect(createInitialParticipantId("24", "A2K9")).toBe("MT-24-A2K9");
});

test("follow-up IDs are normalized and administrator data is recognizable", () => {
  expect(buildFollowUpParticipantId("ad", "24", "mast")).toBe(ADMIN_TEST_ID);
  expect(buildFollowUpParticipantId("M", "24", "ABC1")).toBeNull();
  expect(buildFollowUpParticipantId("MT", "27", "ABC1")).toBeNull();
  expect(isAdministratorTestId(ADMIN_TEST_ID)).toBe(true);
});

test("an initial demographic profile can be loaded during a later test", () => {
  const storage = new MemoryStorage();
  const profile: ParticipantProfile = { participantId: "MT-24-A2K9", collectionMode: "initial", ageYears: 20,
    grade: "24", provinceCode: "440000", provinceLabel: "广东省", profileSource: "created_on_device",
    isAdministratorTest: false, createdAt: "2026-10-16T12:00:00.000Z" };
  saveParticipantProfile(profile, storage);
  expect(loadParticipantProfile(profile.participantId, storage)).toEqual(profile);
});

test("test numbers advance only after a completed save", () => {
  const storage = new MemoryStorage();
  const participantId = "MT-24-A2K9";
  expect(getNextTestNumber(participantId, storage)).toBe(1);
  markTestCompleted(participantId, 1, storage);
  expect(storage.getItem(completedTestCountKey(participantId))).toBe("1");
  expect(getNextTestNumber(participantId, storage)).toBe(2);
  markTestCompleted(participantId, 1, storage);
  expect(getNextTestNumber(participantId, storage)).toBe(2);
  expect(formatTestNumber(2)).toBe("T002");
});

test("export timestamps use local collection completion time to the minute", () => {
  expect(formatExportTimestamp(new Date(2026, 9, 16, 20, 3, 59))).toBe("202610162003");
  expect(buildExportFilename("MT-24-A2K9", 3, new Date(2026, 9, 16, 20, 3, 59))).toBe("MT-24-A2K9-T003-202610162003.json");
});
