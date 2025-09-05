// frontend/src/App.jsx
import React, { useState } from "react";
import axios from "axios";

const BACKEND = process.env.VITE_API_BASE_URL || "https://framepickr-backend.onrender.com";

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
      const res = await axios.post(`${BACKEND}/score_and_save?top_n=5`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResults(res.data);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      console.error(err);
      const msg = err.response?.data?.detail || err.response?.data || err.message;
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
        <button
          onClick={submit}
          disabled={loading}
          style={{
            padding: "10px 18px",
            borderRadius: 8,
            background: "#111",
            color: "#fff",
            border: "1px solid #333",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Processing..." : "Upload & Score"}
        </button>
      </div>

      {results && (
        <div style={{ marginTop: 20 }}>
          <h2>Top Results</h2>

          <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 14 }}>
            {results.top.map((t, idx) => (
              <div
                key={t.filename + (t.saved_as || "")}
                style={{
                  border: "1px solid #444",
                  padding: 12,
                  display: "flex",
                  gap: 12,
                  alignItems: "center",
                  background: "#0f0f0f",
                  borderRadius: 6,
                }}
              >
                <div style={{ width: 160, minHeight: 100 }}>
                  {t.url ? (
                    <img
                      src={`${BACKEND}${t.url}`}
                      alt={t.filename}
                      style={{ width: 160, height: 100, objectFit: "cover", borderRadius: 4 }}
                    />
                  ) : (
                    <div style={{ width: 160, height: 100, background: "#222", display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 4 }}>
                      No preview
                    </div>
                  )}
                </div>

                <div style={{ flex: 1, textAlign: "left" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <div style={{ fontWeight: 700, fontSize: 16 }}>
                      #{idx + 1} — {t.filename}
                    </div>
                    <div style={{ fontWeight: 700, color: "#9ad" }}>{t.score != null ? Number(t.score).toFixed(2) : "-"}</div>
                  </div>

                  <div style={{ marginTop: 6, color: "#bbb", fontSize: 14 }}>
                    <span>Sharpness: {t.sharpness != null ? Number(t.sharpness).toFixed(2) : "-"}</span>
                    <span style={{ marginLeft: 12 }}>Brightness: {t.brightness != null ? Number(t.brightness).toFixed(2) : "-"}</span>
                    <span style={{ marginLeft: 12 }}>Faces: {t.faces ?? 0}</span>
                  </div>

                  {t.url && (
                    <div style={{ marginTop: 8 }}>
                      <a href={`${BACKEND}${t.url}`} target="_blank" rel="noreferrer" style={{ color: "#79f" }}>
                        Open
                      </a>{" "}
                      |{" "}
                      <a href={`${BACKEND}${t.url}`} download style={{ color: "#79f" }}>
                        Download
                      </a>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* If you want debugging later: toggle this manually during development */}
          {/* <details style={{ marginTop: 18 }}>
            <summary style={{ cursor: "pointer" }}>Show raw response (debug)</summary>
            <pre style={{ background: "#111", padding: 10, color: "#ddd", overflowX: "auto" }}>{JSON.stringify(results, null, 2)}</pre>
          </details> */}
        </div>
      )}
    </div>
  );
}

export default App;
