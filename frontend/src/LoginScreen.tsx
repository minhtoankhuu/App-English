import { LoginForm } from "./LoginForm";
import type { UserOut } from "./types/auth";

const FEATURES = [
  "Sinh đề bám đúng Unit và trình độ CEFR của học sinh",
  "Giáo viên duyệt 100% câu hỏi trước khi xuất đề",
  "Xuất DOCX chuẩn định dạng, kèm mã đề A/B/C/D",
];

interface LoginScreenProps {
  onSuccess: (user: UserOut) => void;
}

export function LoginScreen({ onSuccess }: LoginScreenProps) {
  return (
    <div className="login-shell">
      <div className="login-brand-panel">
        <span className="brand-mark login-brand-mark">E</span>
        <h1 className="login-brand-title">
          ExamCraft <em>AI</em>
        </h1>
        <p className="login-tagline">
          Soạn đề tiếng Anh theo sách Global Success, có AI hỗ trợ và giáo viên toàn quyền kiểm duyệt trước khi xuất
          bản.
        </p>
        <ul className="login-features">
          {FEATURES.map((text) => (
            <li key={text} className="login-feature">
              <span className="login-feature-dot" aria-hidden="true" />
              {text}
            </li>
          ))}
        </ul>
      </div>
      <div className="login-form-panel">
        <LoginForm onSuccess={onSuccess} />
      </div>
    </div>
  );
}
