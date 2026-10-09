/**
 * 使用 Chrome DevTools 协议验证店铺详情信息卡片的锚定效果。
 *
 * 前置条件：
 * 1. 后端与前端开发服务器已经启动（127.0.0.1:8000 与 127.0.0.1:5173）；
 * 2. 数据库中存在演示用户（默认使用“美食探索者 / demo-password-2026”）。
 *
 * 运行方式（在 frontend 目录执行，需要先安装 Chrome）：
 *   node scripts/capture-detail-card.mjs [输出图片路径] [页面地址]
 *
 * 可通过环境变量覆盖登录账号：
 *   CFM_LOGIN_USERNAME、CFM_LOGIN_PASSWORD
 */

import { spawn } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const DEBUG_PORT = 9333;
const OUTPUT_PATH = process.argv[2] ?? path.join(tmpdir(), "cfm-detail-card.png");
const TARGET_URL = process.argv[3] ?? "http://127.0.0.1:5173/";
const LOGIN = {
  username: process.env.CFM_LOGIN_USERNAME ?? "美食探索者",
  password: process.env.CFM_LOGIN_PASSWORD ?? "demo-password-2026",
};

const profileDir = mkdtempSync(path.join(tmpdir(), "cfm-chrome-"));
const chrome = spawn(
  CHROME_PATH,
  [
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    `--remote-debugging-port=${DEBUG_PORT}`,
    `--user-data-dir=${profileDir}`,
    "--window-size=1500,1100",
    "about:blank",
  ],
  { stdio: "ignore" },
);

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function debuggerUrl() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/list`);
      const targets = await response.json();
      const page = targets.find((target) => target.type === "page");
      if (page?.webSocketDebuggerUrl) {
        return page.webSocketDebuggerUrl;
      }
    } catch {
      // 等待 Chrome 启动
    }
    await sleep(250);
  }
  throw new Error("无法连接到 Chrome 调试端口");
}

function createClient(socket) {
  let nextId = 1;
  const pending = new Map();

  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) {
        reject(new Error(JSON.stringify(message.error)));
      } else {
        resolve(message.result);
      }
    }
  });

  return {
    send(method, params = {}) {
      const id = nextId;
      nextId += 1;
      return new Promise((resolve, reject) => {
        pending.set(id, { resolve, reject });
        socket.send(JSON.stringify({ id, method, params }));
      });
    },
  };
}

async function main() {
  const url = await debuggerUrl();
  const socket = new WebSocket(url);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve);
    socket.addEventListener("error", reject);
  });

  const client = createClient(socket);

  // 收集页面异常与控制台输出，便于定位前端错误
  const pageLogs = [];
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.method === "Runtime.exceptionThrown") {
      const details = message.params?.exceptionDetails;
      pageLogs.push(
        `页面异常：${details?.exception?.description ?? details?.text ?? "未知异常"}`,
      );
    }
    if (message.method === "Runtime.consoleAPICalled" && message.params?.type === "error") {
      pageLogs.push(
        `控制台错误：${(message.params.args ?? [])
          .map((argument) => argument.value ?? argument.description ?? "")
          .join(" ")}`,
      );
    }
  });

  await client.send("Page.enable");
  await client.send("Runtime.enable");

  // 1. 打开页面并登录（登录接口不需要 CSRF 令牌）
  await client.send("Page.navigate", { url: TARGET_URL });
  await sleep(4000);
  const loginResult = await client.send("Runtime.evaluate", {
    expression: `fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(${JSON.stringify(LOGIN)}),
    }).then((response) => response.status)`,
    awaitPromise: true,
    returnByValue: true,
  });
  console.log("登录状态码：", loginResult.result.value);

  // 2. 重新加载页面，让前端读取登录状态
  await client.send("Page.navigate", { url: TARGET_URL });
  await sleep(5000);

  // 3. 计算第一个地图点位的屏幕坐标，并使用真实鼠标事件点击
  const markerRect = await client.send("Runtime.evaluate", {
    expression: `(() => {
      const markers = document.querySelectorAll('path.leaflet-interactive');
      if (markers.length === 0) return null;
      const marker = markers[0];
      const box = marker.getBoundingClientRect();
      return {
        count: markers.length,
        x: Math.round(box.x + box.width / 2),
        y: Math.round(box.y + box.height / 2),
      };
    })()`,
    returnByValue: true,
  });

  const markerInfo = markerRect.result.value;
  console.log("点位信息：", JSON.stringify(markerInfo));
  if (markerInfo) {
    await client.send("Input.dispatchMouseEvent", {
      type: "mousePressed",
      x: markerInfo.x,
      y: markerInfo.y,
      button: "left",
      clickCount: 1,
    });
    await client.send("Input.dispatchMouseEvent", {
      type: "mouseReleased",
      x: markerInfo.x,
      y: markerInfo.y,
      button: "left",
      clickCount: 1,
    });
  }

  const immediate = await client.send("Runtime.evaluate", {
    expression: `({
      card: Boolean(document.querySelector('.shop-card')),
      notice: document.querySelector('.map-notice')?.innerText ?? null,
    })`,
    returnByValue: true,
  });
  console.log("点击后立即状态：", JSON.stringify(immediate.result.value));

  await sleep(2500);

  // 4. 读取卡片与点位的位置关系，确认卡片锚定在点位附近
  const measure = await client.send("Runtime.evaluate", {
    expression: `(() => {
      const card = document.querySelector('.shop-card');
      const marker = document.querySelector('path.leaflet-interactive');
      if (!card || !marker) return { card: null };
      const cardBox = card.getBoundingClientRect();
      const markerBox = marker.getBoundingClientRect();
      return {
        card: {
          x: Math.round(cardBox.x), y: Math.round(cardBox.y),
          width: Math.round(cardBox.width), height: Math.round(cardBox.height),
          side: card.className,
        },
        marker: { x: Math.round(markerBox.x), y: Math.round(markerBox.y) },
        text: card.innerText.replace(/\\n/g, ' | '),
        overlayCount: document.querySelectorAll('.shop-card').length,
        notice: document.querySelector('.map-notice')?.innerText ?? null,
      };
    })()`,
    returnByValue: true,
  });
  console.log("卡片测量：", JSON.stringify(measure.result.value, null, 2));
  if (pageLogs.length > 0) {
    console.log("页面日志：");
    for (const log of pageLogs) {
      console.log("  " + log);
    }
  } else {
    console.log("页面日志：无异常");
  }

  const screenshot = await client.send("Page.captureScreenshot", { format: "png" });
  writeFileSync(OUTPUT_PATH, Buffer.from(screenshot.data, "base64"));
  console.log("截图已保存：", OUTPUT_PATH);

  socket.close();
  chrome.kill();
}

main()
  .catch((error) => {
    console.error("验证失败：", error.message);
    chrome.kill();
    process.exit(1);
  })
  .finally(() => {
    setTimeout(() => process.exit(0), 500);
  });
