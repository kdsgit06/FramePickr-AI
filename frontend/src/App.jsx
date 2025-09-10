// frontend/src/App.jsx
import React, { useState } from "react";
import axios from "axios";
import "./index.css";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "https://framepickr-backend-1083279422825.us-central1.run.app";

/* small helpers (same as before) */
async function fileToImage(file) {
  return new Promise((res, rej) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => res(img);
      img.onerror = rej;
      img.src = reader.result;
    };
    reader.onerror = rej;
    reader.readAsDataURL(file);
  });
}
async function resizeAndCompress(file, { maxWidth = 1600, maxKB = 700 } = {}) {
  try {
    const img = await fileToImage(file);
    const canvas = document.createElement("canvas");
    let width = img.width;
    let height = img.height;
    if (width > maxWidth) {
      height = Math.round((maxWidth * height) / width);
      width = maxWidth;
    }
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(img, 0, 0, width, height);
    let quality = 0.92;
    let blob = await new Promise((r) => canvas.toBlob(r, "image/jpeg", quality));
    const maxBytes = maxKB * 1024;
    while (blob && blob.size > maxBytes && quality > 0.3) {
      quality -= 0.12;
      blob = await new Promise((r) => canvas.toBlob(r, "image/jpeg", quality));
    }
    return blob || file;
  } catch (e) {
    return file;
  }
}

/* Small presentational components */
function CTA() {
  return (
    <div className="cta-strip" role="note" aria-live="polite">
      <div className="ctastep"><strong>1</strong> Choose images (multiple)</div>
      <div className="ctastep"><strong>2</strong> Upload & Score — we score for sharpness, face & brightness</div>
      <div className="ctastep"><strong>3</strong> Download originals of top picks</div>
    </div>
  );
}

function RankBadge({ n }) {
  return <div className="rank-badge" aria-hidden="true">#{n}</div>;
}

function Card({ item, rank, onOpen }) {
  return (
    <article className="card" aria-labelledby={`card-${rank}-title`}>
      <RankBadge n={rank} />
      <div className="thumb-wrap" onClick={() => item._absolute_url && onOpen(item)} role="button" tabIndex={0}>
        {item._absolute_url ? (
          <img className="thumb" src={item._absolute_url} alt={item.filename} />
        ) : (
          <div className="thumb-empty">No preview</div>
        )}
      </div>

      <div className="meta">
        <div className="meta-left">
          <div id={`card-${rank}-title`} className="filename" title={item.filename}>{item.filename}</div>
          <div className="meta-sub">Score: {typeof item.score !== "undefined" ? item.score : "—"}</div>
          <div className="explain">Higher = better. We compress to score but save original for download.</div>
        </div>

        <div className="meta-right">
          {item._absolute_url && (
            <>
              <a className="btn" href={item._absolute_url} target="_blank" rel="noreferrer">Open</a>
              <a className="btn primary" href={item._absolute_url} download>Download</a>
            </>
          )}
        </div>
      </div>
    </article>
  );
}

/* Main App */
export default function App() {
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [modal, setModal] = useState(null);

  const onFiles = (e) => {
    setFiles(Array.from(e.target.files || []));
    setResults(null);
  };

  const submit = async () => {
    if (!files.length) return alert("Choose images first");
    setLoading(true);
    try {
      const processed = await Promise.all(files.map(async (f) => {
        if (f.size / 1024 <= 800) return f;
        const blob = await resizeAndCompress(f, { maxWidth: 1600, maxKB: 700 });
        if (blob instanceof Blob) return new File([blob], f.name.replace(/\.[^.]+$/, ".jpg"), { type: "image/jpeg" });
        return f;
      }));

      const form = new FormData();
      processed.forEach((f) => form.append("files", f, f.name));
      const res = await axios.post(`${API_BASE.replace(/\/$/, "")}/score_and_save?top_n=8`, form, {
        headers: { "Content-Type": "multipart/form-data" }, timeout: 120000
      });

      if (res?.data) {
        const normalize = (item) => {
          if (!item) return item;
          const copy = { ...item };
          if (copy.url) copy._absolute_url = copy.url.startsWith("/") ? API_BASE.replace(/\/$/, "") + copy.url : copy.url;
          return copy;
        };
        const top = (res.data.top || []).map(normalize);
        const all = (res.data.all || []).map(normalize);
        setResults({ ...res.data, top, all });
        window.scrollTo({ top: 0, behavior: "smooth" });
      } else {
        alert("No data returned");
      }
    } catch (err) {
      console.error(err);
      alert("Upload error: " + (err?.response?.data?.detail || err?.message || err));
    } finally {
      setLoading(false);
    }
  };

  const openModal = (item) => setModal(item);
  const closeModal = () => setModal(null);

  return (
    <div className="page">
      <header className="header">
        <div className="brand">
          <div className="logo">Frame<span className="logo-accent">Pickr</span></div>
          <div className="tag">AI-assisted frame selection</div>
        </div>

        <div className="controls">
          <label className="file-label">
            <input type="file" accept="image/*" multiple onChange={onFiles} />
            <span className="file-btn">Choose files</span>
            <span className="file-count">{files.length ? `${files.length} selected` : ""}</span>
          </label>

          <button className="pill" onClick={submit} disabled={loading}>{loading ? "Processing…" : "Upload & Score"}</button>
        </div>
      </header>

      <CTA />

      <main>
        <section className="results">
          <h2 className="section-title">Top Results</h2>

          {!results && <div className="muted">No results yet — upload images to get ranked picks.</div>}

          {results?.top?.length > 0 && (
            <div className="grid" role="list">
              {results.top.map((t, idx) => (
                <Card key={t.filename + (t.saved_as || idx)} item={t} rank={idx + 1} onOpen={openModal} />
              ))}
            </div>
          )}
        </section>
      </main>

      {modal && (
        <div className="modal" onClick={closeModal} role="dialog" aria-modal="true">
          <div className="modal-inner" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={closeModal}>✕</button>
            <img className="modal-img" src={modal._absolute_url} alt={modal.filename} />
            <div className="modal-meta">
              <div className="modal-title">{modal.filename}</div>
              <div className="modal-sub">Score: {modal.score} · Sharpness: {modal.sharpness}</div>
              <div style={{ marginTop: 12 }}>
                <a className="btn" href={modal._absolute_url} target="_blank" rel="noreferrer">Open</a>
                <a className="btn primary" href={modal._absolute_url} download style={{ marginLeft: 8 }}>Download</a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
