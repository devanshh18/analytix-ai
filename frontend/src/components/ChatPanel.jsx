import { useState, useRef, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { X, Send, MessageCircle, Sparkles, TrendingUp, BarChart3, Download } from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, ScatterChart, Scatter,
} from 'recharts';
import { useApp } from '../context/AppContext';
import { sendChatMessage, fetchSuggestions } from '../services/api';

const CHART_COLORS = ['#2ec4b6', '#1b2a4a', '#3b82f6', '#f59e0b', '#22c55e',
                      '#ef4444', '#8b5cf6', '#ec4899'];

/* ── Chart Download Utility ── */
function downloadChartAsPNG(chartContainerRef, title) {
  if (!chartContainerRef.current) return;
  // Hide the download button before capture
  const btn = chartContainerRef.current.querySelector('[data-download-btn]');
  if (btn) btn.style.display = 'none';

  import('html2canvas').then(({ default: html2canvas }) => {
    html2canvas(chartContainerRef.current, {
      backgroundColor: '#ffffff',
      scale: 2,
    }).then(canvas => {
      if (btn) btn.style.display = '';
      const link = document.createElement('a');
      link.download = `${(title || 'chart').replace(/\s+/g, '_')}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    });
  }).catch(() => {
    if (btn) btn.style.display = '';
    const svgElem = chartContainerRef.current?.querySelector('svg');
    if (!svgElem) return;
    const svgData = new XMLSerializer().serializeToString(svgElem);
    const blob = new Blob([svgData], { type: 'image/svg+xml' });
    const link = document.createElement('a');
    link.download = `${(title || 'chart').replace(/\s+/g, '_')}.svg`;
    link.href = URL.createObjectURL(blob);
    link.click();
  });
}

/* ── Inline Chart Component ── */
function InlineChart({ chartData }) {
  const { chart_type, data, x_column, y_column, title } = chartData;
  const chartRef = useRef(null);
  if (!data || data.length === 0) return null;

  const tooltipStyle = {
    backgroundColor: '#fff', border: '1px solid #e2e6ed', borderRadius: 8,
    color: '#1b2a4a', fontSize: 11, boxShadow: '0 4px 12px rgba(0,0,0,0.08)', padding: '6px 10px',
  };
  const tickStyle = { fill: '#8f96a3', fontSize: 10 };

  return (
    <div ref={chartRef} style={{ marginTop: 10, background: 'var(--bg-base)', borderRadius: 10,
                  padding: '12px 8px 4px', border: '1px solid var(--border-subtle)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingLeft: 8, paddingRight: 8 }}>
        {title && <p style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>{title}</p>}
        <button
          data-download-btn
          onClick={() => downloadChartAsPNG(chartRef, title)}
          style={{
            background: 'none', border: '1px solid var(--border-subtle)', borderRadius: 6,
            padding: '3px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
            fontSize: 10, color: 'var(--text-muted)', transition: 'all 0.2s',
          }}
          onMouseOver={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)'; }}
          onMouseOut={e => { e.currentTarget.style.borderColor = 'var(--border-subtle)'; e.currentTarget.style.color = 'var(--text-muted)'; }}
          title="Download chart"
        >
          <Download size={11} /> Save
        </button>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        {chart_type === 'pie' ? (
          <PieChart>
            <Pie data={data} cx="50%" cy="50%" innerRadius={40} outerRadius={75}
                 paddingAngle={3} dataKey="value" nameKey="name"
                 label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                 labelLine={{ stroke: '#c5d3e3' }}>
              {data.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
          </PieChart>
        ) : chart_type === 'scatter' ? (
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef1f6" />
            <XAxis dataKey={x_column} tick={tickStyle} />
            <YAxis dataKey={y_column} tick={tickStyle} />
            <Tooltip contentStyle={tooltipStyle} />
            <Scatter data={data} fill="#2ec4b6" />
          </ScatterChart>
        ) : chart_type === 'line' || chart_type === 'area' ? (
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef1f6" vertical={false} />
            <XAxis dataKey={x_column} tick={tickStyle} />
            <YAxis tick={tickStyle} />
            <Tooltip contentStyle={tooltipStyle} />
            <Area type="monotone" dataKey={y_column || 'count'} stroke="#2ec4b6"
                  fill="rgba(46,196,182,0.1)" />
          </AreaChart>
        ) : (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef1f6" vertical={false} />
            <XAxis dataKey={x_column || Object.keys(data[0])[0]} tick={tickStyle}
                   angle={-25} textAnchor="end" height={50} />
            <YAxis tick={tickStyle} />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar dataKey={y_column || 'count'} radius={[4, 4, 0, 0]}>
              {data.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
            </Bar>
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

/* ── Inline KPI Card ── */
function InlineKPI({ kpi }) {
  return (
    <div style={{
      marginTop: 10, padding: 16, background: 'linear-gradient(135deg, var(--accent-subtle), #f0fcfb)',
      borderRadius: 12, border: '1px solid rgba(46,196,182,0.15)',
      display: 'flex', alignItems: 'center', gap: 14,
    }}>
      <div style={{
        width: 40, height: 40, borderRadius: 10,
        background: 'rgba(46,196,182,0.12)', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
      }}>
        <TrendingUp size={20} style={{ color: 'var(--accent)' }} />
      </div>
      <div>
        <p style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 500 }}>{kpi.label}</p>
        <p style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.2 }}>
          {kpi.value}
        </p>
      </div>
    </div>
  );
}

/* ── Inline Data Table ── */
function InlineTable({ data }) {
  if (!data || data.length === 0) return null;
  const keys = Object.keys(data[0]);
  return (
    <div style={{ marginTop: 10, overflowX: 'auto', maxHeight: 220, borderRadius: 8,
                  border: '1px solid var(--border-subtle)' }}>
      <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ background: 'var(--bg-base)' }}>
            {keys.map(k => (
              <th key={k} style={{ padding: '6px 10px', borderBottom: '1px solid var(--border-default)',
                                  textAlign: 'left', fontWeight: 600, fontSize: 10,
                                  color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{k}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 25).map((row, j) => (
            <tr key={j} style={{ background: j % 2 === 0 ? 'transparent' : 'var(--bg-base)' }}>
              {keys.map(k => (
                <td key={k} style={{ padding: '4px 10px', borderBottom: '1px solid var(--border-subtle)',
                                     fontSize: 11, whiteSpace: 'nowrap' }}>
                  {row[k] != null ? String(row[k]) : '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Main Chat Panel ── */
export default function ChatPanel() {
  const { datasetId, chatMessages, addChatMessage, setChatOpen } = useApp();
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Fetch LLM-generated suggestions for this dataset
  useEffect(() => {
    if (datasetId) {
      fetchSuggestions(datasetId)
        .then(s => setSuggestions(s))
        .catch(() => setSuggestions([]));
    }
  }, [datasetId]);

  const sendMessage = async (text) => {
    const msg = text || input.trim();
    if (!msg || loading) return;

    addChatMessage('user', msg);
    setInput('');
    setLoading(true);

    try {
      // Build conversation history for context memory
      const history = chatMessages.map(m => ({ role: m.role, content: m.content }));
      const response = await sendChatMessage(datasetId, msg, history);
      addChatMessage('assistant', response.reply, response);
    } catch (err) {
      addChatMessage('assistant', 'Sorry, I encountered an error. Please try again.');
    }

    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <motion.div className="chat-panel"
      initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
      transition={{ type: 'spring', damping: 25, stiffness: 250 }}>

      {/* Header */}
      <div className="chat-header">
        <h3><MessageCircle size={18} className="header-icon" /> AI Analyst</h3>
        <button className="btn-ghost btn" onClick={() => setChatOpen(false)} style={{ padding: 6 }}>
          <X size={18} />
        </button>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {chatMessages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)' }}>
            <Sparkles size={28} style={{ color: 'var(--accent)', marginBottom: 12 }} />
            <p style={{ fontSize: 14, fontWeight: 500, marginBottom: 6, color: 'var(--text-secondary)' }}>
              Ask me to analyze your data
            </p>
            <p style={{ fontSize: 12 }}>I calculate values, create charts, and run queries — not just explain.</p>
          </div>
        )}

        {chatMessages.map((msg, i) => (
          <motion.div key={i} className={`chat-message ${msg.role}`}
            initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
            {/* Text reply */}
            <span>{msg.content}</span>

            {/* KPI Card */}
            {msg.data?.kpi_result && <InlineKPI kpi={msg.data.kpi_result} />}

            {/* Chart */}
            {msg.data?.chart_data && <InlineChart chartData={msg.data.chart_data} />}

            {/* Data Table */}
            {msg.data?.data_result && msg.data.data_result.length > 0 && (
              <InlineTable data={msg.data.data_result} />
            )}
          </motion.div>
        ))}

        {loading && (
          <div className="chat-message assistant" style={{ opacity: 0.7 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <BarChart3 size={14} className="animate-pulse" style={{ color: 'var(--accent)' }} />
              <span className="animate-pulse">Analyzing...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat-input-container">
        <div className="chat-input-wrapper">
          <input ref={inputRef} type="text" value={input}
            onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown}
            placeholder="Ask about your data..." disabled={loading} />
          <button onClick={() => sendMessage()} disabled={loading || !input.trim()}>
            <Send size={16} />
          </button>
        </div>

        {/* Dynamic Suggestions (LLM-generated) */}
        {suggestions.length > 0 && (
          <div className="chat-suggestions">
            {suggestions.slice(0, 6).map((s, i) => (
              <button key={i} onClick={() => sendMessage(s)}>{s}</button>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
