#!/usr/bin/env node
import { copyFileSync, existsSync, mkdirSync, readdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const androidRoot = path.join(root, "android");
const buildEnvironment = { ...process.env };
if (process.platform === "win32") {
  const sdk = buildEnvironment.ANDROID_SDK_ROOT || buildEnvironment.ANDROID_HOME || path.join(buildEnvironment.LOCALAPPDATA ?? "", "Android", "Sdk");
  if (sdk && existsSync(sdk)) {
    buildEnvironment.ANDROID_HOME = sdk;
    buildEnvironment.ANDROID_SDK_ROOT = sdk;
  }
  const microsoftJavaRoot = path.join(buildEnvironment.ProgramFiles ?? "C:\\Program Files", "Microsoft");
  const jdk21 = existsSync(microsoftJavaRoot)
    ? readdirSync(microsoftJavaRoot).filter((name) => name.startsWith("jdk-21")).sort().at(-1)
    : undefined;
  if (jdk21) {
    buildEnvironment.JAVA_HOME = path.join(microsoftJavaRoot, jdk21);
    buildEnvironment.Path = `${buildEnvironment.JAVA_HOME}\\bin;${buildEnvironment.Path ?? ""}`;
  }
}

const wrapper = buildEnvironment.GRADLE_EXECUTABLE || (process.platform === "win32" ? "gradlew.bat" : "./gradlew");
const command = process.platform === "win32"
  ? buildEnvironment.ComSpec || path.join(buildEnvironment.SystemRoot ?? "C:\\Windows", "System32", "cmd.exe")
  : wrapper;
const commandArguments = process.platform === "win32"
  ? ["/d", "/s", "/c", wrapper, "assembleDebug"]
  : ["assembleDebug"];
const result = spawnSync(command, commandArguments, {
  cwd: androidRoot,
  env: buildEnvironment,
  stdio: "inherit",
});
if (result.status !== 0) process.exit(result.status ?? 1);

const source = path.join(androidRoot, "app", "build", "outputs", "apk", "debug", "app-debug.apk");
const outputDirectory = path.join(root, "artifacts", "android");
const destination = path.join(outputDirectory, "mindtrace-handwriting-collector-debug.apk");
mkdirSync(outputDirectory, { recursive: true });
copyFileSync(source, destination);
console.log(`Android APK: ${destination}`);
