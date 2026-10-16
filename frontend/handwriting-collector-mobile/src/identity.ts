export const ADMIN_TEST_ID = "AD-24-MAST";
export const GRADE_OPTIONS = ["23", "24", "25", "26"] as const;
export const CHINA_PROVINCES = [
  { code: "110000", label: "北京市" }, { code: "120000", label: "天津市" }, { code: "130000", label: "河北省" },
  { code: "140000", label: "山西省" }, { code: "150000", label: "内蒙古自治区" }, { code: "210000", label: "辽宁省" },
  { code: "220000", label: "吉林省" }, { code: "230000", label: "黑龙江省" }, { code: "310000", label: "上海市" },
  { code: "320000", label: "江苏省" }, { code: "330000", label: "浙江省" }, { code: "340000", label: "安徽省" },
  { code: "350000", label: "福建省" }, { code: "360000", label: "江西省" }, { code: "370000", label: "山东省" },
  { code: "410000", label: "河南省" }, { code: "420000", label: "湖北省" }, { code: "430000", label: "湖南省" },
  { code: "440000", label: "广东省" }, { code: "450000", label: "广西壮族自治区" }, { code: "460000", label: "海南省" },
  { code: "500000", label: "重庆市" }, { code: "510000", label: "四川省" }, { code: "520000", label: "贵州省" },
  { code: "530000", label: "云南省" }, { code: "540000", label: "西藏自治区" }, { code: "610000", label: "陕西省" },
  { code: "620000", label: "甘肃省" }, { code: "630000", label: "青海省" }, { code: "640000", label: "宁夏回族自治区" },
  { code: "650000", label: "新疆维吾尔自治区" }, { code: "710000", label: "台湾省" },
  { code: "810000", label: "香港特别行政区" }, { code: "820000", label: "澳门特别行政区" },
] as const;

const ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const PARTICIPANT_ID_PATTERN = /^[A-Z]{2}-(23|24|25|26)-[A-Z0-9]{4}$/;
type StorageLike = Pick<Storage, "getItem" | "setItem">;

export type ParticipantProfile = {
  participantId: string;
  collectionMode: "initial" | "follow_up";
  ageYears: number | null;
  grade: typeof GRADE_OPTIONS[number];
  provinceCode: typeof CHINA_PROVINCES[number]["code"] | null;
  provinceLabel: typeof CHINA_PROVINCES[number]["label"] | null;
  profileSource: "created_on_device" | "loaded_from_device" | "unavailable_on_device" | "administrator_test";
  isAdministratorTest: boolean;
  createdAt: string | null;
};

function randomSuffix() {
  const values = new Uint8Array(4);
  globalThis.crypto.getRandomValues(values);
  return [...values].map((value) => ID_ALPHABET[value % ID_ALPHABET.length]).join("");
}

export function createInitialParticipantId(grade: ParticipantProfile["grade"], suffix = randomSuffix()) {
  return `MT-${grade}-${suffix.toUpperCase()}`;
}

export function buildFollowUpParticipantId(prefix: string, grade: string, suffix: string) {
  const participantId = `${prefix.trim().toUpperCase()}-${grade}-${suffix.trim().toUpperCase()}`;
  return PARTICIPANT_ID_PATTERN.test(participantId) ? participantId : null;
}

export function isAdministratorTestId(participantId: string) {
  return participantId === ADMIN_TEST_ID;
}

function profileStorageKey(participantId: string) {
  return `mindtrace.participant-profile.v2.${participantId}`;
}

export function saveParticipantProfile(profile: ParticipantProfile, storage: StorageLike = window.localStorage) {
  try { storage.setItem(profileStorageKey(profile.participantId), JSON.stringify(profile)); } catch { /* keep the active profile in memory */ }
}

export function loadParticipantProfile(participantId: string, storage: StorageLike = window.localStorage): ParticipantProfile | null {
  try {
    const raw = storage.getItem(profileStorageKey(participantId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ParticipantProfile;
    return parsed.participantId === participantId ? parsed : null;
  } catch { return null; }
}

export function completedTestCountKey(participantId: string) {
  return `mindtrace.completed-tests.v2.${participantId}`;
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

export function formatExportTimestamp(date: Date) {
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, "0"), String(date.getDate()).padStart(2, "0"),
    String(date.getHours()).padStart(2, "0"), String(date.getMinutes()).padStart(2, "0")].join("");
}

export function buildExportFilename(participantId: string, collectionCompletedAt: Date) {
  return `${participantId}-${formatExportTimestamp(collectionCompletedAt)}.json`;
}
