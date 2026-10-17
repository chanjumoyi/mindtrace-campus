import { Capacitor } from "@capacitor/core";
import { Directory, Encoding, Filesystem } from "@capacitor/filesystem";
import { Share } from "@capacitor/share";

export async function exportJsonPackage(filename: string, json: string) {
  if (Capacitor.getPlatform() !== "android") {
    const url = URL.createObjectURL(new Blob([json], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    return;
  }

  const result = await Filesystem.writeFile({
    path: filename,
    data: json,
    directory: Directory.Cache,
    encoding: Encoding.UTF8,
  });
  await Share.share({
    title: filename,
    text: "心迹书写状态采集数据",
    url: result.uri,
    dialogTitle: "保存或发送采集文件",
  });
}
