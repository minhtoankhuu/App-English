import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listTeachers } from "../api/admin";

interface AdminCardData {
  title: string;
  description: string;
  chip: string;
  to?: string;
  implemented: boolean;
}

type TeacherStat =
  | { status: "loading" }
  | { status: "success"; activeCount: number }
  | { status: "error" };

export function AdminOverviewPage() {
  const [teacherStat, setTeacherStat] = useState<TeacherStat>({ status: "loading" });

  useEffect(() => {
    listTeachers()
      .then((teachers) =>
        setTeacherStat({ status: "success", activeCount: teachers.filter((teacher) => teacher.is_active).length }),
      )
      .catch(() => setTeacherStat({ status: "error" }));
  }, []);

  const teacherChip =
    teacherStat.status === "loading"
      ? "Đang tải..."
      : teacherStat.status === "error"
        ? "Không tải được dữ liệu"
        : `${teacherStat.activeCount} giáo viên hoạt động`;

  const cards: AdminCardData[] = [
    {
      title: "Kho kiến thức & RAG",
      description: "Nhập PDF/DOCX, kiểm tra, xuất bản và lập phiên bản tài liệu.",
      chip: "Chưa triển khai — chờ Giai đoạn 1D",
      implemented: false,
    },
    {
      title: "Danh mục học thuật",
      description: "Khối lớp, cấp học, bộ sách, Unit và bảng ánh xạ trình độ.",
      chip: "Đã seed sẵn — chưa có màn chỉnh sửa",
      implemented: false,
    },
    {
      title: "Dạng bài & template chuẩn",
      description: "Schema, prompt, validation rule và renderer của từng dạng.",
      chip: "10 dạng bài đã seed — chưa có màn chỉnh sửa",
      implemented: false,
    },
    {
      title: "Thư viện hình ảnh",
      description: "Biển báo, thông báo và minh họa cho dạng bài có hình.",
      chip: "Chưa triển khai — chờ Giai đoạn 1D",
      implemented: false,
    },
    {
      title: "Cấu hình AI",
      description: "Provider, model, API key, embedding và reranker.",
      chip: "Chưa triển khai — chờ Giai đoạn 1D",
      implemented: false,
    },
    {
      title: "Audit log",
      description: "Lịch sử thao tác quản trị tài khoản giáo viên.",
      chip: "Lịch sử thao tác quản trị",
      to: "/admin/audit-logs",
      implemented: true,
    },
    {
      title: "Tài khoản & phân quyền",
      description: "Tài khoản giáo viên, trạng thái và quyền truy cập.",
      chip: teacherChip,
      to: "/admin/teachers",
      implemented: true,
    },
  ];

  return (
    <div style={{ display: "grid", gap: 18 }}>
      <section style={{ background: "var(--surface)", borderRadius: 14, padding: 20 }}>
        <h2 style={{ marginTop: 0 }}>Quản trị hệ thống</h2>
        <p style={{ color: "var(--muted)", fontSize: 13 }}>2 khối bên dưới đã có chức năng thật.</p>

        <div style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))" }}>
          {cards.map((card) => {
            const content = (
              <>
                <h3 style={{ margin: "0 0 6px", fontSize: 15 }}>{card.title}</h3>
                <p style={{ margin: "0 0 10px", fontSize: 12.5, color: "var(--muted)" }}>{card.description}</p>
                <span
                  style={{
                    display: "inline-block",
                    fontSize: 11,
                    fontWeight: 600,
                    padding: "3px 9px",
                    borderRadius: 999,
                    background: card.implemented ? "#ecf1fe" : "#f1f2f5",
                    color: card.implemented ? "var(--primary-dark)" : "var(--muted)",
                  }}
                >
                  {card.chip}
                </span>
              </>
            );

            const cardStyle: React.CSSProperties = {
              display: "block",
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: 16,
              textDecoration: "none",
              color: "inherit",
              cursor: card.implemented ? "pointer" : "default",
              opacity: card.implemented ? 1 : 0.75,
            };

            return card.to ? (
              <Link key={card.title} to={card.to} style={cardStyle}>
                {content}
              </Link>
            ) : (
              <div key={card.title} style={cardStyle}>
                {content}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
