import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Activity, Heart, LayoutDashboard, Database, MessageSquare, LogOut, ShieldCheck, User } from 'lucide-react';

export const Navbar = () => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!user) return null;

  const isActive = (path) => location.pathname === path;

  return (
    <nav style={{
      background: 'rgba(15, 23, 42, 0.95)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
      padding: '12px 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      position: 'sticky',
      top: 0,
      zIndex: 50
    }}>
      {/* Brand Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: '12px',
          background: 'linear-gradient(135deg, #10b981 0%, #06b6d4 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 16px rgba(16, 185, 129, 0.4)'
        }}>
          <Heart size={22} color="#ffffff" fill="#ffffff" />
        </div>
        <div>
          <span style={{ fontWeight: 800, fontSize: '1.1rem', letterSpacing: '-0.02em', color: '#ffffff' }}>
            Healthcare <span style={{ color: '#34d399' }}>Navigator</span>
          </span>
          <span style={{ display: 'block', fontSize: '0.65rem', color: '#06b6d4', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>
            Conversational Companion • August AI Model
          </span>
        </div>
      </div>

      {/* Nav Links */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Link
          to="/chat"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 14px',
            borderRadius: '8px',
            textDecoration: 'none',
            fontSize: '0.875rem',
            fontWeight: 600,
            color: isActive('/chat') ? '#ffffff' : '#94a3b8',
            background: isActive('/chat') ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
            border: isActive('/chat') ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid transparent',
            transition: 'all 0.2s'
          }}
        >
          <MessageSquare size={16} />
          Health Chat
        </Link>

        {isAdmin && (
          <>
            <Link
              to="/admin/dashboard"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 14px',
                borderRadius: '8px',
                textDecoration: 'none',
                fontSize: '0.875rem',
                fontWeight: 600,
                color: isActive('/admin/dashboard') ? '#ffffff' : '#94a3b8',
                background: isActive('/admin/dashboard') ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
                border: isActive('/admin/dashboard') ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid transparent',
                transition: 'all 0.2s'
              }}
            >
              <LayoutDashboard size={16} />
              Triage Dashboard
            </Link>

            <Link
              to="/admin/kb"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 14px',
                borderRadius: '8px',
                textDecoration: 'none',
                fontSize: '0.875rem',
                fontWeight: 600,
                color: isActive('/admin/kb') ? '#ffffff' : '#94a3b8',
                background: isActive('/admin/kb') ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
                border: isActive('/admin/kb') ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid transparent',
                transition: 'all 0.2s'
              }}
            >
              <Database size={16} />
              Clinical Guidelines RAG
            </Link>
          </>
        )}
      </div>

      {/* User Info & Logout */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(30, 41, 59, 0.6)',
          padding: '6px 12px',
          borderRadius: '20px',
          border: '1px solid rgba(255, 255, 255, 0.08)'
        }}>
          {user.role === 'admin' ? (
            <ShieldCheck size={16} color="#10b981" />
          ) : (
            <User size={16} color="#06b6d4" />
          )}
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#e2e8f0' }}>{user.email}</span>
        </div>

        <button
          onClick={handleLogout}
          title="Sign out"
          style={{
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            color: '#94a3b8',
            padding: '8px',
            borderRadius: '8px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s'
          }}
        >
          <LogOut size={18} />
        </button>
      </div>
    </nav>
  );
};
