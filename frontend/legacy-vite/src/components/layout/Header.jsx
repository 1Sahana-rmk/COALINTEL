import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, LogOut, User as UserIcon, Building2, Menu } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../common/Badge';

export const Header = ({ onMenuToggle }) => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearchSubmit = (e) => {
    if (e.key === 'Enter' && searchQuery.trim()) {
      navigate(`/documents?search=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <header className="h-16 bg-slate-900/90 backdrop-blur border-b border-slate-800 px-4 sm:px-6 flex items-center justify-between sticky top-0 z-20 gap-3">
      <div className="flex items-center gap-3 max-w-md w-full">
        {/* Mobile Hamburger Menu Toggle */}
        <button
          onClick={onMenuToggle}
          className="md:hidden p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors shrink-0"
          title="Toggle Navigation Menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Global Search Shell */}
        <div className="relative w-full min-w-0">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          <input
            type="text"
            placeholder="Search mines, documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleSearchSubmit}
            className="w-full bg-slate-800/80 border border-slate-700/80 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-amber-500/60 focus:ring-1 focus:ring-amber-500/60 transition-all"
          />
        </div>
      </div>

      {/* User Context & Actions */}
      <div className="flex items-center space-x-3 shrink-0">
        {user && (
          <div className="hidden sm:flex items-center space-x-3 text-xs border-r border-slate-800 pr-4">
            <div className="flex items-center gap-1.5 text-slate-400">
              <Building2 className="w-3.5 h-3.5 text-amber-500" />
              <span className="font-medium text-slate-300">{user.subsidiary}</span>
            </div>
            <Badge status={user.role === 'Admin' ? 'SUCCESS' : user.role === 'Reviewer' ? 'WARNING' : 'INFO'}>
              {user.role}
            </Badge>
          </div>
        )}

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-2 text-xs">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-amber-400 font-semibold">
              <UserIcon className="w-4 h-4" />
            </div>
            <div className="hidden sm:block text-left">
              <div className="font-medium text-white text-xs">{user?.full_name || user?.username || 'User'}</div>
              <div className="text-[10px] text-slate-500">{user?.username}</div>
            </div>
          </div>

          <button
            onClick={logout}
            title="Logout"
            className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
