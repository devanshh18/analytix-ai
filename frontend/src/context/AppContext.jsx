import { createContext, useContext, useState, useCallback } from 'react';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [datasetId, setDatasetId] = useState(null);
  const [datasetInfo, setDatasetInfo] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [insights, setInsights] = useState([]);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState('upload');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const addChatMessage = useCallback((role, content, data = null) => {
    setChatMessages(prev => [...prev, { role, content, data, timestamp: Date.now() }]);
  }, []);

  const clearData = useCallback(() => {
    setChatOpen(false);
    setDatasetId(null);
    setDatasetInfo(null);
    setDashboard(null);
    setInsights([]);
    setChatMessages([]);
    setError(null);
    setCurrentPage('upload');
  }, []);

  const value = {
    datasetId, setDatasetId,
    datasetInfo, setDatasetInfo,
    dashboard, setDashboard,
    insights, setInsights,
    chatOpen, setChatOpen,
    chatMessages, setChatMessages, addChatMessage,
    loading, setLoading,
    error, setError,
    currentPage, setCurrentPage,
    sidebarCollapsed, setSidebarCollapsed,
    clearData,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within AppProvider');
  return context;
}
