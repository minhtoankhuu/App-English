const STEP_LABELS = ["Nguồn kiến thức", "Cấu trúc đề", "Duyệt câu hỏi", "Xuất DOCX"];

interface StepsIndicatorProps {
  /** 1-indexed: bước nào đang active. */
  current: 1 | 2 | 3 | 4;
}

export function StepsIndicator({ current }: StepsIndicatorProps) {
  return (
    <ol className="steps" aria-label="Tiến trình tạo đề">
      {STEP_LABELS.map((label, index) => {
        const stepNumber = index + 1;
        const isCompleted = stepNumber < current;
        const isActive = stepNumber === current;
        return (
          <li key={label} className={`step${isCompleted ? " completed" : ""}${isActive ? " active" : ""}`}>
            <span className="step-dot">{isCompleted ? "✓" : stepNumber}</span>
            <span className="step-label">{label}</span>
          </li>
        );
      })}
    </ol>
  );
}
