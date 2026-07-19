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
    <form onSubmit={handleSubmit} style={styles.card}>
      <h1 style={styles.title}>ExamCraft AI</h1>
      <p style={styles.subtitle}>Đăng nhập để tiếp tục</p>

      <label style={styles.label}>
        Email
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={styles.input}
        />
      </label>

      <label style={styles.label}>
        Mật khẩu
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          style={styles.input}
        />
      </label>

      {error && <p style={styles.error}>{error}</p>}

      <button type="submit" disabled={submitting} style={styles.button}>
        {submitting ? "Đang đăng nhập..." : "Đăng nhập"}
      </button>
    </form>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    width: 360,
    maxWidth: "100%",
    padding: 32,
    borderRadius: 16,
    background: "var(--surface)",
    boxShadow: "0 12px 32px rgba(15, 27, 51, 0.12)",
    display: "flex",
    flexDirection: "column",
    gap: 14,
  },
  title: { margin: 0, fontSize: 22 },
  subtitle: { margin: "0 0 8px", color: "var(--muted)" },
  label: { display: "flex", flexDirection: "column", gap: 6, fontWeight: 600, fontSize: 14 },
  input: {
    height: 40,
    padding: "0 12px",
    borderRadius: 8,
    border: "1px solid var(--border)",
    fontSize: 14,
  },
  error: { color: "var(--danger)", fontSize: 13, margin: 0 },
  button: {
    height: 42,
    marginTop: 8,
    borderRadius: 8,
    border: "none",
    background: "var(--primary)",
    color: "#fff",
    fontWeight: 600,
  },
};
