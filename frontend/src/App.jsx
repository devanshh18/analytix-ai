import { AppProvider, useApp } from './context/AppContext';
import Sidebar from './components/Sidebar';
import UploadPage from './pages/UploadPage';
import DashboardPage from './pages/DashboardPage';
import DataPreviewPage from './pages/DataPreviewPage';
import InsightsPage from './pages/InsightsPage';
import { AnimatePresence, motion } from 'framer-motion';

function AppContent() {
  const { currentPage, sidebarCollapsed } = useApp();

  const pages = {
    upload: <UploadPage />,
    dashboard: <DashboardPage />,
    data: <DataPreviewPage />,
    insights: <InsightsPage />,
  };

  return (
    <div className="app-shell">
      <Sidebar />
      <main className={`main-content ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <AnimatePresence mode="wait">
          <motion.div
            key={currentPage}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.25 }}
          >
            {pages[currentPage] || <UploadPage />}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}
