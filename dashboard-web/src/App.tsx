import { Routes, Route, Navigate } from 'react-router-dom'
import Shell from './components/Layout/Shell'
import Dashboard from './pages/Dashboard'
import Traders from './pages/Traders'
import TraderDetail from './pages/TraderDetail'
import Models from './pages/Models'
import Regimes from './pages/Regimes'
import Events from './pages/Events'
import Settings from './pages/Settings'

export default function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/traders" element={<Traders />} />
        <Route path="/traders/:id" element={<TraderDetail />} />
        <Route path="/models" element={<Models />} />
        <Route path="/regimes" element={<Regimes />} />
        <Route path="/events" element={<Events />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<div className="card p-3">Not Found</div>} />
      </Routes>
    </Shell>
  )
}
