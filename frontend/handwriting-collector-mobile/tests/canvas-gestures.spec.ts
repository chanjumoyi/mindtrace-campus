import { expect, test, type Page, type Locator } from "@playwright/test";

import { ink } from "./pen-input";

const screenshotRoot = "artifacts/screenshots";
async function screenshot(page: Page, name: string) {
  await page.mouse.move(5, 5);
  await page.locator(".device-screen").screenshot({path:`${screenshotRoot}/${name}.png`, animations:"disabled"});
}
async function touchLine(page:Page,canvas:Locator) {
  const box=(await canvas.boundingBox())!,client=await page.context().newCDPSession(page);
  const path=[[0.25,0.7],[0.27,0.61],[0.34,0.54],[0.42,0.49],[0.5,0.42],[0.62,0.35]];
  for(let i=0;i<path.length;i++)await client.send("Input.dispatchTouchEvent",{type:i===0?"touchStart":"touchMove",touchPoints:[{id:1,x:box.x+box.width*path[i][0],y:box.y+box.height*path[i][1],force:0.5}]});
  await client.send("Input.dispatchTouchEvent",{type:"touchEnd",touchPoints:[]});await client.detach();
}
async function questionnaire(page: Page) {
  await page.goto("/");
  await page.getByTestId("device-picker").click();
  await page.getByRole("menuitemradio", {name:"Pixel 10"}).click();
  await page.getByRole("button", {name:"开始采集"}).click();
  const screen=page.locator('.flow-screen[data-flow-current="true"]');
  await screen.getByRole("button",{name:"初次测试"}).click();
  await screen.getByRole("spinbutton",{name:"年龄"}).fill("20");
  await screen.getByLabel("年级").selectOption("24");
  await screen.getByLabel("来自省份").selectOption("440000");
  await screen.getByRole("button",{name:"生成采集编号"}).click();
  await screen.getByRole("checkbox").check();
  await screen.getByRole("button",{name:"继续",exact:true}).click();
  await expect(screen.getByRole("heading",{name:"状态问卷"})).toBeVisible();
  await expect(screen).toHaveCount(1);
  return screen;
}
async function answer(page:Page,screen:Locator) {
  for(let i=0;i<5;i++) {
    await screen.getByRole("radio",{name:"超过一半的时间 3 分"}).click();
    if(i===1) await screenshot(page,"01-questionnaire");
    await screen.getByRole("button",{name:i===4?"进入书写采集":"下一题"}).click();
  }
}
async function gesture(page:Page,canvas:Locator,fingers:number,mode:"tap"|"drag"|"cancel"|"hold"="tap") {
  const box=(await canvas.boundingBox())!;
  const client=await page.context().newCDPSession(page);
  const contacts=Array.from({length:fingers},(_,i)=>({id:i+1,x:box.x+50+i*35,y:box.y+80,radiusX:4,radiusY:4,force:0.5}));
  // Stagger contact arrival to cover the provisional first-finger mark.
  for(let count=1;count<=fingers;count++)await client.send("Input.dispatchTouchEvent",{type:"touchStart",touchPoints:contacts.slice(0,count)});
  if(mode==="drag")await client.send("Input.dispatchTouchEvent",{type:"touchMove",touchPoints:contacts.map(p=>({...p,x:p.x+30}))});
  if(mode==="hold")await page.waitForTimeout(450);
  await client.send("Input.dispatchTouchEvent",{type:mode==="cancel"?"touchCancel":"touchEnd",touchPoints:[]});
  await client.detach();
}
const count=(canvas:Locator)=>canvas.getAttribute("data-point-count");
const pixels=(canvas:Locator)=>canvas.evaluate((node:HTMLCanvasElement)=>node.toDataURL());

test("real multitouch undoes/redoes copy and free-writing without changing raw data or metrics",async({page})=>{
  test.setTimeout(60_000);
  let payload:any;
  await page.route("**/api/handwriting-sessions",async route=>{payload=route.request().postDataJSON();await route.fulfill({json:{storedAs:"synthetic.json"}});});
  const screen=await questionnaire(page);await answer(page,screen);
  for(let task=0;task<4;task++) {
    const canvas=screen.locator("canvas");await expect(canvas).toBeVisible();await expect(screen).toHaveCount(1);
    if(task===1)await screenshot(page,"02-copy-empty");
    if(task===3) {
      await screenshot(page,"03-free-empty");
      await touchLine(page,canvas);
      await expect(screen.locator(".device-check")).toHaveText("接触画布后开始书写 · 双指点击撤回，三指点击取消");
      await screenshot(page,"04-free-touch-written");
      await screen.getByRole("button",{name:"清空重写"}).click();
    }
    await ink(canvas,task===0);
    if(task>0) {
      const before=await pixels(canvas);await expect(canvas).toHaveAttribute("data-point-count","630");
      await gesture(page,canvas,2);await expect(canvas).toHaveAttribute("data-point-count","616");
      expect(await pixels(canvas)).not.toBe(before);
      await gesture(page,canvas,3);await expect(canvas).toHaveAttribute("data-point-count","630");
      expect((await pixels(canvas)) === before, "restored canvas must match the retained strokes").toBe(true);
      await expect(screen.locator(".device-check")).toHaveText("接触画布后开始书写 · 双指点击撤回，三指点击取消");
      await expect(screen.locator(".device-check")).not.toContainText("输入模式");
      await expect(screen.getByRole("button",{name:"恢复上一笔"})).toBeDisabled();
      await screen.getByRole("button",{name:"撤回上一笔"}).click();
      await expect(canvas).toHaveAttribute("data-point-count","616");
      await screen.getByRole("button",{name:"恢复上一笔"}).click();
      await expect(canvas).toHaveAttribute("data-point-count","630");
      expect((await pixels(canvas))===before).toBe(true);

    }
    await screen.getByRole("button",{name:"确认本页书写"}).click();
  }
  await expect(screen).toHaveCount(1);
  await expect(screen.getByRole("heading",{name:"本轮采集完成"})).toBeVisible();
  const download=page.waitForEvent("download");await screen.getByRole("button",{name:"保存并导出 JSON"}).click();await download;
  await expect.poll(()=>payload?.attempts?.length).toBe(4);
  for(const attempt of payload.attempts.slice(1)) {
    expect(attempt.strokeCount).toBe(45);expect(attempt.points).toHaveLength(630);
    expect(attempt.metrics.strokeCount).toBe(45);expect(attempt.metrics.movePointCount).toBe(540);
    expect(attempt.points.every((p:any)=>p.pointerType==="pen")).toBe(true);
    expect(attempt.points.map((p:any)=>p.seq)).toEqual(Array.from({length:630},(_,i)=>i));
    expect(attempt.interruptions.filter((e:any)=>e.type.startsWith("stroke-")).map((e:any)=>e.type)).toEqual(["stroke-undo","stroke-redo","stroke-undo","stroke-redo"]);
  }
});

test("gesture guards, redo invalidation, and empty canvas keep correct history",async({page})=>{
  test.setTimeout(60_000);
  const screen=await questionnaire(page);await answer(page,screen);
  let canvas=screen.locator("canvas");await ink(canvas,true);await screen.getByRole("button",{name:"确认本页书写"}).click();
  canvas=screen.locator("canvas");await expect(canvas).toBeVisible();
  await gesture(page,canvas,2);await gesture(page,canvas,3);expect(await count(canvas)).toBe("0");
  await ink(canvas,false,2);const before=await pixels(canvas);
  for(const [fingers,mode] of [[2,"drag"],[2,"hold"],[2,"cancel"],[4,"tap"]] as const) {
    await gesture(page,canvas,fingers,mode);await expect(canvas).toHaveAttribute("data-point-count","28");expect((await pixels(canvas)) === before, "restored canvas must match the retained strokes").toBe(true);
  }
  await gesture(page,canvas,2);await gesture(page,canvas,2);await expect(canvas).toHaveAttribute("data-point-count","0");
  await gesture(page,canvas,3);await gesture(page,canvas,3);await expect(canvas).toHaveAttribute("data-point-count","28");expect((await pixels(canvas)) === before, "restored canvas must match the retained strokes").toBe(true);
  await gesture(page,canvas,2);await ink(canvas,false,1);await gesture(page,canvas,3);await expect(canvas).toHaveAttribute("data-point-count","28");
  await gesture(page,canvas,2);await screen.getByRole("button",{name:"清空重写"}).click();await gesture(page,canvas,3);await expect(canvas).toHaveAttribute("data-point-count","0");
  // Real one-finger writing still records points; multitouch must not disable it.
  await gesture(page,canvas,1);await expect(canvas).toHaveAttribute("data-point-count","2");
  await expect(screen.locator(".device-check")).toHaveText("接触画布后开始书写 · 双指点击撤回，三指点击取消");
  await expect(screen.locator(".device-check")).not.toContainText("触摸输入模式");

});

for (const fault of ["missing-third-pointer", "lost-capture"] as const) test(`three-finger redo survives ${fault}`,async({page})=>{
  const screen=await questionnaire(page);await answer(page,screen);
  let canvas=screen.locator("canvas");await ink(canvas,true);await screen.getByRole("button",{name:"确认本页书写"}).click();
  canvas=screen.locator("canvas");await expect(canvas).toBeVisible();
  await ink(canvas,false,2);const original=await pixels(canvas);
  await gesture(page,canvas,2);await expect(canvas).toHaveAttribute("data-point-count","14");
  await canvas.evaluate((node,fault)=>{
    let downs=0;
    const listener=(event:PointerEvent)=>{
      if(event.pointerType!=="touch")return;
      downs++;
      // Emulate incomplete/reordered WebView pointer delivery while native TouchEvents remain intact.
      if(fault==="missing-third-pointer" && downs===3)event.stopImmediatePropagation();
      if(fault==="lost-capture" && downs===2)node.dispatchEvent(new PointerEvent("lostpointercapture",{
        bubbles:true,pointerType:"touch",pointerId:event.pointerId-1,isPrimary:true,
      }));
      if(downs===3)node.removeEventListener("pointerdown",listener,true);
    };
    node.addEventListener("pointerdown",listener,true);
  },fault);
  await gesture(page,canvas,3);
  await expect(canvas).toHaveAttribute("data-point-count","28");
  expect((await pixels(canvas))===original).toBe(true);
});
