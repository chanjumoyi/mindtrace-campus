import { expect, test, type Page, type Locator } from "@playwright/test";

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
async function ink(canvas:Locator, warmup=false, strokes=45) {
  await canvas.evaluate((node,opts)=>{
    const oldCapture=node.setPointerCapture, oldRelease=node.releasePointerCapture;
    node.setPointerCapture=()=>{};node.releasePointerCapture=()=>{};
    const rect=node.getBoundingClientRect();let stamp=performance.now();
    const fire=(type:string,x:number,y:number)=>{
      const e=new PointerEvent(type,{bubbles:true,pointerId:90,pointerType:"pen",isPrimary:true,button:0,
        buttons:type==="pointerup"?0:1,pressure:type==="pointerup"?0:0.4+(x%5)/20,
        clientX:rect.left+x,clientY:rect.top+y});
      Object.defineProperty(e,"timeStamp",{value:stamp});stamp+=40;
      Object.defineProperty(e,"getCoalescedEvents",{value:()=>[e]});node.dispatchEvent(e);
    };
    for(let i=0;i<(opts.warmup?3:opts.strokes);i++) {
      const x=20+(i%7)*35,y=25+(Math.floor(i/7)%5)*30;
      fire("pointerdown",x,y);
      for(let j=1;j<=12;j++)fire("pointermove",x+j*(opts.warmup?4:2),y+(opts.warmup?0:j%2*5));
      fire("pointerup",x+(opts.warmup?48:24),y);
    }
    node.setPointerCapture=oldCapture;node.releasePointerCapture=oldRelease;
  },{warmup,strokes});
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
    expect(attempt.interruptions.filter((e:any)=>e.type.startsWith("stroke-")).map((e:any)=>e.type)).toEqual(["stroke-undo","stroke-redo"]);
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
