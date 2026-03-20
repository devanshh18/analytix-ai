import { motion } from 'framer-motion';
import { Brain } from 'lucide-react';

export default function InsightPanel({ insights, expanded = false }) {
  if (!insights || insights.length === 0) {
    return <p style={{ color: 'var(--text-muted)', textAlign: 'center' }}>No insights available.</p>;
  }

  return (
    <div className="insight-panel">
      <div className="insight-panel-header">
        <Brain size={18} style={{ color: 'var(--accent)' }} />
        <h3>AI-Generated Insights</h3>
        <span className="insight-count">{insights.length}</span>
      </div>
      {insights.map((insight, i) => (
        <motion.div
          key={insight.id || i}
          className="insight-card"
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.06 }}
          style={insight.importance === 'high' ? { borderLeftColor: 'var(--danger)' } :
                 insight.importance === 'medium' ? { borderLeftColor: 'var(--warning)' } : {}}
        >
          <span className={`insight-category ${insight.category || 'summary'}`}>
            {insight.category || 'insight'}
          </span>
          <h4>{insight.title}</h4>
          <p>{insight.description}</p>
          {insight.related_columns?.length > 0 && (
            <div style={{ marginTop: 8, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {insight.related_columns.map(col => (
                <span key={col} className="badge badge-text" style={{ fontSize: 10 }}>{col}</span>
              ))}
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}
