import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Layout.css';

export default function Layout({ children }) {
  const { session, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!session) {
    return children;
  }

  return (
    <div className="layout">
      <nav className="navbar">
        <div className="nav-content">
          <Link to="/transactions" className="nav-logo">
            Spending Tracker
          </Link>
          <div className="nav-links">
            <Link
              to="/transactions"
              className={location.pathname === '/transactions' ? 'active' : ''}
            >
              Transactions
            </Link>
            <Link
              to="/upload"
              className={location.pathname === '/upload' ? 'active' : ''}
            >
              Upload Statement
            </Link>
            <button onClick={handleLogout} className="logout-button">
              Logout
            </button>
          </div>
        </div>
      </nav>
      <main className="main-content">{children}</main>
    </div>
  );
}
