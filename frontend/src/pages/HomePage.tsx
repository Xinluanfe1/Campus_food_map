import { useAuth } from "../auth/AuthContext";
import { useHealthStatus } from "../hooks/useHealthStatus";

const statusText: Record<string, string> = {
  loading: "正在检查后端服务……",
  ok: "后端连接正常",
  error: "后端连接失败",
};

export default function HomePage() {
  const health = useHealthStatus();
  const { user, loading } = useAuth();

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
        <p>当前页面用于验证前端可以启动并正确访问后端接口。</p>
        <p className={`health health-${health.phase}`}>
          {statusText[health.phase]}：{health.message}
        </p>
        <p className="hint">
          后端健康检查地址：<code>http://127.0.0.1:8000/api/v1/health</code>
        </p>
      </section>

      <section className="card">
        <h2>登录状态</h2>
        {loading ? (
          <p>正在检查登录状态……</p>
        ) : user ? (
          <p>
            当前登录用户：{user.username}（{user.role === "admin" ? "管理员" : "普通用户"}）
          </p>
        ) : (
          <p>当前未登录。登录后可以查看店铺详情、评分评价并提交店铺。</p>
        )}
      </section>

      <footer className="page-footer">
        <p>默认示范校园：西南交通大学犀浦校区（地图功能在后续步骤提供）</p>
      </footer>
    </main>
  );
}
