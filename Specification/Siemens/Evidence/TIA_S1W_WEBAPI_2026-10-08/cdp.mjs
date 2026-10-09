// Minimal Chrome DevTools Protocol driver for a headless Chrome started with
// --remote-debugging-port=9333. Actions run in order on the first page target:
//   goto:<url>  click:<x>,<y>  type:<text>  key:<Enter|Tab|...>  wait:<ms>  shot:<file.png>
import fs from 'node:fs';

const targets = await (await fetch('http://127.0.0.1:9333/json/list')).json();
const page = targets.find((t) => t.type === 'page');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
let nextId = 1;
const pending = new Map();
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
};
const send = (method, params = {}) => new Promise((resolve) => {
  const id = nextId++;
  pending.set(id, resolve);
  ws.send(JSON.stringify({ id, method, params }));
});
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
for (const action of process.argv.slice(2)) {
  const [verb, ...rest] = action.split(':');
  const arg = rest.join(':');
  if (verb === 'goto') { await send('Page.navigate', { url: arg }); }
  else if (verb === 'wait') { await sleep(Number(arg)); }
  else if (verb === 'click') {
    const [x, y] = arg.split(',').map(Number);
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
  } else if (verb === 'wheel') {
    const [x, y, dy] = arg.split(',').map(Number);
    await send('Input.dispatchMouseEvent', { type: 'mouseWheel', x, y, deltaX: 0, deltaY: dy });
  } else if (verb === 'type') { await send('Input.insertText', { text: arg }); }
  else if (verb === 'key') {
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: arg, code: arg, windowsVirtualKeyCode: arg === 'Enter' ? 13 : 9 });
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: arg, code: arg, windowsVirtualKeyCode: arg === 'Enter' ? 13 : 9 });
  } else if (verb === 'shot') {
    const res = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(arg, Buffer.from(res.result.data, 'base64'));
    console.log('shot', arg);
  } else { console.log('unknown action', action); }
}
ws.close();
