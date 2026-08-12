import { useState, type CSSProperties, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { accentFor } from "../utils/colors";

interface TopbarProps {
  title: string;
  actions?: ReactNode;
}

export function Topbar({ title, actions }: TopbarProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const initials =
    user?.name
      .split(/\s+/)
      .filter(Boolean)
      .map((part) => part[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() ?? "";

  function handleLogout() {
    setUserMenuOpen(false);
    logout();
  }

  function goTo(path: string) {
    setUserMenuOpen(false);
    navigate(path);
  }

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="topbar-brand">
          <button type="button" className="logo-btn" title="Kanban" onClick={() => goTo("/")}>
            <div className="mini-logo">
              <span>K</span>
            </div>
          </button>
          <span className="logo-word">Kanban</span>
          <span className="topbar-divider" />
          <h2 className="topbar-title">{title}</h2>
        </div>

        <div className="topbar-actions">
          <nav className="topbar-nav">
            <button
              type="button"
              className={`nav-link${location.pathname === "/" ? " active" : ""}`}
              onClick={() => goTo("/")}
            >
              Meus quadros
            </button>
          </nav>

          {actions}

          {user && (
            <div className="user-menu">
              <button
                type="button"
                className="user-menu-trigger"
                aria-expanded={userMenuOpen}
                onClick={() => setUserMenuOpen((open) => !open)}
              >
                <span
                  className="user-avatar"
                  style={{ "--avatar-acc": accentFor(user.id) } as CSSProperties}
                >
                  {initials}
                </span>
                <span className="user-menu-meta">
                  <span className="user-menu-name">{user.name}</span>
                  <span className="user-menu-email">{user.email}</span>
                </span>
                <span className="user-menu-caret">▾</span>
              </button>

              {userMenuOpen && (
                <>
                  <div className="user-menu-backdrop" onClick={() => setUserMenuOpen(false)} />
                  <div className="user-menu-dropdown">
                    <div className="user-menu-dropdown-info">
                      <span className="user-menu-dropdown-name">{user.name}</span>
                      <span className="user-menu-dropdown-email">{user.email}</span>
                    </div>
                    <button type="button" className="dropdown-item" onClick={() => goTo("/")}>
                      Meus quadros
                    </button>
                    <div className="dropdown-sep" />
                    <button type="button" className="dropdown-item danger" onClick={handleLogout}>
                      Sair
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}