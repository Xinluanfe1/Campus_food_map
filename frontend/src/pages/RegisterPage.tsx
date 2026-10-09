import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { registerAccount } from "../api/client";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("两次输入的密码不一致，请重新输入。");
      return;
    }

    setSubmitting(true);
    try {
      const result = await registerAccount(username.trim(), password);
      navigate("/login", { state: { message: result.message } });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "注册失败，请稍后重试。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page auth-page">
      <section className="card">
        <p className="brand-text">校园美食地图</p>
        <h2>用户注册</h2>
        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            用户名（2 至 20 个字符）
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              minLength={2}
              maxLength={20}
              required
            />
          </label>
          <label>
            密码（至少 8 个字符）
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="new-password"
              minLength={8}
              required
            />
          </label>
          <label>
            确认密码
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              autoComplete="new-password"
              minLength={8}
              required
            />
          </label>
          <button type="submit" disabled={submitting}>
            {submitting ? "注册中……" : "注册"}
          </button>
        </form>
        {error && <p className="alert alert-error">{error}</p>}
        <p className="auth-switch">
          已有账号？<Link to="/login">前往登录</Link>
        </p>
      </section>
    </main>
  );
}
