import { useEffect, useState } from "react";
import {
  deleteKnowledgeDocument,
  listKnowledgeDocumentChunks,
  listKnowledgeDocuments,
  updateKnowledgeDocument,
  uploadKnowledgeDocument,
} from "../api/admin";
import { listGrades, listGrammarTopics, listUnitsForGrade } from "../api/catalog";
import { ApiError } from "../api/client";
import { Modal } from "../components/Modal";
import type { KnowledgeChunkAdminOut, KnowledgeChunkType, KnowledgeDocumentOut } from "../types/admin";
import type { GradeOut, GrammarTopicOut, UnitOut } from "../types/catalog";

type SourceKind = "unit" | "grammar";
type SourceFilter = "" | SourceKind;

const CHUNK_TYPE_LABEL: Record<KnowledgeChunkType, string> = {
  vocabulary: "Từ vựng",
  word_form: "Word form",
  phrase: "Cụm từ/giới từ",
  grammar: "Ngữ pháp",
  other: "Khác",
};

function chunkTableGrid(chunk: KnowledgeChunkAdminOut): string[][] | null {
  const table = chunk.structured?.table;
  if (!Array.isArray(table) || !table.every((row) => Array.isArray(row))) return null;
  return table as string[][];
}

type SortKey = "source" | "file_name" | "chunk_count" | "status";

const SORT_COLUMNS: { key: SortKey; label: string }[] = [
  { key: "source", label: "Nguồn" },
  { key: "file_name", label: "Tên file" },
  { key: "chunk_count", label: "Số đoạn" },
  { key: "status", label: "Trạng thái" },
];

function compareDocuments(a: KnowledgeDocumentOut, b: KnowledgeDocumentOut, key: SortKey): number {
  switch (key) {
    case "source": {
      if (a.unit && b.unit) return a.unit.grade_number - b.unit.grade_number || a.unit.order_no - b.unit.order_no;
      if (a.unit && !b.unit) return -1;
      if (!a.unit && b.unit) return 1;
      return (
        (a.grammar_point?.topic_name ?? "").localeCompare(b.grammar_point?.topic_name ?? "") ||
        (a.grammar_point?.name ?? "").localeCompare(b.grammar_point?.name ?? "")
      );
    }
    case "file_name":
      return a.file_name.localeCompare(b.file_name);
    case "chunk_count":
      return a.chunk_count - b.chunk_count;
    case "status":
      return Number(a.is_published) - Number(b.is_published);
  }
}

export function AdminKnowledgePage() {
  const [documents, setDocuments] = useState<KnowledgeDocumentOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [filterGradeNumber, setFilterGradeNumber] = useState("");
  const [filterSourceKind, setFilterSourceKind] = useState<SourceFilter>("");
  const [sortKey, setSortKey] = useState<SortKey>("source");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  const [showUpload, setShowUpload] = useState(false);
  const [sourceKind, setSourceKind] = useState<SourceKind>("unit");
  const [grades, setGrades] = useState<GradeOut[]>([]);
  const [units, setUnits] = useState<UnitOut[]>([]);
  const [gradeId, setGradeId] = useState("");
  const [unitId, setUnitId] = useState("");
  const [grammarTopics, setGrammarTopics] = useState<GrammarTopicOut[]>([]);
  const [grammarTopicId, setGrammarTopicId] = useState("");
  const [grammarPointId, setGrammarPointId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const [viewingDocument, setViewingDocument] = useState<KnowledgeDocumentOut | null>(null);
  const [viewChunks, setViewChunks] = useState<KnowledgeChunkAdminOut[] | null>(null);
  const [viewError, setViewError] = useState<string | null>(null);

  function reload() {
    listKnowledgeDocuments()
      .then(setDocuments)
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Không tải được danh sách tài liệu"));
  }

  useEffect(reload, []);

  const availableGradeNumbers = Array.from(
    new Set((documents ?? []).flatMap((d) => (d.unit ? [d.unit.grade_number] : []))),
  ).sort((a, b) => a - b);
  const sortedDocuments = (documents ?? [])
    .filter((d) => {
      if (filterSourceKind === "unit") return d.unit !== null;
      if (filterSourceKind === "grammar") return d.grammar_point !== null;
      return true;
    })
    .filter((d) => !filterGradeNumber || d.unit?.grade_number === Number(filterGradeNumber))
    .sort((a, b) => compareDocuments(a, b, sortKey) * (sortDirection === "asc" ? 1 : -1));

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDirection("asc");
    }
  }

  useEffect(() => {
    listGrades().then((g) => {
      setGrades(g);
      if (g.length > 0) setGradeId(g[0]!.id);
    });
  }, []);

  useEffect(() => {
    if (!gradeId) {
      setUnits([]);
      return;
    }
    listUnitsForGrade(gradeId).then((u) => {
      setUnits(u);
      setUnitId(u.length > 0 ? u[0]!.id : "");
    });
  }, [gradeId]);

  useEffect(() => {
    listGrammarTopics().then((topics) => {
      setGrammarTopics(topics);
      if (topics.length > 0) setGrammarTopicId(topics[0]!.id);
    });
  }, []);

  useEffect(() => {
    const topic = grammarTopics.find((t) => t.id === grammarTopicId);
    const firstPoint = topic?.groups.flatMap((g) => g.points)[0];
    setGrammarPointId(firstPoint?.id ?? "");
  }, [grammarTopicId, grammarTopics]);

  function openUpload() {
    setFile(null);
    setError(null);
    setSourceKind("unit");
    setShowUpload(true);
  }

  async function handleUpload() {
    if (!file) return;
    if (sourceKind === "unit" && !unitId) return;
    if (sourceKind === "grammar" && !grammarPointId) return;
    setUploading(true);
    setError(null);
    try {
      await uploadKnowledgeDocument(sourceKind === "unit" ? { unitId } : { grammarPointId }, file);
      setShowUpload(false);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không nhập được tài liệu");
    } finally {
      setUploading(false);
    }
  }

  async function handleTogglePublish(document: KnowledgeDocumentOut) {
    setTogglingId(document.id);
    setError(null);
    try {
      await updateKnowledgeDocument(document.id, !document.is_published);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không cập nhật được trạng thái");
    } finally {
      setTogglingId(null);
    }
  }

  async function handleView(document: KnowledgeDocumentOut) {
    setViewingDocument(document);
    setViewChunks(null);
    setViewError(null);
    try {
      const chunks = await listKnowledgeDocumentChunks(document.id);
      setViewChunks(chunks);
    } catch (err) {
      setViewError(err instanceof ApiError ? err.message : "Không tải được nội dung tài liệu");
    }
  }

  async function handleDelete(document: KnowledgeDocumentOut) {
    if (!window.confirm(`Xóa vĩnh viễn tài liệu "${document.file_name}"? Không thể hoàn tác.`)) return;
    setDeletingId(document.id);
    setError(null);
    try {
      await deleteKnowledgeDocument(document.id);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không xóa được tài liệu");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div style={{ display: "grid", gap: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>Kho kiến thức</h2>
        <button type="button" className="button primary" onClick={openUpload}>
          + Nhập tài liệu
        </button>
      </div>

      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
      {!documents && !error && <p style={{ color: "var(--muted)" }}>Đang tải...</p>}
      {documents && documents.length === 0 && <p style={{ color: "var(--muted)" }}>Chưa có tài liệu nào.</p>}

      {documents && documents.length > 0 && (
        <>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <label style={{ maxWidth: 220 }}>
              Lọc theo loại nguồn
              <select value={filterSourceKind} onChange={(e) => setFilterSourceKind(e.target.value as SourceFilter)}>
                <option value="">Tất cả nguồn</option>
                <option value="unit">Global Success (theo Unit)</option>
                <option value="grammar">Kiến thức chung (ngữ pháp)</option>
              </select>
            </label>
            <label style={{ maxWidth: 220 }}>
              Lọc theo khối lớp
              <select value={filterGradeNumber} onChange={(e) => setFilterGradeNumber(e.target.value)}>
                <option value="">Tất cả khối</option>
                {availableGradeNumbers.map((number) => (
                  <option key={number} value={number}>
                    Lớp {number}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <table className="data-table">
          <thead>
            <tr>
              {SORT_COLUMNS.map((column) => (
                <th key={column.key}>
                  <button
                    type="button"
                    onClick={() => handleSort(column.key)}
                    style={{
                      all: "unset",
                      cursor: "pointer",
                      fontWeight: "inherit",
                      fontSize: "inherit",
                      color: "inherit",
                    }}
                  >
                    {column.label}
                    {sortKey === column.key ? (sortDirection === "asc" ? " ▲" : " ▼") : ""}
                  </button>
                </th>
              ))}
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sortedDocuments.map((document) => (
              <tr key={document.id}>
                <td>
                  {document.unit ? (
                    <>
                      Lớp {document.unit.grade_number} · Unit {document.unit.order_no} — {document.unit.title}
                    </>
                  ) : (
                    <>Kiến thức chung · {document.grammar_point?.name}</>
                  )}
                </td>
                <td>{document.file_name}</td>
                <td>{document.chunk_count}</td>
                <td>
                  <span className={`status-pill ${document.is_published ? "active" : "locked"}`}>
                    {document.is_published ? "Đã xuất bản" : "Đã ẩn"}
                  </span>
                </td>
                <td className="actions">
                  <button type="button" className="button secondary compact" onClick={() => handleView(document)}>
                    Xem
                  </button>
                  <button
                    type="button"
                    className="button secondary compact"
                    onClick={() => handleTogglePublish(document)}
                    disabled={togglingId === document.id}
                  >
                    {document.is_published ? "Ẩn" : "Xuất bản"}
                  </button>
                  <button
                    type="button"
                    className="button secondary compact"
                    onClick={() => handleDelete(document)}
                    disabled={deletingId === document.id}
                  >
                    Xóa
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
          </table>
        </>
      )}

      <Modal open={showUpload} onClose={() => setShowUpload(false)} title="Nhập tài liệu">
        <div className="app-modal-body">
          <label>
            Loại nguồn
            <select value={sourceKind} onChange={(e) => setSourceKind(e.target.value as SourceKind)}>
              <option value="unit">Global Success (theo Unit)</option>
              <option value="grammar">Kiến thức chung (ngữ pháp)</option>
            </select>
          </label>

          {sourceKind === "unit" ? (
            <>
              <label>
                Khối lớp
                <select value={gradeId} onChange={(e) => setGradeId(e.target.value)}>
                  {grades.map((g) => (
                    <option key={g.id} value={g.id}>
                      Lớp {g.number}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Unit
                <select value={unitId} onChange={(e) => setUnitId(e.target.value)}>
                  {units.map((u) => (
                    <option key={u.id} value={u.id}>
                      Unit {u.order_no} — {u.title}
                    </option>
                  ))}
                </select>
              </label>
            </>
          ) : (
            <>
              <label>
                Chuyên đề
                <select value={grammarTopicId} onChange={(e) => setGrammarTopicId(e.target.value)}>
                  {grammarTopics.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Cấu trúc / Thì
                <select value={grammarPointId} onChange={(e) => setGrammarPointId(e.target.value)}>
                  {grammarTopics
                    .find((t) => t.id === grammarTopicId)
                    ?.groups.map((g) => (
                      <optgroup key={g.id} label={g.name}>
                        {g.points.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.name}
                          </option>
                        ))}
                      </optgroup>
                    ))}
                </select>
              </label>
            </>
          )}

          <label>
            File tài liệu (.docx)
            <input
              type="file"
              accept=".docx"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
        </div>
        <div className="app-modal-footer">
          <button type="button" className="button secondary" onClick={() => setShowUpload(false)}>
            Hủy
          </button>
          <button
            type="button"
            className="button primary"
            onClick={handleUpload}
            disabled={uploading || !file || (sourceKind === "unit" ? !unitId : !grammarPointId)}
          >
            {uploading ? "Đang nhập..." : "Nhập tài liệu"}
          </button>
        </div>
      </Modal>

      <Modal
        open={viewingDocument !== null}
        onClose={() => setViewingDocument(null)}
        title={viewingDocument ? `Nội dung — ${viewingDocument.file_name}` : "Nội dung"}
        size="lg"
      >
        <div className="app-modal-body" style={{ maxHeight: "60vh", overflowY: "auto" }}>
          {viewError && <p style={{ color: "var(--danger)" }}>{viewError}</p>}
          {!viewChunks && !viewError && <p style={{ color: "var(--muted)" }}>Đang tải...</p>}
          {viewChunks && viewChunks.length === 0 && <p style={{ color: "var(--muted)" }}>Tài liệu chưa có đoạn nào.</p>}
          {viewChunks && viewChunks.length > 0 && (
            <div style={{ display: "grid", gap: 10 }}>
              {viewChunks.map((chunk) => {
                const grid = chunkTableGrid(chunk);
                return (
                  <div key={chunk.id} style={{ borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
                    <p style={{ margin: "0 0 4px", fontSize: 12, color: "var(--muted)" }}>
                      <span className="chip">{CHUNK_TYPE_LABEL[chunk.chunk_type]}</span>{" "}
                      {chunk.section_title && <span>{chunk.section_title}</span>}
                    </p>
                    {grid ? (
                      <table style={{ borderCollapse: "collapse", width: "100%" }}>
                        <tbody>
                          {grid.map((row, rowIndex) => (
                            <tr key={rowIndex}>
                              {row.map((cell, cellIndex) => (
                                <td
                                  key={cellIndex}
                                  style={{
                                    border: "1px solid var(--border)",
                                    padding: "4px 8px",
                                    verticalAlign: "top",
                                    whiteSpace: "pre-wrap",
                                  }}
                                >
                                  {cell}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{chunk.raw_text}</p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
        <div className="app-modal-footer">
          <button type="button" className="button secondary" onClick={() => setViewingDocument(null)}>
            Đóng
          </button>
        </div>
      </Modal>
    </div>
  );
}
