import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, AlertCircle, BarChart3, Brain, MessageCircle } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { uploadDataset, getDashboard } from '../services/api';
import logoImg from '../assets/logo.png';

export default function UploadPage() {
  const { setDatasetId, setDatasetInfo, setDashboard, setInsights,
          setCurrentPage, setLoading } = useApp();
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [stage, setStage] = useState('');

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError('Please upload a CSV file.');
      return;
    }

    setError(null);
    setUploading(true);
    setProgress(0);
    setStage('Uploading file...');

    const handleProgress = (e) => setProgress(Math.min(e.detail, 50));
    window.addEventListener('upload-progress', handleProgress);

    try {
      setStage('Uploading & processing...');
      setProgress(30);
      const uploadResult = await uploadDataset(file);
      setProgress(60);

      setDatasetId(uploadResult.dataset_id);
      setDatasetInfo(uploadResult);

      setStage('Generating dashboard...');
      setProgress(75);
      const dashResult = await getDashboard(uploadResult.dataset_id);
      setProgress(90);

      setDashboard(dashResult.dashboard);
      setInsights(dashResult.insights || []);

      setStage('Done!');
      setProgress(100);

      setTimeout(() => {
        setCurrentPage('dashboard');
        setUploading(false);
      }, 800);

    } catch (err) {
      const message = err.response?.data?.detail || err.message || 'Upload failed. Please try again.';
      setError(message);
      setUploading(false);
    } finally {
      window.removeEventListener('upload-progress', handleProgress);
    }
  }, [setDatasetId, setDatasetInfo, setDashboard, setInsights, setCurrentPage, setLoading]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'] },
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <div className="upload-area animate-fade-in">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        style={{ width: '100%', maxWidth: 720, textAlign: 'center' }}
      >
        {/* Logo */}
        <img src={logoImg} alt="Analytix AI" className="upload-logo" />
        <p style={{ color: 'var(--text-secondary)', fontSize: 15, marginBottom: 36, maxWidth: 480, margin: '0 auto 36px' }}>
          Upload your dataset and let AI generate dashboards, insights, and analysis in seconds.
        </p>

        <AnimatePresence mode="wait">
          {!uploading ? (
            <motion.div
              key="dropzone"
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.97 }}
            >
              <div
                {...getRootProps()}
                className={`dropzone ${isDragActive ? 'active' : ''}`}
              >
                <input {...getInputProps()} />
                <div className="upload-icon"><Upload size={40} strokeWidth={1.5} /></div>
                <h3>Drop your CSV file here</h3>
                <p>or click to browse · Max 100MB</p>
                <div style={{ marginTop: 20, display: 'flex', gap: 6, justifyContent: 'center', flexWrap: 'wrap' }}>
                  {['Sales Data', 'Financial Reports', 'Survey Results', 'Analytics'].map(tag => (
                    <span key={tag} className="badge badge-numeric">{tag}</span>
                  ))}
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="progress"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="card-glass"
              style={{ padding: 40 }}
            >
              <div className="spinner" style={{ margin: '0 auto 20px' }} />
              <h3 style={{ marginBottom: 8, fontSize: 16, fontWeight: 600 }}>{stage}</h3>
              <div className="progress-bar" style={{ margin: '0 auto' }}>
                <div className="progress-fill" style={{ width: `${progress}%` }} />
              </div>
              <p style={{ color: 'var(--text-muted)', marginTop: 12, fontSize: 13 }}>
                {progress}% complete
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              style={{ marginTop: 20, padding: 12, borderRadius: 10,
                       background: 'rgba(239, 68, 68, 0.06)', border: '1px solid rgba(239, 68, 68, 0.15)',
                       color: '#dc2626', fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}
            >
              <AlertCircle size={16} />
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Feature cards */}
        <div className="feature-grid">
          {[
            { icon: BarChart3, title: 'Auto Dashboard', desc: 'Charts & KPIs generated instantly' },
            { icon: Brain, title: 'AI Insights', desc: 'Trends, anomalies & correlations' },
            { icon: MessageCircle, title: 'Chat with Data', desc: 'Ask questions in plain English' },
          ].map(f => {
            const Icon = f.icon;
            return (
              <div key={f.title} className="feature-card">
                <div className="feature-icon"><Icon size={22} /></div>
                <h4>{f.title}</h4>
                <p>{f.desc}</p>
              </div>
            );
          })}
        </div>
      </motion.div>
    </div>
  );
}
