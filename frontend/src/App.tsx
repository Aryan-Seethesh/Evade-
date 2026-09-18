import { BrowserRouter, Route, Routes } from 'react-router-dom';
import Layout from './pages/Layout';
import Dashboard from './pages/Dashboard';
import AnalyticsPage from './pages/AnalyticsPage';
import DecisionsPage from './pages/DecisionsPage';
import ArchitecturePage from './pages/ArchitecturePage';
import ScenariosPage from './pages/ScenariosPage';
import './styles.css';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/decisions" element={<DecisionsPage />} />
          <Route path="/architecture" element={<ArchitecturePage />} />
          <Route path="/scenarios" element={<ScenariosPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
