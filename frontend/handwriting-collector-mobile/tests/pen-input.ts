import type { Locator } from "@playwright/test";

export async function ink(canvas:Locator, warmup=false, strokes=45) {
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
