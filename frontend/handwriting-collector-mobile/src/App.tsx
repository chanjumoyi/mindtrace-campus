import { Capacitor } from "@capacitor/core";
import { useLayoutEffect } from "react";
import { MobileRuntime } from "./mobile";
import { useMobileDevice } from "./mobile/Device";
import Prototype from "./Prototype";

export default function App() {
  const isNativeAndroid = Capacitor.getPlatform() === "android";
  if (!isNativeAndroid) {
    return <MobileRuntime><Prototype /></MobileRuntime>;
  }

  return (
    <div className="native-shell" data-native-platform="android">
      <MobileRuntime>
        <AndroidDeviceSelection />
        <Prototype />
      </MobileRuntime>
    </div>
  );
}

function AndroidDeviceSelection() {
  const { setDeviceId } = useMobileDevice();
  useLayoutEffect(() => setDeviceId("pixel-10"), [setDeviceId]);
  return null;
}
