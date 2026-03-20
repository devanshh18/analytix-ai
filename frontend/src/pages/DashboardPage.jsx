import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { MessageCircle, FileText, Presentation, Lightbulb, SlidersHorizontal,
         Database, Columns3, TrendingUp, Trophy, CalendarDays, CheckCircle2, BarChart3, Loader2 } from 'lucide-react';
import { useApp } from '../context/AppContext';
import ChartCard from '../components/ChartCard';
import InsightPanel from '../components/InsightPanel';
import ChatPanel from '../components/ChatPanel';
import { getExportPdfUrl, getExportPptxUrl } from '../services/api';

// KPI icon mapping — lucide-react icons
const ICON_MAP = {
  'database': Database,
  'columns': Columns3,
  'trending-up': TrendingUp,
  'award': Trophy,
  'calendar': CalendarDays,
  'check-circle': CheckCircle2,
  'bar-chart': BarChart3,
};

export default function DashboardPage() {
  const { dashboard, insights, datasetId, chatOpen, setChatOpen, datasetInfo } = useApp();
  const [activeFilters, setActiveFilters] = useState({});
  const [showInsights, setShowInsights] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportingPpt, setExportingPpt] = useState(false);

  const handleExport = async (type) => {
    if (type === 'pdf') setExportingPdf(true);
    else setExportingPpt(true);

    try {
      const url = type === 'pdf' ? getExportPdfUrl(datasetId) : getExportPptxUrl(datasetId);
      const response = await fetch(url);
      if (!response.ok) throw new Error('Export failed');
      const blob = await response.blob();
      
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = downloadUrl;
      a.download = `AnalytixAI_Report_${datasetInfo?.filename?.split('.')[0] || 'Data'}.${type}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      a.remove();
    } catch (error) {
      console.error('Export error:', error);
      alert('Failed to generate export. Please try again.');
    } finally {
      if (type === 'pdf') setExportingPdf(false);
      else setExportingPpt(false);
    }
  };

  const kpis = dashboard?.kpis || [];
  const charts = dashboard?.charts || [];
  const filters = dashboard?.filters || [];

  const handleFilterChange = (column, value) => {
    setActiveFilters(prev => {
      if (!value || value === '__all__') {
        const next = { ...prev };
        delete next[column];
        return next;
      }
      return { ...prev, [column]: value };
    });
  };

  // Client-side filtering of chart data — must be before any early return
  const filteredCharts = useMemo(() => {
    if (Object.keys(activeFilters).length === 0) return charts;

    return charts.map(chart => {
      let filteredData = [...(chart.data || [])];

      Object.entries(activeFilters).forEach(([filterKey, filterValue]) => {
        if (filterKey.endsWith('_min') || filterKey.endsWith('_max')) {
          const baseColumn = filterKey.replace(/_min$|_max$/, '');
          if (chart.x_column === baseColumn) {
            filteredData = filteredData.filter(row => {
              const rowDate = row[baseColumn];
              if (!rowDate) return true;
              if (filterKey.endsWith('_min') && rowDate < filterValue) return false;
              if (filterKey.endsWith('_max') && rowDate > filterValue) return false;
              return true;
            });
          }
        } else {
          if (chart.x_column === filterKey) {
            filteredData = filteredData.filter(row => String(row[filterKey]) === String(filterValue));
          }
        }
      });

      return { ...chart, data: filteredData };
    });
  }, [charts, activeFilters]);

  // Loading state — AFTER all hooks
  if (!dashboard) {
    return (
      <div className="loading-container">
        <div className="spinner" />
        <p style={{ color: 'var(--text-muted)' }}>Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in" style={{ paddingRight: chatOpen ? 410 : 0, transition: 'padding 0.3s' }}>
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h2>{dashboard.title || 'Dashboard'}</h2>
          <p className="subtitle">
            {datasetInfo?.filename} · {datasetInfo?.rows?.toLocaleString()} rows · {datasetInfo?.columns} columns
          </p>
        </div>
        <div className="actions">
          <button className="btn btn-secondary" onClick={() => setShowInsights(!showInsights)}>
            <Lightbulb size={15} />
            {showInsights ? 'Hide Insights' : 'Insights'}
          </button>
          <button className="btn btn-secondary" onClick={() => handleExport('pdf')} disabled={exportingPdf}>
            {exportingPdf ? <Loader2 size={15} className="spin" /> : <FileText size={15} />}
            PDF
          </button>
          <button className="btn btn-secondary" onClick={() => handleExport('pptx')} disabled={exportingPpt}>
            {exportingPpt ? <Loader2 size={15} className="spin" /> : <Presentation size={15} />}
            PPT
          </button>
        </div>
      </div>

      {/* Filters */}
      {filters.length > 0 && (
        <div className="filter-bar">
          <span className="filter-icon"><SlidersHorizontal size={16} /></span>
          {filters.map(f => (
            <div key={f.id} className="filter-item">
              <label>{f.label}</label>
              {f.type === 'select' ? (
                <select onChange={e => handleFilterChange(f.column, e.target.value)}>
                  <option value="__all__">All</option>
                  {f.options?.map(opt => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              ) : f.type === 'date_range' ? (
                <>
                  <input type="date" defaultValue={f.min}
                         onChange={e => handleFilterChange(f.column + '_min', e.target.value)} />
                  <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>to</span>
                  <input type="date" defaultValue={f.max}
                         onChange={e => handleFilterChange(f.column + '_max', e.target.value)} />
                </>
              ) : null}
            </div>
          ))}
        </div>
      )}

      {/* KPI Cards */}
      <div className="kpi-grid">
        {kpis.map((kpi, i) => {
          const IconComp = ICON_MAP[kpi.icon] || BarChart3;
          return (
            <motion.div
              key={kpi.id}
              className="kpi-card"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
            >
              <div className="kpi-icon"><IconComp size={20} /></div>
              <div className="kpi-label">{kpi.label}</div>
              <div className="kpi-value">{typeof kpi.value === 'number' ? kpi.value.toLocaleString() : kpi.value}</div>
            </motion.div>
          );
        })}
      </div>

      {/* Insights Panel (toggleable) */}
      {showInsights && insights.length > 0 && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          style={{ marginBottom: 24 }}
        >
          <InsightPanel insights={insights} />
        </motion.div>
      )}

      {/* Charts Grid */}
      <div className="chart-grid">
        {filteredCharts.map((chart, i) => (
          <motion.div
            key={chart.id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 + i * 0.08 }}
          >
            <ChartCard chart={chart} datasetId={datasetId} />
          </motion.div>
        ))}
      </div>

      {/* Floating Chat FAB */}
      {!chatOpen && (
        <button className="chat-fab" onClick={() => setChatOpen(true)} title="Chat with your data">
          <MessageCircle size={22} />
          <span className="fab-badge" />
        </button>
      )}

      {/* Chat Panel */}
      {chatOpen && <ChatPanel />}
    </div>
  );
}
