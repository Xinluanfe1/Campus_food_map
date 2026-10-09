import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export default function AppHeader() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleLogout() {
    setError("");
    setBusy(true);
    try {
      await logout();
      navigate("/");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "退出登录失败，请稍后重试。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <header className="app-header">
      <div className="app-header-inner">
        <Link className="brand" to="/">
          校园美食地图
        </Link>
        <nav className="app-nav">
          <Link to="/">地图首页</Link>
          {loading ? (
            <span className="nav-muted">正在检查登录状态……</span>
          ) : user ? (
            <>
              <Link to="/submit">提交店铺</Link>
              {user.role === "admin" && <Link to="/admin/shops">审核店铺</Link>}
              <span className="nav-muted">
                {user.username}
                {user.role === "admin" ? "（管理员）" : ""}
              </span>
              <button type="button" onClick={handleLogout} disabled={busy}>
                {busy ? "退出中……" : "退出登录"}
              </button>
            </>
          ) : (
            <>
              <Link to="/login">登录</Link>
              <Link to="/register">注册</Link>
            </>
          )}
        </nav>
      </div>
      {error && <p className="alert alert-error header-alert">{error}</p>}
    </header>
  );
}
