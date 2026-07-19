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

const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"];

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
  const [dropTargetId, setDropTargetId] = useState<string | null>(null);

  function requestReorder(sourceId: string, targetId: string) {
    if (saving || sourceId === targetId) return;
    const reordered = moveBlock(blocks, sourceId, targetId);
    if (reordered === blocks) return;
    onReorder(reordered.map((block) => block.id));
  }

  function handleDragStart(event: DragEvent<HTMLButtonElement>, blockId: string) {
    if (saving) return;
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", blockId);
    }
    setDropTargetId(null);
    setDraggedId(blockId);
  }

  function handleDragOver(event: DragEvent<HTMLElement>, targetId: string) {
    if (saving) return;
    event.preventDefault();
    setDropTargetId(draggedId && draggedId !== targetId ? targetId : null);
  }

  function handleDrop(event: DragEvent<HTMLElement>, targetId: string) {
    event.preventDefault();
    if (draggedId) requestReorder(draggedId, targetId);
    setDropTargetId(null);
    setDraggedId(null);
  }

  return (
    <div className="block-list">
      {blocks.map((block, index) => (
        <article
          key={block.id}
          data-testid={`block-${block.id}`}
          className={`exam-block${draggedId === block.id ? " dragging" : ""}`}
          onDragOver={(event) => handleDragOver(event, block.id)}
          onDrop={(event) => handleDrop(event, block.id)}
          style={dropTargetId === block.id ? { border: "2px solid var(--primary)" } : undefined}
        >
          <button
            type="button"
            aria-label={`Kéo để sắp xếp ${block.title}`}
            className="drag"
            disabled={saving}
            draggable={!saving}
            onDragStart={(event) => handleDragStart(event, block.id)}
            onDragEnd={() => {
              setDropTargetId(null);
              setDraggedId(null);
            }}
            style={{ cursor: saving ? "not-allowed" : draggedId === block.id ? "grabbing" : "grab" }}
          >
            ⠿
          </button>

          <span className={`block-badge badge-${block.exercise_type.code}`} aria-hidden="true">
            {ROMAN[index] ?? index + 1}
          </span>

          <div className="block-body">
            <h3>{block.title}</h3>
            <p className="chips">
              <span className="chip">{block.exercise_type.name}</span>
              <span className="chip">{block.question_count} câu</span>
              <span className="chip">{DIFFICULTY_LABEL[block.difficulty]}</span>
              <span className="chip score">{block.points} điểm</span>
            </p>
          </div>

          <div className="item-actions">
            <input
              type="number"
              min={1}
              max={50}
              defaultValue={block.question_count}
              disabled={saving}
              aria-label={`Số câu ${block.title}`}
              className="field-input"
              onBlur={(event) => onUpdateField(block, "question_count", Number(event.target.value))}
            />
            <input
              type="number"
              min={0}
              max={10}
              step={0.5}
              defaultValue={block.points}
              disabled={saving}
              aria-label={`Điểm ${block.title}`}
              className="field-input"
              onBlur={(event) => onUpdateField(block, "points", Number(event.target.value))}
            />
            <button
              type="button"
              aria-label={`Lên ${block.title}`}
              disabled={saving || index === 0}
              onClick={() => requestReorder(block.id, blocks[index - 1]!.id)}
            >
              ↑
            </button>
            <button
              type="button"
              aria-label={`Xuống ${block.title}`}
              disabled={saving || index === blocks.length - 1}
              onClick={() => requestReorder(blocks[index + 1]!.id, block.id)}
            >
              ↓
            </button>
            <button type="button" aria-label={`Xóa ${block.title}`} disabled={saving} onClick={() => onDelete(block.id)}>
              ✕
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}
