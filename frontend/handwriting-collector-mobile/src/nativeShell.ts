import { Capacitor, SystemBars, SystemBarType } from "@capacitor/core";

export function configureNativeShell() {
  if (!Capacitor.isNativePlatform()) return;
  // Keep the Android navigation bar hidden; MainActivity also re-applies this
  // on focus so the status bar can stay visible while the nav bar does not
  // cover the bottom actions.
  void SystemBars.hide({ bar: SystemBarType.NavigationBar }).catch(() => {});
}
