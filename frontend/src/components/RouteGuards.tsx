import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <main className="page">
        <p>正在检查登录状态……</p>
      </main>
    );
  }
  if (!user) {
    return (
      <main className="page">
        <p>
          该页面需要登录，请先<Link to="/login">登录</Link>。
        </p>
      </main>
    );
  }
  return <>{children}</>;
}

export function RequireAdmin({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <main className="page">
        <p>正在检查登录状态……</p>
      </main>
    );
  }
  if (!user) {
    return (
      <main className="page">
        <p>
          该页面需要登录，请先<Link to="/login">登录</Link>。
        </p>
      </main>
    );
  }
  if (user.role !== "admin") {
    return (
      <main className="page">
        <p>该页面需要管理员权限，当前账号无权访问。</p>
      </main>
    );
  }
  return <>{children}</>;
}
