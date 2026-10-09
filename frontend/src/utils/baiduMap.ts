/**
 * 百度地图 JSAPI（BMapGL）加载工具。
 *
 * AK 由后端从部署环境变量读取后下发，不会写入代码仓库。
 * SDK 地址存放在校园配置的 tile_url_template 字段（真实地图-百度模式下为 SDK 地址，不含 AK）。
 */

export const DEFAULT_BAIDU_SDK_URL = "https://api.map.baidu.com/api?type=webgl&v=1.0";

declare global {
  interface Window {
    // 百度地图 SDK 没有官方 TypeScript 类型，这里使用宽松类型
    BMapGL?: any;
  }
}

let loadedUrl: string | null = null;
let pending: { url: string; promise: Promise<void> } | null = null;
let callbackCounter = 0;

export function buildBaiduSdkUrl(sdkUrl: string | null | undefined, ak: string): string {
  const base = sdkUrl && sdkUrl.startsWith("http") ? sdkUrl : DEFAULT_BAIDU_SDK_URL;
  const separator = base.includes("?") ? "&" : "?";
  return `${base}${separator}ak=${encodeURIComponent(ak)}`;
}

export function loadBaiduMapSdk(sdkUrl: string | null | undefined, ak: string): Promise<void> {
  const url = buildBaiduSdkUrl(sdkUrl, ak);
  if (window.BMapGL?.Map && loadedUrl === url) {
    return Promise.resolve();
  }
  if (pending && pending.url === url) {
    return pending.promise;
  }

  const promise = new Promise<void>((resolve, reject) => {
    // 百度返回的引导脚本会动态插入真正的 SDK，因此必须使用 callback 异步加载方式：
    // 直接 append 的 script 在页面加载完成后执行 document.write 是无效的。
    callbackCounter += 1;
    const callbackName = `__cfmBaiduReady${callbackCounter}`;
    const globalWindow = window as unknown as Record<string, unknown>;
    const cleanup = () => {
      delete globalWindow[callbackName];
    };
    let settled = false;

    globalWindow[callbackName] = () => {
      cleanup();
      settled = true;
      if (window.BMapGL?.Map) {
        loadedUrl = url;
        resolve();
      } else {
        reject(new Error("百度地图 SDK 初始化失败。"));
      }
    };

    const script = document.createElement("script");
    script.src = `${url}&callback=${callbackName}`;
    script.async = true;
    script.onerror = () => {
      cleanup();
      settled = true;
      reject(new Error("百度地图 SDK 加载失败，请检查网络以及 AK 的 Referer 白名单设置。"));
    };
    document.head.appendChild(script);

    window.setTimeout(() => {
      if (!settled) {
        cleanup();
        reject(new Error("百度地图 SDK 加载超时，请检查网络以及 AK 的 Referer 白名单设置。"));
      }
    }, 15000);
  });

  pending = { url, promise };
  return promise;
}
