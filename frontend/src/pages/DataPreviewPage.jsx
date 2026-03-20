import { useState } from 'react';
import { useApp } from '../context/AppContext';
import { motion } from 'framer-motion';
import { Search } from 'lucide-react';

const TYPE_BADGE = {
  numeric: 'badge-numeric',
  categorical: 'badge-categorical',
  datetime: 'badge-datetime',
  text: 'badge-text',
  boolean: 'badge-boolean',
};

export default function DataPreviewPage() {
  const { datasetInfo } = useApp();
  const [search, setSearch] = useState('');
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState('asc');

  if (!datasetInfo) {
    return (
      <div className="loading-container">
        <p style={{ color: 'var(--text-muted)' }}>No dataset loaded.</p>
      </div>
    );
  }

  const { preview = [], column_info = [] } = datasetInfo;
  const columns = column_info.map(c => c.name);

  let filtered = preview;
  if (search) {
    const searchLower = search.toLowerCase();
    filtered = preview.filter(row =>
      Object.values(row).some(v => String(v).toLowerCase().includes(searchLower))
    );
  }

  if (sortCol) {
    filtered = [...filtered].sort((a, b) => {
      const va = a[sortCol], vb = b[sortCol];
      if (va === vb) return 0;
      const cmp = va < vb ? -1 : 1;
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortCol(col);
      setSortDir('asc');
    }
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="animate-fade-in">
      <div className="page-header">
        <div>
          <h2>Data Preview</h2>
          <p className="subtitle">
            {datasetInfo.filename} · Showing {Math.min(filtered.length, 100)} of {datasetInfo.rows?.toLocaleString()} rows
          </p>
        </div>
      </div>

      {/* Column Info Cards */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
        {column_info.map(col => (
          <div key={col.name} style={{
            padding: '7px 12px', borderRadius: 'var(--radius-sm)',
            background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
            fontSize: 13, display: 'flex', gap: 8, alignItems: 'center',
            boxShadow: 'var(--shadow-xs)',
          }}>
            <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{col.name}</span>
            <span className={`badge ${TYPE_BADGE[col.col_type] || 'badge-text'}`}>{col.col_type}</span>
            {col.missing_count > 0 && (
              <span style={{ color: 'var(--warning)', fontSize: 11 }}>{col.missing_pct}% missing</span>
            )}
          </div>
        ))}
      </div>

      {/* Search */}
      <div style={{ marginBottom: 16, position: 'relative', maxWidth: 360 }}>
        <Search size={16} style={{ position: 'absolute', left: 12, top: 11, color: 'var(--text-muted)' }} />
        <input
          type="text"
          placeholder="Search data..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            width: '100%', padding: '9px 14px 9px 36px', borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-default)', background: 'var(--bg-surface)',
            color: 'var(--text-primary)', fontSize: 13, outline: 'none',
            fontFamily: 'Inter, sans-serif', boxShadow: 'var(--shadow-xs)',
          }}
        />
      </div>

      {/* Data Table */}
      <div className="data-preview" style={{ maxHeight: 560, overflowY: 'auto' }}>
        <table>
          <thead>
            <tr>
              {columns.map(col => (
                <th key={col} onClick={() => handleSort(col)} style={{ cursor: 'pointer', userSelect: 'none' }}>
                  {col} {sortCol === col ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, 100).map((row, i) => (
              <tr key={i}>
                {columns.map(col => (
                  <td key={col}>{row[col] != null ? String(row[col]) : '—'}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}
