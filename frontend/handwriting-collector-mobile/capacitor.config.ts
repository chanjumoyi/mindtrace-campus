import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.mindtrace.collector",
  appName: "心迹书写采集",
  webDir: "dist/client",
  plugins: {
    // MainActivity applies the real status-bar inset as CSS variables and
    // keeps the navigation bar hidden, so Capacitor's native inset padding
    // would leave an empty black strip at the bottom.
    SystemBars: {
      insetsHandling: "disable",
    },
  },
};

export default config;
