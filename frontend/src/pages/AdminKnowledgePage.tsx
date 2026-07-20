import { useEffect, useState } from "react";
import {
  deleteKnowledgeDocument,
  listKnowledgeDocumentChunks,
  listKnowledgeDocuments,
  updateKnowledgeDocument,
  uploadKnowledgeDocument,
} from "../api/admin";
import { listGrades, listUnitsForGrade } from "../api/catalog";
import { ApiError } from "../api/client";
import { Modal } from "../components/Modal";
import type { KnowledgeChunkAdminOut, KnowledgeChunkType, KnowledgeDocumentOut } from "../types/admin";
import type { GradeOut, UnitOut } from "../types/catalog";

const CHUNK_TYPE_LABEL: Record<KnowledgeChunkType, string> = {
  vocabulary: "Từ vựng",
  word_form: "Word form",
  phrase: "Cụm từ/giới từ",
  grammar: "Ngữ pháp",
  other: "Khác",
};

export function AdminKnowledgePage() {
  const [documents, setDocuments] = useState<KnowledgeDocumentOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [filterGradeNumber, setFilterGradeNumber] = useState("");

  const [showUpload, setShowUpload] = useState(false);
  const [grades, setGrades] = useState<GradeOut[]>([]);
  const [units, setUnits] = useState<UnitOut[]>([]);
  const [gradeId, setGradeId] = useState("");
  const [unitId, setUnitId] = useState("");
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

  const availableGradeNumbers = Array.from(new Set((documents ?? []).map((d) => d.unit.grade_number))).sort(
    (a, b) => a - b,
  );
  const filteredDocuments = (documents ?? []).filter(
    (d) => !filterGradeNumber || d.unit.grade_number === Number(filterGradeNumber),
  );

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

  function openUpload() {
    setFile(null);
    setError(null);
    setShowUpload(true);
  }

  async function handleUpload() {
    if (!unitId || !file) return;
    setUploading(true);
    setError(null);
    try {
      await uploadKnowledgeDocument(unitId, file);
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

          <table className="data-table">
          <thead>
            <tr>
              <th>Khối / Unit</th>
              <th>Tên file</th>
              <th>Số đoạn</th>
              <th>Trạng thái</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filteredDocuments.map((document) => (
              <tr key={document.id}>
                <td>
                  Lớp {document.unit.grade_number} · Unit {document.unit.order_no} — {document.unit.title}
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
            disabled={uploading || !unitId || !file}
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
              {viewChunks.map((chunk) => (
                <div key={chunk.id} style={{ borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
                  <p style={{ margin: "0 0 4px", fontSize: 12, color: "var(--muted)" }}>
                    <span className="chip">{CHUNK_TYPE_LABEL[chunk.chunk_type]}</span>{" "}
                    {chunk.section_title && <span>{chunk.section_title}</span>}
                  </p>
                  <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{chunk.raw_text}</p>
                </div>
              ))}
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
