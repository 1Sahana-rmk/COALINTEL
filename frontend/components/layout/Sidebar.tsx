'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  FileText,
  Sparkles,
  BarChart3,
  ShieldCheck,
  GitCompare,
  FileSpreadsheet,
  History,
  Landmark,
  Mountain,
  ChevronLeft,
  ChevronRight,
  LogOut,
  User as UserIcon,
} from 'lucide-react';
import { Logo } from '@/components/ui/Logo';
import { cn } from '@/lib/utils/cn';
import { NAV_ITEMS, NavItem } from '@/lib/constants';

interface SidebarProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  userRole?: string;
  userName?: string;
  userSubsidiary?: string;
  onLogout?: () => void;
  onNavigate?: () => void;
}

const iconMap: Record<string, React.ReactNode> = {
  LayoutDashboard: <LayoutDashboard className="h-4 w-4" />,
  Mountain: <Mountain className="h-4 w-4" />,
  FileText: <FileText className="h-4 w-4" />,
  Sparkles: <Sparkles className="h-4 w-4" />,
  Landmark: <Landmark className="h-4 w-4" />,
  BarChart3: <BarChart3 className="h-4 w-4" />,
  ShieldCheck: <ShieldCheck className="h-4 w-4" />,
  GitCompare: <GitCompare className="h-4 w-4" />,
  FileSpreadsheet: <FileSpreadsheet className="h-4 w-4" />,
  History: <History className="h-4 w-4" />,
};

export const Sidebar: React.FC<SidebarProps> = ({
  collapsed = false,
  onToggleCollapse,
  userRole = 'Analyst',
  userName = 'CMPDI Analyst',
  userSubsidiary = 'CMPDI',
  onLogout,
  onNavigate,
}) => {
  const pathname = usePathname();

  // Filter navigation items by role permissions
  const filteredNav = NAV_ITEMS.filter((item) => {
    if (!item.roles || item.roles.length === 0) return true;
    return item.roles.includes(userRole);
  });

  const intelligenceHrefs = ['/dashboard', '/query', '/mines', '/analytics'];
  const repositoryHrefs = ['/documents', '/comparison', '/validation', '/conflicts'];
  const reportingHrefs = ['/parliamentary', '/reports'];
  const governanceHrefs = ['/audit'];

  const intelligenceNav = filteredNav.filter((i) => intelligenceHrefs.includes(i.href));
  const repositoryNav = filteredNav.filter((i) => repositoryHrefs.includes(i.href));
  const reportingNav = filteredNav.filter((i) => reportingHrefs.includes(i.href));
  const governanceNav = filteredNav.filter((i) => governanceHrefs.includes(i.href));

  const renderNavGroup = (items: NavItem[], groupTitle: string) => {
    if (items.length === 0) return null;
    return (
      <div className="space-y-1">
        {!collapsed && (
          <p className="px-3 text-[10px] font-mono uppercase tracking-widest text-[#9BA5A8] pt-2 pb-1 font-semibold">
            {groupTitle}
          </p>
        )}

        {items.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/dashboard' && pathname.startsWith(item.href));

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => {
                if (onNavigate) onNavigate();
              }}
              className={cn(
                'group relative flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150',
                isActive
                  ? 'bg-[#C58B3A]/15 text-[#C58B3A] font-semibold border border-[#C58B3A]/40 shadow-sm'
                  : 'text-[#9BA5A8] hover:text-[#E8ECEB] hover:bg-[#1C2226] hover:border-[#30383D] border border-transparent'
              )}
              aria-current={isActive ? 'page' : undefined}
            >
              {/* Left Accent indicator */}
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-[#C58B3A] rounded-r" />
              )}

              <div
                className={cn(
                  'shrink-0 transition-colors duration-150',
                  isActive ? 'text-[#C58B3A]' : 'text-[#9BA5A8] group-hover:text-[#E8ECEB]'
                )}
              >
                {iconMap[item.icon]}
              </div>

              {!collapsed && <span className="truncate">{item.label}</span>}

              {/* Tooltip for collapsed mode */}
              {collapsed && (
                <div className="absolute left-full ml-3.5 px-2.5 py-1 bg-[#1C2226] border border-[#30383D] text-[#E8ECEB] text-xs rounded-md shadow-dropdown whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity duration-150 z-50 flex items-center gap-1.5">
                  <span>{item.label}</span>
                  {item.roles && item.roles.length > 0 && (
                    <span className="text-[9px] font-mono text-[#C58B3A]">[{item.roles[0]}]</span>
                  )}
                </div>
              )}
            </Link>
          );
        })}
      </div>
    );
  };

  return (
    <aside
      className={cn(
        'relative flex flex-col bg-[#151A1D] border-r border-[#30383D] text-[#E8ECEB] transition-all duration-200 h-screen sticky top-0 z-30 select-none shadow-sm',
        collapsed ? 'w-20' : 'w-64'
      )}
    >
      {/* Header & Brand Logo */}
      <div className="flex items-center justify-between h-16 px-3.5 border-b border-[#30383D] gap-2 overflow-hidden">
        <Logo size={collapsed ? 'sm' : 'md'} showText={!collapsed} className="min-w-0 flex-1" />
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="p-1.5 rounded-lg bg-[#1C2226] hover:bg-[#242C30] border border-[#30383D] text-[#9BA5A8] hover:text-[#E8ECEB] transition-colors hidden lg:flex items-center justify-center shrink-0"
            title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
            aria-label={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        )}
      </div>

      {/* Navigation List */}
      <nav className="flex-1 overflow-y-auto px-3 py-2 space-y-2.5 scrollbar-thin">
        {renderNavGroup(intelligenceNav, 'Intelligence Suite')}
        <div className="h-px bg-[#30383D]/60 mx-1 my-1" />
        {renderNavGroup(repositoryNav, 'Repository & Verification')}
        <div className="h-px bg-[#30383D]/60 mx-1 my-1" />
        {renderNavGroup(reportingNav, 'Reporting & Parliament')}
        {governanceNav.length > 0 && (
          <>
            <div className="h-px bg-[#30383D]/60 mx-1 my-1" />
            {renderNavGroup(governanceNav, 'Governance & Audit')}
          </>
        )}
      </nav>

      {/* User Profile & Logout Section */}
      <div className="p-3 border-t border-[#30383D] bg-[#151A1D]">
        <div className={cn('flex items-center gap-3', collapsed ? 'justify-center' : 'justify-between')}>
          {!collapsed ? (
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="h-8 w-8 rounded-lg bg-[#1C2226] border border-[#30383D] flex items-center justify-center text-[#C58B3A] font-bold shrink-0">
                <UserIcon className="h-4 w-4" />
              </div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs font-semibold text-[#E8ECEB] truncate">{userName}</span>
                <span className="text-[10px] font-mono text-[#9BA5A8] truncate uppercase">
                  {userRole} • {userSubsidiary}
                </span>
              </div>
            </div>
          ) : (
            <div className="group relative flex items-center justify-center">
              <div className="h-8 w-8 rounded-lg bg-[#1C2226] border border-[#30383D] flex items-center justify-center text-[#C58B3A] font-bold cursor-pointer">
                <UserIcon className="h-4 w-4" />
              </div>
              <div className="absolute left-full ml-3.5 px-2.5 py-1 bg-[#1C2226] border border-[#30383D] text-[#E8ECEB] text-xs rounded-md shadow-dropdown whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity duration-150 z-50">
                {userName} ({userRole})
              </div>
            </div>
          )}

          {onLogout && !collapsed && (
            <button
              onClick={onLogout}
              className="p-1.5 rounded-lg text-[#9BA5A8] hover:text-[#C94B45] hover:bg-[#C94B45]/10 transition-colors"
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
};
