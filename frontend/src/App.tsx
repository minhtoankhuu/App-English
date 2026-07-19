import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { fetchCurrentUser } from "./api/auth";
import { LoginForm } from "./LoginForm";
import { Layout } from "./Layout";
import { ExamListPage } from "./pages/ExamListPage";
import { ExamBuilderPage } from "./pages/ExamBuilderPage";
import { ExamReviewPage } from "./pages/ExamReviewPage";
import { ExamExportPage } from "./pages/ExamExportPage";
import { AdminOverviewPage } from "./pages/AdminOverviewPage";
import { AdminAuditLogsPage } from "./pages/AdminAuditLogsPage";
import { AdminTeachersPage } from "./pages/AdminTeachersPage";
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
    return (
      <div className="center-screen">
        <p style={{ color: "var(--muted)" }}>Đang kiểm tra phiên đăng nhập...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="center-screen">
        <LoginForm onSuccess={setUser} />
      </div>
    );
  }

  const isAdmin = user.role === "admin";
  const homePath = isAdmin ? "/admin" : "/exams";
  const teacherOnly = (element: ReactNode) => (isAdmin ? <Navigate to="/admin" replace /> : element);

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout user={user} onLogout={() => setUser(null)} />}>
          <Route path="/" element={<Navigate to={homePath} replace />} />
          <Route path="/exams" element={teacherOnly(<ExamListPage />)} />
          <Route path="/exams/:examId/builder" element={teacherOnly(<ExamBuilderPage />)} />
          <Route path="/exams/:examId/review" element={teacherOnly(<ExamReviewPage />)} />
          <Route path="/exams/:examId/export" element={teacherOnly(<ExamExportPage />)} />
          <Route path="/admin" element={isAdmin ? <AdminOverviewPage /> : <Navigate to="/exams" replace />} />
          <Route
            path="/admin/audit-logs"
            element={isAdmin ? <AdminAuditLogsPage /> : <Navigate to="/exams" replace />}
          />
          <Route
            path="/admin/teachers"
            element={isAdmin ? <AdminTeachersPage /> : <Navigate to="/exams" replace />}
          />
          <Route path="*" element={<Navigate to={homePath} replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
