import { useState } from "react";
import type { DragEvent } from "react";
import type { BlockOut, Difficulty } from "../types/exam";
import { moveBlock } from "./blockOrder";

const DIFFICULTY_LABEL: Record<Difficulty, string> = {
  nhan_biet: "Nhận biết",
  thong_hieu: "Thông hiểu",
  van_dung: "Vận dụng",
  hon_hop: "Hỗn hợp",
};

type EditableField = "question_count" | "points";

interface SortableBlockListProps {
  blocks: BlockOut[];
  saving: boolean;
  onReorder: (blockIds: string[]) => void;
  onDelete: (blockId: string) => void;
  onUpdateField: (block: BlockOut, field: EditableField, value: number) => void;
}

export function SortableBlockList({
  blocks,
  saving,
  onReorder,
  onDelete,
  onUpdateField,
}: SortableBlockListProps) {
  const [draggedId, setDraggedId] = useState<string | null>(null);

  function requestReorder(sourceId: string, targetId: string) {
    if (saving || sourceId === targetId) return;
    const reordered = moveBlock(blocks, sourceId, targetId);
    if (reordered === blocks) return;
    onReorder(reordered.map((block) => block.id));
  }

  function requestSwap(index: number, direction: -1 | 1) {
    if (saving) return;
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= blocks.length) return;

    const reordered = [...blocks];
    [reordered[index], reordered[targetIndex]] = [reordered[targetIndex]!, reordered[index]!];
    onReorder(reordered.map((block) => block.id));
  }

  function handleDragStart(event: DragEvent<HTMLButtonElement>, blockId: string) {
    if (saving) return;
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", blockId);
    }
    setDraggedId(blockId);
  }

  function handleDragOver(event: DragEvent<HTMLElement>) {
    if (!saving) event.preventDefault();
  }

  function handleDrop(event: DragEvent<HTMLElement>, targetId: string) {
    event.preventDefault();
    if (draggedId) requestReorder(draggedId, targetId);
    setDraggedId(null);
  }

  return (
    <div style={{ display: "grid", gap: 8 }}>
      {blocks.map((block, index) => (
        <article
          key={block.id}
          data-testid={`block-${block.id}`}
          onDragOver={handleDragOver}
          onDrop={(event) => handleDrop(event, block.id)}
          style={{
            border: "1px solid var(--border)",
            borderRadius: 10,
            padding: 12,
            opacity: draggedId === block.id ? 0.6 : 1,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
            <div>
              <strong>
                {index + 1}. {block.title}
              </strong>
              <p style={{ margin: "3px 0 0", fontSize: 12, color: "var(--muted)" }}>
                {block.exercise_type.name} · {DIFFICULTY_LABEL[block.difficulty]}
              </p>
            </div>
            <div style={{ display: "flex", gap: 4 }}>
              <button
                aria-label={`Kéo để sắp xếp ${block.title}`}
                disabled={saving}
                draggable={!saving}
                onDragStart={(event) => handleDragStart(event, block.id)}
                onDragEnd={() => setDraggedId(null)}
                style={iconButtonStyle}
              >
                ⠿
              </button>
              <button
                aria-label={`Lên ${block.title}`}
                disabled={saving || index === 0}
                onClick={() => requestSwap(index, -1)}
                style={iconButtonStyle}
              >
                ↑
              </button>
              <button
                aria-label={`Xuống ${block.title}`}
                disabled={saving || index === blocks.length - 1}
                onClick={() => requestSwap(index, 1)}
                style={iconButtonStyle}
              >
                ↓
              </button>
              <button
                aria-label={`Xóa ${block.title}`}
                disabled={saving}
                onClick={() => onDelete(block.id)}
                style={iconButtonStyle}
              >
                ✕
              </button>
            </div>
          </div>
          <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
            <label style={{ fontSize: 12 }}>
              Số câu {block.title}{" "}
              <input
                type="number"
                min={1}
                max={50}
                defaultValue={block.question_count}
                disabled={saving}
                onBlur={(event) => onUpdateField(block, "question_count", Number(event.target.value))}
                style={numberInputStyle}
              />
            </label>
            <label style={{ fontSize: 12 }}>
              Điểm {block.title}{" "}
              <input
                type="number"
                min={0}
                max={10}
                step={0.5}
                defaultValue={block.points}
                disabled={saving}
                onBlur={(event) => onUpdateField(block, "points", Number(event.target.value))}
                style={numberInputStyle}
              />
            </label>
          </div>
        </article>
      ))}
    </div>
  );
}

const iconButtonStyle: React.CSSProperties = {
  width: 28,
  height: 28,
  border: "1px solid var(--border)",
  borderRadius: 6,
  background: "#fff",
};

const numberInputStyle: React.CSSProperties = {
  width: 60,
  marginLeft: 4,
};
