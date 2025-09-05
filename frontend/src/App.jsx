// frontend/src/App.jsx
import React, { useState } from "react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://framepickr-backend.onrender.com";

function App() {
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const onFiles = (e) => setFiles(Array.from(e.target.files || []));

  const submit = async () => {
    if (!files.length) return alert("Choose images first");
    setLoading(true);
    setResults(null);

    const form = new FormData();
    files.forEach((f) => form.append("files", f, f.name));

    try {
      const res = await axios.post(`${API_BASE}/score_and_save?top_n=5`, form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 60_000,
      });
      setResults(res.data);
      // scroll to results
      setTimeout(() => window.scrollTo({ top: 0, behavior: "smooth" }), 200);
    } catch (err) {
      console.error("Upload error:", err);
      // helpful error message for devs & users
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        err?.message ||
        "Network or server error";
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
            border: "1px solid #333",
            color: "#fff",
            cursor: loading ? "default" : "pointer",
          }}
        >
          {loading ? "Processing..." : "Upload & Score"}
        </button>
      </div>

      <div style={{ marginTop: 20 }}>
        <h2>Top Results</h2>

        {!results && <div style={{ color: "#ccc" }}>No scored images found.</div>}

        {results && (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 14 }}>
              {results.top.length === 0 && <div style={{ color: "#ccc" }}>No scored images returned.</div>}
              {results.top.map((t) => (
                <div
                  key={(t.saved_as || t.filename) + t.score}
                  style={{ border: "1px solid #444", padding: 12, display: "flex", gap: 12, alignItems: "center" }}
                >
                  <div style={{ width: 160, minHeight: 100 }}>
                    {t.url ? (
                      <img
                        src={`${API_BASE}${t.url}`}
                        alt={t.filename}
                        style={{ width: 160, height: 120, objectFit: "cover", borderRadius: 4 }}
                      />
                    ) : (
                      <div style={{ width: 160, height: 120, background: "#222", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        No preview
                      </div>
                    )}
                  </div>

                  <div style={{ flex: 1, textAlign: "left" }}>
                    <div style={{ fontWeight: 700 }}>{t.filename}</div>
                    <div style={{ marginTop: 6, fontSize: 14 }}>
                      <strong>Score:</strong> {t.score ?? "—"}
                    </div>
                    <div style={{ fontSize: 13, color: "#bbb", marginTop: 6 }}>
                      Sharpness: {t.sharpness ?? "—"} | Brightness: {t.brightness ?? "—"} | Faces: {t.faces ?? 0}
                    </div>

                    {t.url && (
                      <div style={{ marginTop: 10 }}>
                        <a href={`${API_BASE}${t.url}`} target="_blank" rel="noreferrer" style={{ color: "#7fcfff" }}>
                          Open
                        </a>{" "}
                        |{" "}
                        <a href={`${API_BASE}${t.url}`} download style={{ color: "#7fcfff" }}>
                          Download
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Optional: small "All results" summary (hidden by default) */}
            {/* <details style={{marginTop: 16}}>
              <summary style={{cursor: 'pointer'}}>View raw results</summary>
              <pre style={{background: "#111", padding: 10, color: "#ddd", overflowX: "auto"}}>{JSON.stringify(results.all, null, 2)}</pre>
            </details> */}
          </>
        )}
      </div>
    </div>
  );
}

export default App;
