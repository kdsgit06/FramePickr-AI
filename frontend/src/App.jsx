// frontend/src/App.jsx
import React, { useState } from "react";
import axios from "axios";

const API_BASE = process.env.VITE_API_BASE_URL || "https://framepickr-backend.onrender.com";

function App() {
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const onFiles = (e) => setFiles(Array.from(e.target.files || []));

  const submit = async () => {
    if (!files.length) return alert("Choose images first");
    setLoading(true);
    const form = new FormData();
    files.forEach((f) => form.append("files", f, f.name));

    try {
      const res = await axios.post(`${API_BASE}/score_and_save?top_n=5`, form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120000,
      });
      setResults(res.data);
      // scroll to top so user sees results
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      console.error("Upload error:", err);
      const msg = err.response?.data?.detail || err.response?.data?.error || err.message || "Network Error";
      alert("Error: " + msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 980, margin: "2rem auto", fontFamily: "Inter, Arial, sans-serif", color: "#eee" }}>
      <h1 style={{ fontSize: 48, margin: 0 }}>FramePickr AI — Demo</h1>
      <p style={{ opacity: 0.8 }}>Upload multiple images; FramePickr will score and save the top picks.</p>

      <input type="file" multiple accept="image/*" onChange={onFiles} />
      <div style={{ marginTop: 12 }}>
        <button onClick={submit} disabled={loading} style={{ padding: "10px 18px", borderRadius: 8 }}>
          {loading ? "Processing..." : "Upload & Score"}
        </button>
      </div>

      {results && (
        <div style={{ marginTop: 20 }}>
          <h2>Top Results</h2>

          {/* Ranked list */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 14 }}>
            {results.top && results.top.length === 0 && <div>No scored images found.</div>}

            {results.top?.map((t, idx) => (
              <div
                key={(t.filename || "") + (t.saved_as || idx)}
                style={{
                  border: "1px solid #444",
                  padding: 12,
                  display: "flex",
                  gap: 12,
                  alignItems: "center",
                  background: "#1b1b1b",
                }}
              >
                <div style={{ width: 160, minHeight: 100 }}>
                  {t.url ? (
                    <img
                      src={`${API_BASE}${t.url}`}
                      alt={t.filename}
                      style={{ width: 160, height: "auto", objectFit: "cover", display: "block" }}
                      onError={(e) => {
                        e.currentTarget.style.opacity = 0.6;
                        e.currentTarget.alt = "Preview not available";
                      }}
                    />
                  ) : (
                    <div style={{ width: 160, height: 120, background: "#222", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      No preview
                    </div>
                  )}
                </div>

                <div style={{ flex: 1, textAlign: "left" }}>
                  <div style={{ fontWeight: 700 }}>{t.filename}</div>
                  <div style={{ marginTop: 6 }}>Score: <strong>{t.score ?? "-"}</strong></div>
                  <div style={{ marginTop: 4, opacity: 0.9 }}>
                    Sharpness: {t.sharpness ?? "-"} | Brightness: {t.brightness ?? "-"} | Faces: {t.faces ?? "-"}
                  </div>

                  {t.url && (
                    <div style={{ marginTop: 8 }}>
                      <a href={`${API_BASE}${t.url}`} target="_blank" rel="noreferrer" style={{ color: "#6ea0ff" }}>
                        Open
                      </a>{" "}
                      |{" "}
                      <a href={`${API_BASE}${t.url}`} download style={{ color: "#6ea0ff" }}>
                        Download
                      </a>
                    </div>
                  )}
                </div>

                <div style={{ width: 60, textAlign: "center", color: "#ccc" }}>
                  <div style={{ fontSize: 18, fontWeight: 700 }}>{idx + 1}</div>
                  <div style={{ fontSize: 12, opacity: 0.8 }}>rank</div>
                </div>
              </div>
            ))}
          </div>

          {/* Optional: show small debug summary (collapsed by default). Hidden now. */}
        </div>
      )}
    </div>
  );
}

export default App;
