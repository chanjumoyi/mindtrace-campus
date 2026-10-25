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
async function recontactGesture(page:Page,canvas:Locator,fingers:2|3) {
  const box=(await canvas.boundingBox())!;
  const client=await page.context().newCDPSession(page);
  const contacts=Array.from({length:fingers},(_,i)=>({id:i+1,x:box.x+50+i*35,y:box.y+80,radiusX:4,radiusY:4,force:0.5}));
  for(let count=1;count<=fingers;count++)await client.send("Input.dispatchTouchEvent",{type:"touchStart",touchPoints:contacts.slice(0,count)});
  // CDP touchEnd lists the contacts to lift. Keep the last finger down so this remains one session.
  await client.send("Input.dispatchTouchEvent",{type:"touchEnd",touchPoints:contacts.slice(0,-1)});
  const active=[contacts[fingers-1]];
  for(let i=0;i<fingers-1;i++) {
    active.push({...contacts[i],id:fingers+i+1});
    await client.send("Input.dispatchTouchEvent",{type:"touchStart",touchPoints:[...active]});
  }
  await client.send("Input.dispatchTouchEvent",{type:"touchEnd",touchPoints:[]});
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
      await expect(screen.locator(".device-check")).toHaveText("接触画布后开始书写 · 双指点击撤回，三指点击恢复");
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
      await expect(screen.locator(".device-check")).toHaveText("接触画布后开始书写 · 双指点击撤回，三指点击恢复");
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
  await expect(screen.getByRole("region",{name:"WHO-5 状态评定"})).toBeVisible();
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
  await expect(screen.locator(".device-check")).toHaveText("接触画布后开始书写 · 双指点击撤回，三指点击恢复");
  await expect(screen.locator(".device-check")).not.toContainText("触摸输入模式");

});

for (const fault of ["missing-third-pointer", "lost-capture", "missing-third-touchstart", "missing-both-third-starts"] as const) test(`three-finger redo survives ${fault}`,async({page})=>{
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
      if((fault==="missing-third-pointer" || fault==="missing-both-third-starts") && downs===3)event.stopImmediatePropagation();
      if(fault==="lost-capture" && downs===2)node.dispatchEvent(new PointerEvent("lostpointercapture",{
        bubbles:true,pointerType:"touch",pointerId:event.pointerId-1,isPrimary:true,
      }));
      if(downs===3)node.removeEventListener("pointerdown",listener,true);
    };
    node.addEventListener("pointerdown",listener,true);
    if(fault === "missing-third-touchstart" || fault === "missing-both-third-starts") {
      const dropThirdStart = (event: TouchEvent) => {
        if(event.targetTouches.length === 3) {
          event.stopImmediatePropagation();
          node.removeEventListener("touchstart", dropThirdStart, true);
        }
      };
      node.addEventListener("touchstart", dropThirdStart, true);
    }
  },fault);
  await gesture(page,canvas,3);
  await expect(canvas).toHaveAttribute("data-point-count","28");
  expect((await pixels(canvas))===original).toBe(true);
});

for (const fingers of [2,3] as const) test(`${fingers}-finger ${fingers===2?"undo":"redo"} counts simultaneous contacts after fingers lift and recontact`,async({page})=>{
  const screen=await questionnaire(page);await answer(page,screen);
  let canvas=screen.locator("canvas");await ink(canvas,true);await screen.getByRole("button",{name:"确认本页书写"}).click();
  canvas=screen.locator("canvas");await expect(canvas).toBeVisible();
  await ink(canvas,false,2);const original=await pixels(canvas);
  await gesture(page,canvas,2);await expect(canvas).toHaveAttribute("data-point-count","14");
  const undone=await pixels(canvas);
  if(fingers===2) {
    await gesture(page,canvas,3);await expect(canvas).toHaveAttribute("data-point-count","28");
  }
  await recontactGesture(page,canvas,fingers);
  await expect(canvas).toHaveAttribute("data-point-count",fingers===2?"14":"28");
  expect((await pixels(canvas))===(fingers===2?undone:original),"recontact must edit one stroke and preserve its pixels").toBe(true);
});

// WebViews can deliver an incomplete pointer stream before the full native touch stream.
async function reorderedTouch(page: Page, canvas: Locator, fingers: 2 | 3, native: boolean, delay = 20, cancelPointers = false) {
  await canvas.evaluate(async (node, { fingers, native, delay, cancelPointers }) => {
    const capture = node.setPointerCapture, release = node.releasePointerCapture;
    node.setPointerCapture = () => {}; node.releasePointerCapture = () => {};
    const rect = node.getBoundingClientRect();
    const pointer = (type: string, id: number) => node.dispatchEvent(new PointerEvent(type, {
      bubbles: true, cancelable: true, pointerType: "touch", pointerId: id, isPrimary: id === 1,
      button: 0, buttons: type === "pointerup" ? 0 : 1, pressure: 0.5,
      clientX: rect.x + 45 + id * 30, clientY: rect.y + 80,
    }));
    // Only two pointer contacts are delivered, even when the native tap has three.
    const pointerCount = native ? 2 : fingers;
    for (let id = 1; id <= pointerCount; id++) pointer("pointerdown", id);
    for (let id = 1; id <= pointerCount; id++) pointer(cancelPointers ? "pointercancel" : "pointerup", id);
    if (native) {
      await new Promise((resolve) => setTimeout(resolve, delay));
      const touches = Array.from({ length: fingers }, (_, index) => new Touch({
        identifier: index + 11, target: node, clientX: rect.x + 75 + index * 30, clientY: rect.y + 80,
      }));
      node.dispatchEvent(new TouchEvent("touchstart", {
        bubbles: true, cancelable: true, touches, targetTouches: touches, changedTouches: touches,
      }));
      node.dispatchEvent(new TouchEvent("touchend", {
        bubbles: true, cancelable: true, touches: [], targetTouches: [], changedTouches: touches,
      }));
    }
    node.setPointerCapture = capture; node.releasePointerCapture = release;
  }, { fingers, native, delay, cancelPointers });
  // Include the fallback completion window, so a second history edit cannot escape the assertion.
  await page.waitForTimeout(160);
}

for (const native of [true, false]) test(
  native ? "late native touch delivery must commit exactly one history action" : "pointer-only fallback keeps multilevel undo and redo",
  async ({ page }) => {
    const screen = await questionnaire(page); await answer(page, screen);
    await ink(screen.locator("canvas"), true);
    await screen.getByRole("button", { name: "确认本页书写" }).click();
    const canvas = screen.locator("canvas"); await expect(canvas).toBeVisible();
    await ink(canvas, false, 3); const original = await pixels(canvas);
    await screen.getByRole("button", { name: "撤回上一笔" }).click();
    await reorderedTouch(page, canvas, 3, native);
    await expect(canvas).toHaveAttribute("data-point-count", "42");
    // Delayed native delivery must still claim this gesture without a second history edit.
    await reorderedTouch(page, canvas, 2, native, 80);
    await expect(canvas).toHaveAttribute("data-point-count", "28");
    await reorderedTouch(page, canvas, 2, native);
    await expect(canvas).toHaveAttribute("data-point-count", "14");
    await reorderedTouch(page, canvas, 3, native);
    await expect(canvas).toHaveAttribute("data-point-count", "28");
    await reorderedTouch(page, canvas, 3, native);
    await expect(canvas).toHaveAttribute("data-point-count", "42");
    expect(await pixels(canvas)).toBe(original);
    await expect(screen.getByRole("button", { name: "恢复上一笔" })).toBeDisabled();
  },
);


test("native touch completion overrides provisional pointer cancellation only", async ({ page }) => {
  const screen = await questionnaire(page); await answer(page, screen);
  await ink(screen.locator("canvas"), true);
  await screen.getByRole("button", { name: "确认本页书写" }).click();
  const canvas = screen.locator("canvas"); await expect(canvas).toBeVisible();
  await ink(canvas, false, 3); const original = await pixels(canvas);
  await reorderedTouch(page, canvas, 2, false, 0, true);
  await expect(canvas).toHaveAttribute("data-point-count", "42");
  await screen.getByRole("button", { name: "撤回上一笔" }).click();
  await reorderedTouch(page, canvas, 3, true, 20, true);
  await expect(canvas).toHaveAttribute("data-point-count", "42");
  expect(await pixels(canvas)).toBe(original);
});

test("staggered finger release never executes an intermediate undo during redo", async ({ page }) => {
  const screen = await questionnaire(page); await answer(page, screen);
  await ink(screen.locator("canvas"), true);
  await screen.getByRole("button", { name: "确认本页书写" }).click();
  const canvas = screen.locator("canvas"); await expect(canvas).toBeVisible();
  await ink(canvas, false, 3); const original = await pixels(canvas);
  const client = await page.context().newCDPSession(page);
  const box = (await canvas.boundingBox())!;
  const contacts = Array.from({ length: 3 }, (_, i) => ({
    id: i + 1, x: box.x + 55 + i * 35, y: box.y + 80, force: 0.5,
  }));
  for (const releaseOrder of [[0, 1, 2], [2, 0, 1]]) {
    await gesture(page, canvas, 2);
    await expect(canvas).toHaveAttribute("data-point-count", "28");
    const intermediateCounts = [];
    for (let fingers = 1; fingers <= 3; fingers++) {
      await client.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: contacts.slice(0, fingers) });
    }
    for (const index of releaseOrder.slice(0, 2)) {
      await client.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [contacts[index]] });
      intermediateCounts.push(await count(canvas));
    }
    await client.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    expect(intermediateCounts).toEqual(["28", "28"]);
    await expect(canvas).toHaveAttribute("data-point-count", "42");
    expect(await pixels(canvas)).toBe(original);
  }
  await client.detach();
});


test("a native undo does not disable pointer-only redo on the next gesture", async ({ page }) => {
  const screen = await questionnaire(page); await answer(page, screen);
  await ink(screen.locator("canvas"), true);
  await screen.getByRole("button", { name: "确认本页书写" }).click();
  const canvas = screen.locator("canvas"); await expect(canvas).toBeVisible();
  await ink(canvas, false, 2); const original = await pixels(canvas);
  await gesture(page, canvas, 2);
  await expect(canvas).toHaveAttribute("data-point-count", "14");
  await reorderedTouch(page, canvas, 3, false);
  await expect(canvas).toHaveAttribute("data-point-count", "28");
  expect(await pixels(canvas)).toBe(original);
  await screen.getByRole("button", { name: "撤回上一笔" }).click();
  await expect(canvas).toHaveAttribute("data-point-count", "14");
  await screen.getByRole("button", { name: "恢复上一笔" }).click();
  await expect(canvas).toHaveAttribute("data-point-count", "28");
});


test("a missing pointerup must not turn two-finger recontact into redo", async ({ page }) => {
  const screen = await questionnaire(page); await answer(page, screen);
  await ink(screen.locator("canvas"), true);
  await screen.getByRole("button", { name: "确认本页书写" }).click();
  const canvas = screen.locator("canvas"); await expect(canvas).toBeVisible();
  await ink(canvas, false, 2);
  await canvas.evaluate((node) => {
    const dropFirstUp = (event: PointerEvent) => {
      if (event.pointerType !== "touch") return;
      event.stopImmediatePropagation();
      node.removeEventListener("pointerup", dropFirstUp, true);
    };
    node.addEventListener("pointerup", dropFirstUp, true);
  });
  await recontactGesture(page, canvas, 2);
  await expect(canvas).toHaveAttribute("data-point-count", "14");
  await gesture(page, canvas, 3);
  await expect(canvas).toHaveAttribute("data-point-count", "28");
});


for (const releaseOutside of [false, true]) test(
  "pointer-only three-finger redo survives capture loss, release outside=" + releaseOutside, async ({ page }) => {
  const screen = await questionnaire(page); await answer(page, screen);
  await ink(screen.locator("canvas"), true);
  await screen.getByRole("button", { name: "确认本页书写" }).click();
  const canvas = screen.locator("canvas"); await expect(canvas).toBeVisible();
  await ink(canvas, false, 2); const original = await pixels(canvas);
  await reorderedTouch(page, canvas, 2, false);
  await expect(canvas).toHaveAttribute("data-point-count", "14");
  await canvas.evaluate((node, releaseOutside) => {
    let downs = 0;
    const loseCapture = (event: PointerEvent) => {
      if (event.pointerType !== "touch") return;
      if (++downs === 3) {
        node.dispatchEvent(new PointerEvent("lostpointercapture", {
          bubbles: true, pointerType: "touch", pointerId: 1, isPrimary: true,
        }));
        node.removeEventListener("pointerdown", loseCapture, true);
      }
    };
    node.addEventListener("pointerdown", loseCapture, true);
    if (releaseOutside) {
      const retargetUp = (event: PointerEvent) => {
        if (event.pointerType !== "touch") return;
        event.stopImmediatePropagation();
        document.body.dispatchEvent(new PointerEvent("pointerup", {
          bubbles: true, pointerType: "touch", pointerId: event.pointerId,
          clientX: event.clientX, clientY: event.clientY, isPrimary: event.isPrimary,
        }));
        if (event.pointerId === 3) node.removeEventListener("pointerup", retargetUp, true);
      };
      node.addEventListener("pointerup", retargetUp, true);
    }
  }, releaseOutside);
  await reorderedTouch(page, canvas, 3, false);
  await expect(canvas).toHaveAttribute("data-point-count", "28");
  expect(await pixels(canvas)).toBe(original);
});


test("Windows pointer-only input draws, undoes and redoes real touch strokes", async ({ page }) => {
  const screen = await questionnaire(page); await answer(page, screen);
  await ink(screen.locator("canvas"), true);
  await screen.getByRole("button", { name: "确认本页书写" }).click();
  const canvas = screen.locator("canvas"); await expect(canvas).toBeVisible();
  await canvas.evaluate((node) => {
    for (const type of ["touchstart", "touchmove", "touchend", "touchcancel"]) {
      node.addEventListener(type, event => event.stopImmediatePropagation(), true);
    }
  });
  await touchLine(page, canvas); await page.waitForTimeout(160);
  const points = await count(canvas), original = await pixels(canvas);
  expect(Number(points)).toBeGreaterThan(2);
  await gesture(page, canvas, 2); await expect(canvas).toHaveAttribute("data-point-count", "0");
  await gesture(page, canvas, 3); await expect(canvas).toHaveAttribute("data-point-count", points!);
  expect(await pixels(canvas)).toBe(original);
});


for (const marginFirst of [false, true]) test("three-finger redo includes a finger on the writing margin, first=" + marginFirst, async ({ page }) => {
  const screen = await questionnaire(page); await answer(page, screen);
  await ink(screen.locator("canvas"), true);
  await screen.getByRole("button", { name: "确认本页书写" }).click();
  const canvas = screen.locator("canvas"); await expect(canvas).toBeVisible();
  await ink(canvas, false, 2); const original = await pixels(canvas);
  await gesture(page, canvas, 2); await expect(canvas).toHaveAttribute("data-point-count", "14");
  const box = (await canvas.boundingBox())!;
  const client = await page.context().newCDPSession(page);
  const contacts = [
    {id: 1, x: box.x + 60, y: box.y + 90},
    {id: 2, x: box.x + 110, y: box.y + 90},
    {id: 3, x: box.x - 6, y: box.y + 90},
  ];
  if (marginFirst) contacts.unshift(contacts.pop()!);
  for (let n=1; n<=3; n++) await client.send("Input.dispatchTouchEvent", {type:"touchStart", touchPoints:contacts.slice(0,n)});
  await client.send("Input.dispatchTouchEvent", {type:"touchEnd", touchPoints:[]});
  await client.detach();
  await expect(canvas).toHaveAttribute("data-point-count", "28");
  expect(await pixels(canvas)).toBe(original);
});


test("history toolbar is above the canvas and shares button, touch and keyboard history", async ({ page }) => {
  const screen = await questionnaire(page); await answer(page, screen);
  await ink(screen.locator("canvas"), true);
  await screen.getByRole("button", { name: "确认本页书写" }).click();
  const canvas = screen.locator("canvas"); await expect(canvas).toBeVisible();
  const toolbar = screen.getByRole("toolbar", { name: "笔画历史" });
  await expect(toolbar).toBeVisible();
  const toolbarBox=(await toolbar.boundingBox())!, canvasBox=(await canvas.boundingBox())!;
  expect(toolbarBox.y+toolbarBox.height).toBeLessThanOrEqual(canvasBox.y);
  await ink(canvas, false, 2); const original = await pixels(canvas);
  await gesture(page, canvas, 2); await expect(canvas).toHaveAttribute("data-point-count", "14");
  await toolbar.getByRole("button", {name:"恢复上一笔"}).click();
  await expect(canvas).toHaveAttribute("data-point-count", "28");
  await expect(toolbar.getByRole("status")).toHaveText("已恢复一笔");
  expect(await pixels(canvas)).toBe(original);
  await page.keyboard.press("Control+z"); await expect(canvas).toHaveAttribute("data-point-count", "14");
  await page.keyboard.press("Control+y"); await expect(canvas).toHaveAttribute("data-point-count", "28");
  await page.keyboard.press("Control+z");
  await page.keyboard.press("Control+Shift+z");
  await expect(canvas).toHaveAttribute("data-point-count", "28");
  expect(await pixels(canvas)).toBe(original);
  await page.locator(".device-screen").screenshot({path:"artifacts/screenshots/history-toolbar-restored.png"});
});
