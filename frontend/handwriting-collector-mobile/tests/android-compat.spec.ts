import { expect, test } from "@playwright/test";
import { ink } from "./pen-input";

for(const viewport of [{width:393,height:873},{width:360,height:640}])test(`Android shell and native export/upload contract ${viewport.width}x${viewport.height}`,async({page})=>{
  test.setTimeout(60_000);
  await page.setViewportSize(viewport);
  // Contract test only: emulate the Capacitor bridge, never call the production upload server.
  await page.addInitScript(()=>{
    const w=window as any;
    w.androidBridge={};w.__nativeCalls=[];w.__uploads=0;
    w.Capacitor={PluginHeaders:[
      {name:"SystemBars",methods:[{name:"hide",rtype:"promise"}]},
      {name:"Filesystem",methods:[{name:"writeFile",rtype:"promise"}]},
      {name:"Share",methods:[{name:"share",rtype:"promise"}]},
      {name:"CapacitorHttp",methods:[{name:"post",rtype:"promise"}]},
    ],nativePromise:async(plugin:string,method:string,options:any)=>{
      w.__nativeCalls.push({plugin,method,options});
      if(plugin==="Filesystem")return{uri:`file:///cache/${options.path}`};
      if(plugin==="CapacitorHttp")return ++w.__uploads===1?{status:503,data:{}}:{status:201,data:{storedAs:"synthetic-test.json"}};
      return{};
    }};
    document.addEventListener("DOMContentLoaded",()=>{
      document.documentElement.style.setProperty("--native-inset-top","28px");
      document.documentElement.style.setProperty("--native-inset-bottom","0px");
    });
  });
  await page.goto("/");await expect(page.locator(".native-shell")).toBeVisible();
  await expect(page.getByTestId("device-picker")).toBeHidden();
  await page.getByRole("button",{name:"开始采集"}).click();
  const screen=page.locator('.flow-screen[data-flow-current="true"]');
  await screen.getByRole("button",{name:"初次测试"}).click();
  await screen.getByRole("spinbutton",{name:"年龄"}).fill("20");
  await expect(page.getByTestId("keyboard-dock")).toBeHidden();
  await screen.getByLabel("年级").selectOption("24");await screen.getByLabel("来自省份").selectOption("440000");
  await screen.getByRole("button",{name:"生成采集编号"}).click();await screen.getByRole("checkbox").check();
  await screen.getByRole("button",{name:"继续",exact:true}).click();
  for(let i=0;i<5;i++){
    await screen.getByRole("radio",{name:"超过一半的时间 3 分"}).click();
    await screen.getByRole("button",{name:i===4?"进入书写采集":"下一题"}).click();
  }
  for(let task=0;task<4;task++){
    const canvas=screen.locator("canvas");await expect(canvas).toBeVisible();await expect(screen).toHaveCount(1);
    await ink(canvas,task===0);
    if(task>0){
      await screen.getByRole("button",{name:"撤回上一笔"}).click();await expect(canvas).toHaveAttribute("data-point-count","616");
      await screen.getByRole("button",{name:"恢复上一笔"}).click();await expect(canvas).toHaveAttribute("data-point-count","630");
    }
    await screen.getByRole("button",{name:"确认本页书写"}).click();
  }
  await screen.getByRole("button",{name:"保存并导出 JSON"}).click();
  await expect(screen).toContainText("服务器连接失败，数据已保存在本机");
  await screen.getByRole("button",{name:"重试上传"}).click();await expect(screen).toContainText("已上传到服务器");
  const calls=await page.evaluate(()=>(window as any).__nativeCalls);
  const write=calls.find((c:any)=>c.plugin==="Filesystem");const share=calls.find((c:any)=>c.plugin==="Share");
  expect(write.options.directory).toBe("CACHE");expect(write.options.encoding).toBe("utf8");
  expect(JSON.parse(write.options.data).questionnaire.instrumentId).toBe("WHO_5");
  expect(share.options.url).toBe(`file:///cache/${write.options.path}`);
  const uploads=calls.filter((c:any)=>c.plugin==="CapacitorHttp");expect(uploads).toHaveLength(2);
  expect(uploads[0].options.url).toBe("http://82.157.132.139:8082/api/handwriting-sessions");
  expect(uploads[0].options.headers["X-Filename"]).toBe(encodeURIComponent(write.options.path));
  expect(uploads[1].options.data).toBe(uploads[0].options.data);
  expect(calls.some((c:any)=>c.plugin==="SystemBars"&&c.options.bar==="NavigationBar")).toBe(true);
  await page.screenshot({path:`artifacts/screenshots/android-native-${viewport.width}.png`});
});
