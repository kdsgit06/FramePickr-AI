import React, { useState } from "react";
import axios from "axios";

function App() {
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

  const onFiles = (e) => {
    setFiles(Array.from(e.target.files));
  };

  const submit = async () => {
    if (!files.length) return alert("Choose images first");
    setLoading(true);
    const form = new FormData();
    files.forEach((f) => form.append("files", f, f.name));

    try {
      const res = await axios.post(
  "https://framepickr-backend.onrender.com/score_and_save?top_n=5",
  form,
  { headers: { "Content-Type": "multipart/form-data" } }
);

      setResults(res.data);
    } catch (err) {
      console.error(err);
      alert("Error: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "2rem auto", fontFamily: "Arial, Helvetica, sans-serif" }}>
      <h1>FramePickr AI — Demo</h1>
      <p>Upload multiple images; FramePickr will score and save the top picks.</p>

      <input type="file" multiple accept="image/*" onChange={onFiles} />
      <div style={{ marginTop: 10 }}>
        <button onClick={submit} disabled={loading}>
          {loading ? "Processing..." : "Upload & Score"}
        </button>
      </div>

      {results && (
        <div style={{ marginTop: 20 }}>
          <h2>Top Results</h2>
          <div>
            {results.top.map((t) => (
              <div key={t.filename} style={{ border: "1px solid #ddd", padding: 10, marginBottom: 8, display: "flex", gap: 12 }}>
                <div>
                  {t.url ? (
                    <img src={`${API_BASE}${t.url}`} alt={t.filename} style={{ width: 160, height: "auto", objectFit: "cover" }} />
                  ) : (
                    <div style={{ width: 160, height: 120, background: "#eee", display: "flex", alignItems: "center", justifyContent: "center" }}>No preview</div>
                  )}
                </div>
                <div>
                  <div><strong>{t.filename}</strong></div>
                  <div>Score: {t.score}</div>
                  <div>Sharpness: {t.sharpness} | Brightness: {t.brightness} | Faces: {t.faces}</div>
                  {t.url && (
                    <div style={{ marginTop: 8 }}>
                      <a href={`${API_BASE}${t.url}`} target="_blank" rel="noreferrer">Open</a>{" "}
                      | <a href={`${API_BASE}${t.url}`} download>Download</a>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <h3>All</h3>
          <pre style={{ background: "#f9f9f9", padding: 10 }}>{JSON.stringify(results.all, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}

export default App;
