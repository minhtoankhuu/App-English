import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  size?: "md" | "lg";
}

export function Modal({ open, onClose, title, children, size = "md" }: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  // Chỉ mount <dialog> khi mở — tránh nhiều dialog cùng nằm trong DOM lúc đóng
  // (gây trùng label khi có nhiều modal dùng chung tên trường như "Lưu"/"Họ tên").
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (typeof dialog.showModal === "function") {
      try {
        dialog.showModal();
      } catch {
        // jsdom (test) chỉ có showModal dạng stub không hoạt động — bỏ qua.
      }
    }
    // Luôn đặt thuộc tính open: vô hại khi showModal đã set (trình duyệt thật),
    // và là fallback bắt buộc khi showModal là stub không làm gì (môi trường test).
    dialog.setAttribute("open", "");
    // Phụ thuộc `open`: dialog chỉ được mount vào DOM (ref gắn vào) sau khi `open`
    // chuyển true — deps rỗng sẽ bỏ lỡ lần đó vì effect đã chạy một lần lúc dialog
    // còn null (render trước đó return null khi open=false).
  }, [open]);

  if (!open) return null;

  return (
    <dialog ref={dialogRef} className={`app-modal${size === "lg" ? " app-modal-lg" : ""}`} onClose={onClose} onCancel={onClose}>
      <div className="app-modal-header">
        <h2>{title}</h2>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Đóng">
          ✕
        </button>
      </div>
      {children}
    </dialog>
  );
}
