import { useEffect, useState } from "react";
import { fetchCurrentUser } from "./api/auth";
import { LoginForm } from "./LoginForm";
import { Dashboard } from "./Dashboard";
import type { UserOut } from "./types/auth";

function App() {
  const [user, setUser] = useState<UserOut | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);

  useEffect(() => {
    fetchCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setCheckingSession(false));
  }, []);

  if (checkingSession) {
    return <p style={{ color: "var(--muted)" }}>Đang kiểm tra phiên đăng nhập...</p>;
  }

  if (!user) {
    return <LoginForm onSuccess={setUser} />;
  }

  return <Dashboard user={user} onLogout={() => setUser(null)} />;
}

export default App;
