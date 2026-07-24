import { useEffect, useState } from "react";
import { getAIConfig, testAIConfig, updateAIConfig } from "../api/admin";
import { ApiError } from "../api/client";
import type { AIProviderConfigOut } from "../types/admin";

const CHAT_MODELS = ["gpt-4o-mini", "gpt-4o"];
const EMBEDDING_MODELS = ["text-embedding-3-small", "text-embedding-3-large"];

export function AdminAIConfigPage() {
  const [config, setConfig] = useState<AIProviderConfigOut | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  const [model, setModel] = useState(CHAT_MODELS[0]!);
  const [embeddingModel, setEmbeddingModel] = useState(EMBEDDING_MODELS[0]!);
  const [temperature, setTemperature] = useState(0.7);
  const [threshold, setThreshold] = useState(0.9);
  const [apiKey, setApiKey] = useState("");

  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);

  function reload() {
    getAIConfig()
      .then((c) => {
        setConfig(c);
        if (c) {
          setModel(c.model);
          setEmbeddingModel(c.embedding_model);
          setTemperature(c.temperature);
          setThreshold(c.duplicate_similarity_threshold);
        }
      })
      .catch((err: unknown) => setError(err instanceof ApiError ? err.message : "Không tải được cấu hình AI"));
  }

  useEffect(reload, []);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await updateAIConfig({
        model,
        embedding_model: embeddingModel,
        temperature,
        duplicate_similarity_threshold: threshold,
        api_key: apiKey || null,
      });
      setApiKey("");
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Không lưu được cấu hình");
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    if (!apiKey) return;
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testAIConfig(apiKey);
      setTestResult(result);
    } catch (err) {
      setTestResult({ ok: false, message: err instanceof ApiError ? err.message : "Không kiểm tra được kết nối" });
    } finally {
      setTesting(false);
    }
  }

  if (config === undefined && !error) {
    return <p style={{ color: "var(--muted)" }}>Đang tải...</p>;
  }

  return (
    <div style={{ display: "grid", gap: 18, maxWidth: 480 }}>
      <div>
        <h2 style={{ margin: "0 0 4px" }}>Cấu hình AI</h2>
        <p style={{ color: "var(--muted)", fontSize: 13, margin: 0 }}>
          Provider OpenAI dùng để sinh câu hỏi thật. API key được mã hóa khi lưu, không bao giờ hiển thị đầy đủ.
        </p>
      </div>

      {error && <p style={{ color: "var(--danger)" }}>{error}</p>}

      {config === null && (
        <p style={{ color: "var(--muted)" }}>Chưa cấu hình — nhập API key bên dưới để bắt đầu dùng OpenAI thật.</p>
      )}
      {config && (
        <p style={{ color: "var(--muted)", fontSize: 13 }}>
          Đang dùng: <strong>{config.model}</strong> · Key: <code>{config.api_key_masked}</code> · Cập nhật lần cuối{" "}
          {new Date(config.updated_at).toLocaleString("vi-VN")}
        </p>
      )}

      <div style={{ display: "grid", gap: 14 }}>
        <label>
          Model sinh câu hỏi
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            {CHAT_MODELS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>

        <label>
          Embedding model (RAG)
          <select value={embeddingModel} onChange={(e) => setEmbeddingModel(e.target.value)}>
            {EMBEDDING_MODELS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>

        <label>
          Temperature ({temperature.toFixed(1)})
          <input
            type="range"
            min={0}
            max={2}
            step={0.1}
            value={temperature}
            onChange={(e) => setTemperature(Number(e.target.value))}
          />
        </label>

        <label>
          Ngưỡng cảnh báo trùng câu ({(threshold * 100).toFixed(0)}%)
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
          />
        </label>

        <label>
          API key {config && "(để trống nếu giữ nguyên key hiện tại)"}
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={config ? config.api_key_masked : "sk-..."}
          />
        </label>

        {testResult && (
          <p style={{ color: testResult.ok ? "var(--success)" : "var(--danger)", fontSize: 13 }}>
            {testResult.message}
          </p>
        )}

        <div style={{ display: "flex", gap: 10 }}>
          <button
            type="button"
            className="button secondary"
            onClick={handleTest}
            disabled={testing || !apiKey}
          >
            {testing ? "Đang kiểm tra..." : "Kiểm tra kết nối"}
          </button>
          <button
            type="button"
            className="button primary"
            onClick={handleSave}
            disabled={saving || (!config && !apiKey)}
          >
            {saving ? "Đang lưu..." : "Lưu cấu hình"}
          </button>
        </div>
      </div>
    </div>
  );
}
