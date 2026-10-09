import { useHealthStatus } from "./hooks/useHealthStatus";
import "./styles.css";

const statusText: Record<string, string> = {
  loading: "正在检查后端服务……",
  ok: "后端连接正常",
  error: "后端连接失败",
};

export default function App() {
  const health = useHealthStatus();

  return (
    <main className="page">
      <header className="page-header">
        <h1>校园美食地图</h1>
        <p className="subtitle">
          以校园地图为核心、由用户共同贡献店铺数据、通过评分评价与排行榜帮助用户发现校园美食的可配置平台。
        </p>
      </header>

      <section className="card">
        <h2>开发环境自检</h2>
        <p>
          当前页面是第一阶段的项目骨架页面，用于验证前端可以启动并正确访问后端健康检查接口。
        </p>
        <p className={`health health-${health.phase}`}>
          {statusText[health.phase]}：{health.message}
        </p>
        <p className="hint">
          后端健康检查地址：<code>http://127.0.0.1:8000/api/v1/health</code>
        </p>
      </section>

      <footer className="page-footer">
        <p>默认示范校园：西南交通大学犀浦校区（后续版本提供地图功能）</p>
      </footer>
    </main>
  );
}
