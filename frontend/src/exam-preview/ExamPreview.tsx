import type { CSSProperties } from "react";
import type { ExamPreviewOut, PreviewBlockOut } from "../types/examPreview";

interface ExamPreviewProps {
  preview: ExamPreviewOut | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export function ExamPreview({ preview, loading, error, onRetry }: ExamPreviewProps) {
  if (loading) {
    return <p style={{ color: "var(--muted)" }}>Đang dựng bản xem trước...</p>;
  }

  if (error) {
    return (
      <div role="alert" style={statusStyle}>
        <p style={{ margin: 0, color: "var(--danger)" }}>{error}</p>
        <button type="button" onClick={onRetry} style={buttonStyle}>
          Thử lại
        </button>
      </div>
    );
  }

  if (!preview) return null;

  const isEmpty = preview.pages.every((page) => page.blocks.length === 0);

  return (
    <section aria-label="Bản xem trước đề A4" style={{ display: "grid", gap: 16 }}>
      <header style={toolbarStyle}>
        <div>
          <p style={{ margin: 0, fontSize: 12, color: "var(--muted)", fontWeight: 700 }}>BẢN XEM TRƯỚC A4</p>
          <h2 style={{ margin: "4px 0 0", fontSize: 18 }}>{preview.title}</h2>
        </div>
        <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>
          {preview.total_questions} câu · {preview.total_points} điểm · {preview.page_count} trang
        </p>
      </header>

      {isEmpty ? (
        <p style={statusStyle}>Thêm phần để xem trước đề</p>
      ) : (
        <div style={{ display: "grid", gap: 18 }}>
          {preview.pages.map((page) => (
            <article key={page.page_number} aria-label={`Trang ${page.page_number}/${preview.page_count}`} style={pageStyle}>
              <header style={{ borderBottom: "1px solid var(--border)", paddingBottom: 10 }}>
                <p style={{ margin: 0, fontSize: 12, color: "var(--muted)", fontWeight: 700 }}>{preview.title}</p>
              </header>

              <div style={{ display: "grid", gap: 14, marginTop: 14 }}>
                {page.blocks.map((block) => (
                  <PreviewBlock key={`${block.block_id}-${block.question_start ?? "empty"}`} block={block} />
                ))}
              </div>

              <footer style={footerStyle}>Trang {page.page_number}/{preview.page_count}</footer>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function PreviewBlock({ block }: { block: PreviewBlockOut }) {
  let previousPassage: string | null = null;

  return (
    <section>
      <h3 style={{ margin: 0, fontSize: 14 }}>
        {block.section_label}. {block.title}
        {block.continuation ? " (tiếp theo)" : ""}
      </h3>
      {block.instruction && <p style={{ margin: "5px 0 8px", fontSize: 13, fontStyle: "italic" }}>{block.instruction}</p>}
      <div style={{ display: "grid", gap: 8 }}>
        {block.questions.map((question) => {
          const showPassage = Boolean(question.passage_text && question.passage_text !== previousPassage);
          previousPassage = question.passage_text;

          return (
            <div key={question.question_number} style={{ fontSize: 13 }}>
              {showPassage && <p style={{ margin: "0 0 6px", whiteSpace: "pre-wrap" }}>{question.passage_text}</p>}
              <p style={{ margin: 0 }}>
                Câu {question.question_number}. {question.is_placeholder ? "Chưa có nội dung" : (question.prompt_text ?? "Chưa có nội dung")}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

const toolbarStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-end",
  gap: 12,
  flexWrap: "wrap",
  background: "var(--surface)",
  borderRadius: 14,
  padding: 16,
};

const statusStyle: CSSProperties = {
  margin: 0,
  display: "flex",
  alignItems: "center",
  gap: 10,
  padding: 16,
  borderRadius: 10,
  background: "var(--surface)",
};

const buttonStyle: CSSProperties = {
  padding: "6px 12px",
  borderRadius: 8,
  border: "1px solid var(--border)",
  background: "#fff",
  fontWeight: 600,
};

const pageStyle: CSSProperties = {
  aspectRatio: "210 / 297",
  width: "100%",
  maxWidth: 760,
  margin: "0 auto",
  padding: 32,
  background: "#fff",
  border: "1px solid var(--border)",
  boxSizing: "border-box",
  display: "flex",
  flexDirection: "column",
};

const footerStyle: CSSProperties = {
  marginTop: "auto",
  paddingTop: 12,
  borderTop: "1px solid var(--border)",
  textAlign: "center",
  fontSize: 12,
  color: "var(--muted)",
};
