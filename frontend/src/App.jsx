// frontend/src/App.jsx
import React, { useState } from "react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "https://framepickr-backend.onrender.com";

function App() {
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const onFiles = (e) => {
    setFiles(Array.from(e.target.files || []));
    setResults(null); // clear previous results when new files chosen
  };

  const submit = async () => {
    if (!files.length) return alert("Choose images first");
    setLoading(true);

    const form = new FormData();
    files.forEach((f) => form.append("files", f, f.name));

    try {
      const url = `${API_BASE.replace(/\/$/, "")}/score_and_save?top_n=5`;
      const res = await axios.post(url, form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120000,
      });

      // backend response shape: { count, top: [...], all: [...], saved: [...] }
      if (res?.data) {
        // normalize URLs in top[] so previews open correctly
        const normalize = (item) => {
          if (!item) return item;
          let copy = { ...item };
          if (copy.url) {
            // url could be "/uploads/xxx.jpg" or full "https://..."
            if (copy.url.startsWith("/")) {
              copy._absolute_url = API_BASE.replace(/\/$/, "") + copy.url;
            } else {
              copy._absolute_url = copy.url;
            }
          }
          return copy;
        };

        const top = (res.data.top || []).map(normalize);
        const all = (res.data.all || []).map(normalize);

        setResults({ ...res.data, top, all });
        // scroll to results
        window.scrollTo({ top: 0, behavior: "smooth" });
      } else {
        alert("No data returned from backend");
      }
    } catch (err) {
      console.error("Upload error:", err);
      const msg = err.response?.data?.detail || err.response?.data?.error || err.message;
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

      <div style={{ marginTop: 20 }}>
        <h2>Top Results</h2>
        {results && results.top && results.top.length === 0 && <div>No scored images returned.</div>}
        {!results && <div style={{ color: "#bbb" }}>No results yet — upload images to get ranked picks.</div>}

        {results?.top?.length > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 14 }}>
            {results.top.map((t, i) => (
              <div key={t.filename + (t.saved_as || i)} style={{ border: "1px solid #444", padding: 12, display: "flex", gap: 12 }}>
                <div style={{ width: 160, minHeight: 100 }}>
                  {t._absolute_url ? (
                    <img src={t._absolute_url} alt={t.filename} style={{ width: 160, height: "auto", objectFit: "cover" }} />
                  ) : (
                    <div style={{ width: 160, height: 120, background: "#222", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      No preview
                    </div>
                  )}
                </div>
                <div style={{ flex: 1, textAlign: "left" }}>
                  <div style={{ fontWeight: 700 }}>{t.filename}</div>
                  <div>Score: {typeof t.score !== "undefined" ? t.score : "—"}</div>
                  <div>
                    Sharpness: {t.sharpness ?? "—"} | Brightness: {t.brightness ?? "—"} | Faces: {t.faces ?? "—"}
                  </div>
                  {t._absolute_url && (
                    <div style={{ marginTop: 8 }}>
                      <a href={t._absolute_url} target="_blank" rel="noreferrer">Open</a>{" "}
                      | <a href={t._absolute_url} download>Download</a>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}

export default App;
