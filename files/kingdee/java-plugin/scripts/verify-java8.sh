#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/target/self-test"
rm -rf "$BUILD"
mkdir -p "$BUILD"
javac --release 8 -d "$BUILD" \
  "$ROOT/src/main/java/com/xinji/kingdee/FoundationPluginCore.java" \
  "$ROOT/src/test/java/com/xinji/kingdee/FoundationPluginCoreSelfTest.java"
java -cp "$BUILD" com.xinji.kingdee.FoundationPluginCoreSelfTest
