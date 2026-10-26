import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

test("initial collection creates the requested ID and keeps pen-safe writing actions", async ({ page }) => {
  test.setTimeout(30_000);
  await page.goto("/");
  await page.getByRole("button", { name: "开始采集" }).click();

  const currentScreen = page.locator('.flow-screen[data-flow-current="true"]');
  await currentScreen.getByRole("button", { name: "初次测试" }).click();
  await currentScreen.getByRole("spinbutton", { name: "年龄" }).fill("20");
  await currentScreen.getByLabel("年级").selectOption("24");
  await currentScreen.getByLabel("来自省份").selectOption("440000");
  await currentScreen.getByRole("button", { name: "生成采集编号" }).click();

  await expect(currentScreen).toContainText(/MT-24-[A-HJ-NP-Z2-9]{4}/);
  await expect(currentScreen).toContainText("第 1 次");
  await expect(currentScreen).not.toContainText("编号已经锁定，本轮无法修改");
  const participantId = await currentScreen.locator(".identity-card strong").innerText();
  const storedProfile = await page.evaluate((id) => localStorage.getItem(`mindtrace.participant-profile.v2.${id}`), participantId);
  expect(JSON.parse(storedProfile ?? "{}")).toMatchObject({ ageYears: 20, grade: "24", provinceCode: "440000", provinceLabel: "广东省" });

  await currentScreen.getByRole("checkbox").check();
  await currentScreen.getByRole("button", { name: "继续" }).click();

  await expect(currentScreen).not.toContainText("心境与兴趣");

  for (let itemIndex = 0; itemIndex < 5; itemIndex += 1) {
    await currentScreen.getByRole("radio", { name: "所有时间 5 分" }).click();
    await currentScreen.getByRole("button", { name: itemIndex === 4 ? "进入书写采集" : "下一题" }).click();
  }

  await expect(currentScreen.getByText("压力热身")).toBeVisible();
  await expect(currentScreen).toContainText("1/4");
  await expect(currentScreen.locator(".writing-actions")).toHaveAttribute("data-scroll-drag", "ignore");
  await expect(currentScreen.getByRole("button", { name: "确认本页书写" })).toHaveAttribute("type", "button");
});

test("questionnaire requires a response and preserves answers when returning", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "开始采集" }).click();
  const currentScreen = page.locator('.flow-screen[data-flow-current="true"]');
  await currentScreen.getByRole("button", { name: "初次测试" }).click();
  await currentScreen.getByRole("spinbutton", { name: "年龄" }).fill("20");
  await currentScreen.getByLabel("年级").selectOption("24");
  await currentScreen.getByLabel("来自省份").selectOption("440000");
  await currentScreen.getByRole("button", { name: "生成采集编号" }).click();
  await currentScreen.getByRole("checkbox").check();
  await currentScreen.getByRole("button", { name: "继续" }).click();

  await expect(currentScreen.getByRole("heading", { name: "状态问卷" })).toBeVisible();
  await expect(currentScreen).not.toContainText("分数越高");
  await expect(currentScreen.getByRole("button", { name: /跳过|暂不回答/ })).toHaveCount(0);
  await expect(currentScreen.getByRole("button", { name: "下一题" })).toBeDisabled();
  await currentScreen.getByRole("radio", { name: "有时候 1 分" }).click();
  await currentScreen.getByRole("button", { name: "下一题" }).click();
  await expect(currentScreen).toContainText("2/5");
  await expect(currentScreen.getByRole("button", { name: "下一题" })).toBeDisabled();
  await currentScreen.getByRole("button", { name: "上一题" }).click();
  await expect(currentScreen).toContainText("1/5");
  await expect(currentScreen.getByRole("radio", { name: "有时候 1 分" })).toHaveAttribute("aria-checked", "true");
});

test("follow-up collection accepts the fixed administrator test ID", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "开始采集" }).click();
  const currentScreen = page.locator('.flow-screen[data-flow-current="true"]');
  await currentScreen.getByRole("button", { name: "后续测试" }).click();
  await currentScreen.getByRole("textbox", { name: "前两位" }).fill("ad");
  await currentScreen.getByLabel("年级").selectOption("24");
  await currentScreen.getByRole("textbox", { name: "后四位" }).fill("mast");
  await currentScreen.getByRole("button", { name: "确认采集编号" }).click();
  await expect(currentScreen).toContainText("AD-24-MAST");
});

test("identity actions keep visual spacing and the keyboard dismisses outside fields", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "开始采集" }).click();
  const currentScreen = page.locator('.flow-screen[data-flow-current="true"]');

  const modeButton = currentScreen.getByRole("button", { name: "初次测试" });
  const confirmButton = currentScreen.getByRole("button", { name: "确认采集编号" });
  const [modeBox, confirmBox] = await Promise.all([modeButton.boundingBox(), confirmButton.boundingBox()]);
  expect(modeBox).not.toBeNull();
  expect(confirmBox).not.toBeNull();
  expect((confirmBox?.y ?? 0) - ((modeBox?.y ?? 0) + (modeBox?.height ?? 0))).toBeGreaterThanOrEqual(15);

  await modeButton.click();
  await currentScreen.getByRole("spinbutton", { name: "年龄" }).click();
  await expect(page.getByTestId("keyboard-dock")).toHaveAttribute("data-visible", "true");
  await currentScreen.getByRole("heading", { name: "参与者识别" }).click();
  await expect(page.getByTestId("keyboard-dock")).toHaveAttribute("data-visible", "false");
});

test("completion hides assessment feedback and exports scores, valid signals and separate pauses", async ({ page }) => {
  test.setTimeout(45_000);
  let uploaded: Record<string, any> | undefined;
  await page.route("**/api/handwriting-sessions", async route => {
    uploaded = route.request().postDataJSON();
    expect(route.request().method()).toBe("POST");
    expect(route.request().headers()["x-filename"]).toBeTruthy();
    await route.fulfill({json:{storedAs:"synthetic-test.json"}});
  });
  await page.goto("/");
  await page.getByRole("button", {name:"开始采集"}).click();
  const screen = page.locator('.flow-screen[data-flow-current="true"]');
  await screen.getByRole("button", {name:"初次测试"}).click();
  await screen.getByRole("spinbutton", {name:"年龄"}).fill("20");
  await screen.getByLabel("年级").selectOption("24");
  await screen.getByLabel("来自省份").selectOption("440000");
  await screen.getByRole("button", {name:"生成采集编号"}).click();
  await screen.getByRole("checkbox").check();
  await screen.getByRole("button", {name:"继续",exact:true}).click();
  for (let i=0;i<5;i++) {
    {
      await screen.getByRole("radio", {name:"少于一半的时间 2 分"}).click();
      await screen.getByRole("button", {name:i===4 ? "进入书写采集" : "下一题"}).click();
    }
  }
  for (let task=0;task<4;task++) {
    await expect(screen.locator("canvas")).toBeVisible();
    if (task === 3) {
      await expect(screen.getByText("轨迹会上传用于研究，请不要写姓名、联系方式、学校等个人信息", { exact: true })).toBeVisible();
      await expect(screen).not.toContainText("内容不会上传");
    }
    await screen.locator("canvas").evaluate((canvas, taskIndex) => {
      // Synthetic ink covers dynamic pen pressure, a fixed pen fallback and touch input.
      canvas.setPointerCapture = () => {};
      canvas.releasePointerCapture = () => {};
      const rect=canvas.getBoundingClientRect();
      let stamp=performance.now();
      const fire=(type:string,x:number,y:number,pressure=0.5) => {
        const event=new PointerEvent(type,{bubbles:true,pointerId:1,pointerType:taskIndex<2?"pen":"touch",isPrimary:true,
          button:0,buttons:type==="pointerup"?0:1,pressure:type==="pointerup"?0:pressure,clientX:rect.left+x,clientY:rect.top+y,
          tiltX:0,tiltY:0});
        Object.defineProperty(event,"timeStamp",{value:stamp}); stamp+=40;
        Object.defineProperty(event,"getCoalescedEvents",{value:()=>[event]});
        canvas.dispatchEvent(event);
      };
      const strokeCount=taskIndex===0?3:45;
      for(let stroke=0;stroke<strokeCount;stroke++) {
        const x=20+(stroke%7)*35, y=25+(Math.floor(stroke/7)%5)*30;
        fire("pointerdown",x,y);
        for(let move=1;move<=12;move++) {
          if(stroke===0 && move===6) {
            // Twelve stationary 50 ms samples form one observed 600 ms pause.
            // A single long event gap would indicate missing samples instead.
            for(let sample=0;sample<12;sample++) {
              stamp+=10;
              fire("pointermove",x+5*(taskIndex===0?4:2),y+(taskIndex===0?0:5));
            }
          }
          fire("pointermove",x+move*(taskIndex===0?4:2),y+(taskIndex===0?0:(move%2)*5),taskIndex===0?0.2+0.1*(move%5):0.5);
        }
        fire("pointerup",x+(taskIndex===0?48:24),y);
        // Every lift lasts 700 ms and must stay separate from the in-stroke pause.
        if(stroke+1<strokeCount) stamp+=660;
      }
    },task);
    await screen.getByRole("button",{name:"确认本页书写"}).click();
  }
  await expect(screen).toHaveCount(1);
  await expect(screen.getByRole("heading",{name:"本轮采集完成"})).toBeVisible();
  await expect(screen.getByRole("region",{name:"WHO-5 状态评定"})).toHaveCount(0);
  await expect(screen.locator(".assessment-result, .assessment-score")).toHaveCount(0);
  await expect(screen).not.toContainText(/40\s*\/\s*100|原始分|近期心理幸福感偏低|进一步评估|量表来源与计分/);
  await page.screenshot({path:"test-results/who5-review.png"});
  const download=page.waitForEvent("download");
  await screen.getByRole("button",{name:"保存并导出 JSON"}).click();
  const exported=await download;
  const exportPath=await exported.path();
  expect(exportPath).not.toBeNull();
  const downloaded=JSON.parse(await readFile(exportPath!,"utf8"));
  await expect.poll(()=>uploaded?.questionnaire?.instrumentId).toBe("WHO_5");
  expect(downloaded).toEqual(uploaded);
  expect(uploaded?.schemaVersion).toBe("1.8.0");
  expect(uploaded?.questionnaire.items).toHaveLength(5);
  expect(uploaded?.questionnaire.scoring.higherDerivedScoreMeaning).toBe("better_mental_wellbeing");
  expect(uploaded?.questionnaire.derived.rawTotal).toBe(10);
  expect(uploaded?.questionnaire.derived.percentageScore).toBe(40);
  expect(uploaded?.questionnaire.derived.needsFurtherAssessment).toBe(true);
  expect(uploaded?.questionnaire.derived.resultTitle).toBe("近期心理幸福感偏低");
  expect(uploaded?.questionnaire.derived.recommendation).toContain("进一步评估");
  expect(uploaded?.device.deviceProfileId).toEqual(expect.any(String));
  expect(uploaded?.device.deviceProfileId).not.toBe("");
  expect(uploaded?.attempts).toHaveLength(4);
  for(const [index,attempt] of uploaded!.attempts.entries()) {
    expect(attempt.tiltValid).toBe(false);
    expect(attempt.pressureValid).toBe(index===0);
    expect(attempt.pressureValid).toBe(attempt.pressureDetected);
    expect(attempt.deviceProfileId).toBe(uploaded?.device.deviceProfileId);
    expect(attempt.metrics.pauseInStrokeMs).toBe(600);
    expect(attempt.metrics.betweenStrokeMs).toBe((attempt.strokeCount-1)*700);
    expect(attempt.points.every((point: Record<string,number>)=>point.tiltX===0 && point.tiltY===0)).toBe(true);
  }
  expect(uploaded?.attempts[1].input.penDetected).toBe(true);
  expect(uploaded?.attempts[2].input.observedPointerTypes).toEqual(["touch"]);
  expect(uploaded?.attempts[3].input.observedPointerTypes).toEqual(["touch"]);
  await expect(screen).not.toContainText(/40\s*\/\s*100|原始分|近期心理幸福感偏低|进一步评估/);
});
