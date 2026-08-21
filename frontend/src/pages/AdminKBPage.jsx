import React, { useState, useEffect, useRef } from 'react';
import client from '../api/client';
import { Database, UploadCloud, FileText, Trash2, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

export const AdminKBPage = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  const fileInputRef = useRef(null);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const res = await client.get('/kb/documents');
      setDocuments(res.data);
    } catch (err) {
      console.error("Failed to fetch KB documents:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleUploadFile = async (file) => {
    if (!file) return;
    setMessage(null);
    setError(null);
    setUploading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await client.post('/kb/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setMessage(`Document "${res.data.filename}" uploaded successfully! Chunked into ${res.data.chunk_count} segments and TF-IDF RAG index rebuilt.`);
      fetchDocuments();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload document');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleUploadFile(e.target.files[0]);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleUploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleDeleteDoc = async (id, filename) => {
    if (!window.confirm(`Are you sure you want to delete document "${filename}"?`)) return;
    try {
      await client.delete(`/kb/documents/${id}`);
      setMessage(`Document "${filename}" removed. TF-IDF index refreshed.`);
      fetchDocuments();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete document');
    }
  };

  return (
    <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '32px 24px' }}>
      {/* Page Title */}
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 800, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Database size={26} color="#6366f1" /> Knowledge Base Management
        </h1>
        <p style={{ fontSize: '0.875rem', color: '#94a3b8', marginTop: '4px' }}>
          Upload support documents (.txt, .md, .pdf) to ground the Autonomous Copilot RAG pipeline
        </p>
      </div>

      {/* Notifications */}
      {message && (
        <div style={{
          padding: '12px 16px',
          background: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          borderRadius: '8px',
          color: '#34d399',
          fontSize: '0.875rem',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <CheckCircle2 size={18} />
          <span>{message}</span>
        </div>
      )}

      {error && (
        <div style={{
          padding: '12px 16px',
          background: 'rgba(244, 63, 94, 0.15)',
          border: '1px solid rgba(244, 63, 94, 0.3)',
          borderRadius: '8px',
          color: '#fca5a5',
          fontSize: '0.875rem',
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* DRAG & DROP UPLOAD ZONE */}
      <div
        className="glass-panel"
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          padding: '40px 24px',
          textAlign: 'center',
          cursor: 'pointer',
          border: dragActive ? '2px dashed #6366f1' : '2px dashed rgba(255, 255, 255, 0.15)',
          background: dragActive ? 'rgba(99, 102, 241, 0.1)' : 'rgba(17, 24, 39, 0.7)',
          marginBottom: '36px',
          transition: 'all 0.2s'
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.pdf"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '16px',
          background: 'rgba(99, 102, 241, 0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 16px auto',
          color: '#818cf8'
        }}>
          {uploading ? (
            <RefreshCw size={28} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
          ) : (
            <UploadCloud size={28} />
          )}
        </div>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', marginBottom: '6px' }}>
          {uploading ? 'Processing & Vectorizing Document...' : 'Click to Browse or Drag & Drop File'}
        </h3>
        <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
          Supports plain text (<strong>.txt</strong>), Markdown (<strong>.md</strong>), and PDF documents (<strong>.pdf</strong>)
        </p>
      </div>

      {/* DOCUMENT INVENTORY TABLE */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f8fafc', marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileText size={20} color="#06b6d4" /> Uploaded Document Inventory ({documents.length})
        </h3>

        {loading ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#64748b' }}>Loading documents...</div>
        ) : documents.length === 0 ? (
          <div style={{ padding: '32px', textAlign: 'center', color: '#64748b', fontSize: '0.9rem' }}>
            No documents uploaded yet. Upload a file above to enable RAG grounding.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8' }}>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Filename</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Type</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Indexed Chunks</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>Upload Date</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                  <td style={{ padding: '14px 16px', fontWeight: 600, color: '#f1f5f9', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FileText size={16} color="#818cf8" /> {doc.filename}
                  </td>
                  <td style={{ padding: '14px 16px' }}>
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      background: 'rgba(255,255,255,0.06)',
                      color: '#cbd5e1'
                    }}>
                      {doc.file_type}
                    </span>
                  </td>
                  <td style={{ padding: '14px 16px', color: '#38bdf8', fontWeight: 600 }}>
                    {doc.chunk_count} chunks
                  </td>
                  <td style={{ padding: '14px 16px', color: '#94a3b8' }}>
                    {new Date(doc.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                    <button
                      onClick={() => handleDeleteDoc(doc.id, doc.filename)}
                      className="btn-danger"
                      title="Delete document"
                    >
                      <Trash2 size={14} /> Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
