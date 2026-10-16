import { formatLocalDate } from "./questionnaire";

const PARTICIPANT_ID_KEY = "mindtrace.participant-id.v1";
const PARTICIPANT_ID_PATTERN = /^MT-\d{8}-[A-HJ-NP-Z2-9]{6}$/;
const ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

type StorageLike = Pick<Storage, "getItem" | "setItem">;

function randomSuffix() {
  const values = new Uint8Array(6);
  globalThis.crypto.getRandomValues(values);
  return [...values].map((value) => ID_ALPHABET[value % ID_ALPHABET.length]).join("");
}

export function createParticipantId(now = new Date(), suffix = randomSuffix()) {
  const enrollmentDate = formatLocalDate(now).replaceAll("-", "");
  return `MT-${enrollmentDate}-${suffix}`;
}

export function getOrCreateParticipantId(storage: StorageLike = window.localStorage) {
  try {
    const existing = storage.getItem(PARTICIPANT_ID_KEY)?.trim().toUpperCase();
    if (existing && PARTICIPANT_ID_PATTERN.test(existing)) return existing;
    const created = createParticipantId();
    storage.setItem(PARTICIPANT_ID_KEY, created);
    return created;
  } catch {
    return createParticipantId();
  }
}

export function completedTestCountKey(participantId: string) {
  return `mindtrace.completed-tests.v1.${participantId}`;
}

function readCompletedTestCount(participantId: string, storage: StorageLike) {
  const parsed = Number.parseInt(storage.getItem(completedTestCountKey(participantId)) ?? "0", 10);
  return Number.isSafeInteger(parsed) && parsed >= 0 ? parsed : 0;
}

export function getNextTestNumber(participantId: string, storage: StorageLike = window.localStorage) {
  try {
    return readCompletedTestCount(participantId, storage) + 1;
  } catch {
    return 1;
  }
}

export function markTestCompleted(participantId: string, testNumber: number, storage: StorageLike = window.localStorage) {
  try {
    const completed = readCompletedTestCount(participantId, storage);
    storage.setItem(completedTestCountKey(participantId), String(Math.max(completed, testNumber)));
  } catch {
    // The exported package still records the test number when local storage is unavailable.
  }
}

export function formatTestNumber(testNumber: number) {
  return `T${String(testNumber).padStart(3, "0")}`;
}
