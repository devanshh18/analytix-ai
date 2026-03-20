import { useState } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area, ScatterChart, Scatter, Legend,
} from 'recharts';
import { motion } from 'framer-motion';
import { Info, Image, ArrowLeftRight, Lightbulb } from 'lucide-react';
import { explainChart, getChartImageUrl } from '../services/api';

const COLORS = ['#2ec4b6', '#1b2a4a', '#3b82f6', '#f59e0b', '#22c55e',
                '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316'];

const CHART_TYPES = ['bar', 'line', 'pie', 'histogram', 'area', 'scatter'];

export default function ChartCard({ chart, datasetId }) {
  const [explanation, setExplanation] = useState(null);
  const [loadingExplain, setLoadingExplain] = useState(false);
  const [chartType, setChartType] = useState(chart.chart_type);
  const [showTypeSelector, setShowTypeSelector] = useState(false);

  const data = chart.data || [];
  const xCol = chart.x_column;
  const yCol = chart.y_column || 'count';

  const handleExplain = async () => {
    if (explanation) { setExplanation(null); return; }
    setLoadingExplain(true);
    try {
      const res = await explainChart(datasetId, chart);
      setExplanation(res.explanation);
    } catch { setExplanation('Unable to generate explanation.'); }
    setLoadingExplain(false);
  };

  const tooltipStyle = {
    backgroundColor: '#ffffff',
    border: '1px solid #e2e6ed',
    borderRadius: 8,
    color: '#1b2a4a',
    fontSize: 12,
    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
    padding: '8px 12px',
  };

  const gridStroke = '#eef1f6';
  const tickStyle = { fill: '#8f96a3', fontSize: 11 };

  const renderChart = () => {
    const type = chartType;

    if (type === 'bar' || type === 'histogram') {
      return (
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
            <XAxis dataKey={xCol} tick={tickStyle} angle={-30} textAnchor="end" height={60} axisLine={{ stroke: gridStroke }} />
            <YAxis tick={tickStyle} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(46, 196, 182, 0.04)' }} />
            <Bar dataKey={yCol} radius={[4, 4, 0, 0]}>
              {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      );
    }

    if (type === 'line') {
      return (
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id={`grad_${chart.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2ec4b6" stopOpacity={0.12} />
                <stop offset="100%" stopColor="#2ec4b6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
            <XAxis dataKey={xCol} tick={tickStyle} angle={-30} textAnchor="end" height={60} axisLine={{ stroke: gridStroke }} />
            <YAxis tick={tickStyle} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} />
            <Area type="monotone" dataKey={yCol} stroke="#2ec4b6" strokeWidth={2}
                  fill={`url(#grad_${chart.id})`} dot={{ r: 3, fill: '#2ec4b6', strokeWidth: 0 }} />
          </AreaChart>
        </ResponsiveContainer>
      );
    }

    if (type === 'pie') {
      return (
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie data={data} cx="50%" cy="50%" innerRadius={55} outerRadius={100}
                 paddingAngle={3} dataKey="value" nameKey="name"
                 label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                 labelLine={{ stroke: '#c5d3e3' }}>
              {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
          </PieChart>
        </ResponsiveContainer>
      );
    }

    if (type === 'scatter') {
      return (
        <ResponsiveContainer width="100%" height={280}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
            <XAxis dataKey={xCol} tick={tickStyle} name={xCol} axisLine={{ stroke: gridStroke }} />
            <YAxis dataKey={yCol} tick={tickStyle} name={yCol} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} />
            <Scatter data={data} fill="#2ec4b6" />
          </ScatterChart>
        </ResponsiveContainer>
      );
    }

    if (type === 'area') {
      return (
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} vertical={false} />
            <XAxis dataKey={xCol} tick={tickStyle} axisLine={{ stroke: gridStroke }} />
            <YAxis tick={tickStyle} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} />
            <Area type="monotone" dataKey={yCol} stroke="#1b2a4a" fill="rgba(27,42,74,0.06)" />
          </AreaChart>
        </ResponsiveContainer>
      );
    }

    return <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>Unsupported chart type</p>;
  };

  return (
    <div className="chart-card">
      <div className="chart-header">
        <h3>{chart.title}</h3>
        <div className="chart-actions">
          <button onClick={() => setShowTypeSelector(!showTypeSelector)} title="Change chart type">
            <ArrowLeftRight size={14} />
          </button>
          <button onClick={handleExplain} title="Explain this chart">
            {loadingExplain ? '···' : <Info size={14} />}
          </button>
          <a href={getChartImageUrl(datasetId, chart.id)} download title="Download chart image">
            <Image size={14} />
          </a>
        </div>
      </div>

      {showTypeSelector && (
        <div style={{ display: 'flex', gap: 4, marginBottom: 12, flexWrap: 'wrap' }}>
          {CHART_TYPES.map(t => (
            <button key={t}
              className={`tab ${chartType === t ? 'active' : ''}`}
              style={{ padding: '5px 12px', fontSize: 12 }}
              onClick={() => { setChartType(t); setShowTypeSelector(false); }}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      )}

      {chart.description && (
        <p style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 12 }}>{chart.description}</p>
      )}

      {renderChart()}

      {explanation && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          style={{ marginTop: 12, padding: 12, borderRadius: 10,
                   background: 'var(--accent-subtle)', border: '1px solid rgba(46, 196, 182, 0.12)',
                   fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6,
                   display: 'flex', gap: 8, alignItems: 'flex-start' }}
        >
          <Lightbulb size={16} style={{ color: 'var(--accent)', flexShrink: 0, marginTop: 2 }} />
          <span>{explanation}</span>
        </motion.div>
      )}
    </div>
  );
}
