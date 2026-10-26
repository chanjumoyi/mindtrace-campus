export type InputEnvironment = {
  userAgent: string;
  platform: string;
  maxTouchPoints: number;
  devicePixelRatio: number;
  screen: { width: number; height: number };
};

// This groups reported input environments, not physical devices or calibrated pens.
// A configured study profile takes precedence once hardware has been inventoried.
export function buildDeviceProfile(environment: InputEnvironment, configuredId = "") {
  const signature = JSON.stringify({
    userAgent: environment.userAgent,
    platform: environment.platform,
    maxTouchPoints: environment.maxTouchPoints,
    devicePixelRatio: environment.devicePixelRatio,
    screenSize: [environment.screen.width, environment.screen.height].sort((a, b) => a - b),
  });
  let hash = 0xcbf29ce484222325n;
  for (const byte of new TextEncoder().encode(signature)) {
    hash = BigInt.asUintN(64, (hash ^ BigInt(byte)) * 0x100000001b3n);
  }
  const configured = configuredId.trim();
  return {
    deviceProfileId: configured || `unverified-web-v1-${hash.toString(16).padStart(16, "0")}`,
    profileSource: configured ? "study_configuration" : "reported_environment",
    profileVersion: "input-environment/1.0.0",
    calibrationStatus: "unverified",
    physicalDeviceVerified: false,
  };
}
