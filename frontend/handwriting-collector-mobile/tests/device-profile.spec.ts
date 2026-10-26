import { expect, test } from "@playwright/test";
import { buildDeviceProfile } from "../src/deviceProfile";

const environment = {
  userAgent: "Synthetic WebView/1.0",
  platform: "Synthetic Android",
  maxTouchPoints: 5,
  devicePixelRatio: 3,
  screen: { width: 360, height: 800 },
};

test("reported environment profiles survive screen rotation without claiming calibrated hardware", () => {
  const profile = buildDeviceProfile(environment);
  expect(buildDeviceProfile({ ...environment, screen: { width: 800, height: 360 } })).toEqual(profile);
  expect(profile.deviceProfileId).toMatch(/^unverified-web-v1-[0-9a-f]{16}$/);
  expect(profile).toMatchObject({
    profileSource: "reported_environment", calibrationStatus: "unverified", physicalDeviceVerified: false,
  });
  expect(buildDeviceProfile({ ...environment, userAgent: "Synthetic WebView/2.0" }).deviceProfileId)
    .not.toBe(profile.deviceProfileId);
});

test("a study can link attempts to an inventoried profile without asserting sensor calibration", () => {
  expect(buildDeviceProfile(environment, " LAB-TABLET-A ")).toMatchObject({
    deviceProfileId: "LAB-TABLET-A", profileSource: "study_configuration",
    calibrationStatus: "unverified", physicalDeviceVerified: false,
  });
  expect(buildDeviceProfile(environment, " ")).toEqual(buildDeviceProfile(environment));
});
