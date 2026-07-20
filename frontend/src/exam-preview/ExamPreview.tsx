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
      <div role="alert" style={{ display: "flex", alignItems: "center", gap: 10, padding: 16, borderRadius: 10, background: "var(--surface)" }}>
        <p style={{ margin: 0, color: "var(--danger)" }}>{error}</p>
        <button type="button" onClick={onRetry} className="button secondary compact">
          Thử lại
        </button>
      </div>
    );
  }

  if (!preview) return null;

  return (
    <div className="preview-panel" aria-label="Bản xem trước đề A4">
      <div className="section-heading preview-heading">
        <div>
          <h2>Xem trước A4</h2>
          <p>
            {preview.total_questions} câu · {preview.total_points} điểm · {preview.page_count} trang
          </p>
        </div>
      </div>

      <div style={{ display: "grid", gap: 18 }}>
        {preview.pages.map((page) => (
          <article key={page.page_number} aria-label={`Trang ${page.page_number}/${preview.page_count}`} className="paper">
            <header className="paper-header">
              <div className="paper-header-top">
                <div className="paper-header-fields">
                  <p>School: ..........................................</p>
                  <p>Full name: .......................................... Class: ..........</p>
                </div>
                <div className="paper-score-box">Mark</div>
              </div>
              <div className="paper-title-block">
                <strong>{preview.title.toUpperCase()}</strong>
              </div>
            </header>

            <div style={{ flex: 1 }}>
              {page.blocks.length === 0 ? (
                <p style={{ margin: "16px 0 0", color: "var(--muted)", fontSize: 13 }}>Thêm phần để xem trước đề</p>
              ) : (
                page.blocks.map((block) => (
                  <PreviewBlock key={`${block.block_id}-${block.question_start ?? "empty"}`} block={block} />
                ))
              )}
            </div>

            <footer className="paper-footer">
              Trang {page.page_number}/{preview.page_count}
            </footer>
          </article>
        ))}
      </div>

      <dl className="metrics">
        <div>
          <dt>Câu hỏi</dt>
          <dd>{preview.total_questions}</dd>
        </div>
        <div>
          <dt>Tổng điểm</dt>
          <dd>{preview.total_points}</dd>
        </div>
        <div>
          <dt>Trang</dt>
          <dd>{preview.page_count}</dd>
        </div>
      </dl>
    </div>
  );
}

function PreviewBlock({ block }: { block: PreviewBlockOut }) {
  let previousPassage: string | null = null;
  let previousPartNumber: number | null = null;

  return (
    <section>
      <h3>
        {block.section_label}. {block.title}
        {block.continuation ? " (tiếp theo)" : ""}
      </h3>
      <p style={{ margin: "4px 0 8px", fontSize: 12, color: "var(--muted)", fontFamily: "inherit" }}>
        {block.question_start}–{block.question_end} · {block.points} điểm
      </p>
      {block.instruction && <p style={{ fontStyle: "italic" }}>{block.instruction}</p>}
      <div style={{ display: "grid", gap: 8 }}>
        {block.questions.map((question) => {
          const showPassage = Boolean(question.passage_text && question.passage_text !== previousPassage);
          previousPassage = question.passage_text;
          const showPart = Boolean(question.part_number !== null && question.part_number !== previousPartNumber);
          previousPartNumber = question.part_number;

          return (
            <div key={question.question_number}>
              {showPart && (
                <p style={{ fontWeight: 600 }}>
                  {question.part_number}. {question.part_title}
                  {question.part_instruction ? ` — ${question.part_instruction}` : ""}
                </p>
              )}
              {showPassage && <p style={{ whiteSpace: "pre-wrap" }}>{question.passage_text}</p>}
              <p>
                {question.question_number}. {question.is_placeholder ? "................................................................" : (question.prompt_text ?? "Chưa có nội dung")}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
