import { useApp } from '../context/AppContext';
import {
  Upload, BarChart3, Table2, FileText,
  MessageCircle, ChevronLeft, ChevronRight, LogOut
} from 'lucide-react';
import logoImg from '../assets/logo_dark.png';

export default function Sidebar() {
  const { currentPage, setCurrentPage, datasetId,
          sidebarCollapsed, setSidebarCollapsed, clearData, chatOpen, setChatOpen } = useApp();

  const navItems = [
    { id: 'upload', label: 'Upload Data', icon: Upload },
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3, needsData: true },
    { id: 'data', label: 'Data Preview', icon: Table2, needsData: true },
    { id: 'insights', label: 'Insights', icon: FileText, needsData: true },
  ];

  return (
    <nav className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-logo">
        {sidebarCollapsed ? (
          <img src={logoImg} alt="Analytix AI" className="logo-img-collapsed" />
        ) : (
          <img src={logoImg} alt="Analytix AI" className="logo-img" />
        )}
      </div>

      {!sidebarCollapsed && <div className="nav-section-label">Navigation</div>}

      <div className="nav-items">
        {navItems.map(item => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={`nav-item ${currentPage === item.id ? 'active' : ''} ${item.needsData && !datasetId ? 'disabled' : ''}`}
              onClick={() => setCurrentPage(item.id)}
              disabled={item.needsData && !datasetId}
            >
              <span className="icon"><Icon size={18} /></span>
              {!sidebarCollapsed && <span>{item.label}</span>}
            </button>
          );
        })}
      </div>

      {/* Chat CTA — dedicated prominent button */}
      {datasetId && (
        <>
          {!sidebarCollapsed && <div className="nav-section-label">AI Assistant</div>}
          <button
            className={`sidebar-chat-cta ${sidebarCollapsed ? 'collapsed-cta' : ''}`}
            onClick={() => setChatOpen(!chatOpen)}
          >
            <span className="icon"><MessageCircle size={18} /></span>
            {!sidebarCollapsed && <span>Chat with Data</span>}
          </button>
        </>
      )}

      <div className="sidebar-divider" />

      <div className="sidebar-footer">
        {datasetId && (
          <button className="nav-item" onClick={clearData}>
            <span className="icon"><LogOut size={18} /></span>
            {!sidebarCollapsed && <span>New Dataset</span>}
          </button>
        )}

        <button
          className="nav-item"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          style={{ marginTop: 4 }}
        >
          <span className="icon">
            {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </span>
          {!sidebarCollapsed && <span>Collapse</span>}
        </button>
      </div>
    </nav>
  );
}
