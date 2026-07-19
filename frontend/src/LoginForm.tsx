import { useState } from "react";
import type { FormEvent } from "react";
import { login } from "./api/auth";
import { ApiError } from "./api/client";
import type { UserOut } from "./types/auth";

interface LoginFormProps {
  onSuccess: (user: UserOut) => void;
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login({ email, password });
      onSuccess(user);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không thể kết nối máy chủ");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="login-card">
      <span className="brand-mark login-mark">E</span>
      <h1 className="login-title">ExamCraft AI</h1>
      <p className="login-subtitle">Đăng nhập để tiếp tục</p>

      <label>
        Email
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      </label>

      <label>
        Mật khẩu
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      </label>

      {error && <p className="login-error">{error}</p>}

      <button type="submit" className="button primary large" disabled={submitting}>
        {submitting ? "Đang đăng nhập..." : "Đăng nhập"}
      </button>
    </form>
  );
}
