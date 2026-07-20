import { useEffect, useState } from "react";
import {
  deleteKnowledgeDocument,
  listKnowledgeDocuments,
  updateKnowledgeDocument,
  uploadKnowledgeDocument,
} from "../api/admin";
import { listGrades, listUnitsForGrade } from "../api/catalog";
import { ApiError } from "../api/client";
import { Modal } from "../components/Modal";
import type { KnowledgeDocumentOut } from "../types/admin";
import type { GradeOut, UnitOut } from "../types/catalog";

export function AdminKnowledgePage() {
  const [documents, setDocuments] = useState<KnowledgeDocumentOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const [showUpload, setShowUpload] = useState(false);
  const [grades, setGrades] = useState<GradeOut[]>([]);
  const [units, setUnits] = useState<UnitOut[]>([]);
  const [gradeId, setGradeId] = useState("");
  const [unitId, setUnitId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  function reload() {
    listKnowledgeDocuments()
      .then(setDocuments)
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Không tải được danh sách tài liệu"));
  }

  useEffect(reload, []);

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
            {documents.map((document) => (
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
    </div>
  );
}
