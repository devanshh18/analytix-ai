import { motion } from 'framer-motion';
import { useApp } from '../context/AppContext';
import InsightPanel from '../components/InsightPanel';

export default function InsightsPage() {
  const { insights, datasetInfo } = useApp();

  if (!insights || insights.length === 0) {
    return (
      <div className="loading-container">
        <p style={{ color: 'var(--text-muted)' }}>No insights generated yet. Upload a dataset first.</p>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="page-header">
        <div>
          <h2>AI Insights</h2>
          <p className="subtitle">
            {insights.length} insights generated for {datasetInfo?.filename}
          </p>
        </div>
      </div>
      <InsightPanel insights={insights} expanded />
    </motion.div>
  );
}
