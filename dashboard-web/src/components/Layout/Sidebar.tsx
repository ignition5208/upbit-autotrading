import { NavLink } from 'react-router-dom'

export default function Sidebar() {
  return (
    <aside className="sidebar p-3 d-none d-lg-block">
      <div className="d-flex align-items-center gap-2 mb-3">
        <div className="rounded-3 px-2 py-1 border border-soft bg-panel mono">ATS</div>
        <div>
          <div className="fw-semibold">Upbit ATS</div>
          <div className="text-muted-2 small">v1.8-0001</div>
        </div>
      </div>

      <nav className="nav flex-column gap-1">
        <NavLink className="nav-link" to="/dashboard">Dashboard</NavLink>
        <NavLink className="nav-link" to="/traders">Traders</NavLink>
        <NavLink className="nav-link" to="/models">Models</NavLink>
        <NavLink className="nav-link" to="/regimes">Regimes</NavLink>
        <NavLink className="nav-link" to="/events">Events</NavLink>
        <NavLink className="nav-link" to="/settings">Settings</NavLink>
      </nav>

      <hr className="soft my-3" />

      <div className="small text-muted-2">
        <div>Design: Terminal Dark</div>
        <div className="mt-1">Mode is per-trader</div>
      </div>
    </aside>
  )
}
