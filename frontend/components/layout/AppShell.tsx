'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { UserRole } from '@/types/auth';

interface AppShellProps {
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  // Client-side authentication state from localStorage
  const [user, setUser] = useState<{ username: string; role: UserRole; subsidiary: string } | null>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('coalintel_user');
      if (stored) {
        try {
          return JSON.parse(stored);
        } catch (e) {
          // Ignore json parse error
        }
      }
    }
    return { username: 'analyst', role: 'Analyst', subsidiary: 'CMPDI' };
  });

  // Lock body scroll when mobile drawer is open
  React.useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileOpen]);

  const handleLogout = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('coalintel_token');
      localStorage.removeItem('coalintel_user');
    }
    router.push('/login');
  };

  return (
    <div className="min-h-screen bg-[#0E1113] flex font-sans text-[#E8ECEB] antialiased selection:bg-[#C58B3A]/30 selection:text-[#E8ECEB]">
      {/* Desktop Sidebar */}
      <div className="hidden lg:block">
        <Sidebar
          collapsed={collapsed}
          onToggleCollapse={() => setCollapsed(!collapsed)}
          userRole={user?.role || 'Analyst'}
          userName={user?.username || 'CMPDI Analyst'}
          userSubsidiary={user?.subsidiary || 'CMPDI'}
          onLogout={handleLogout}
        />
      </div>

      {/* Mobile Drawer Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-[#0E1113]/80 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile Sidebar Drawer */}
      <div
        className={`fixed inset-y-0 left-0 z-50 transform transition-transform duration-300 lg:hidden ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <Sidebar
          collapsed={false}
          userRole={user?.role || 'Analyst'}
          userName={user?.username || 'CMPDI Analyst'}
          userSubsidiary={user?.subsidiary || 'CMPDI'}
          onLogout={handleLogout}
          onNavigate={() => setMobileOpen(false)}
        />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#0E1113]">
        <Header
          onMobileMenuToggle={() => setMobileOpen(!mobileOpen)}
          userName={user?.username || 'CMPDI Analyst'}
          userRole={user?.role || 'Analyst'}
          showLogoOnDesktop={collapsed}
        />

        <main className="flex-1 p-3 sm:p-5 md:p-6 lg:p-8 max-w-7xl 2xl:max-w-[1720px] w-full mx-auto space-y-6 animate-page-enter">
          {children}
        </main>

        <footer className="py-4 px-6 border-t border-[#30383D] text-center text-xs text-[#9BA5A8] font-mono bg-[#0E1113]">
          COALINTEL V2 Platform • Evidence-Driven Geological & Mining Intelligence • Ministry of Coal / CIL
        </footer>
      </div>
    </div>
  );
};
