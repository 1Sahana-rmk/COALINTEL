'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { Menu, Bell, Shield, Database, Search } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Logo } from '@/components/ui/Logo';
import { useScope } from '@/context/ScopeContext';
import { CIL_SUBSIDIARIES } from '@/lib/constants';
import { cn } from '@/lib/utils/cn';

interface HeaderProps {
  onMobileMenuToggle?: () => void;
  userName?: string;
  userRole?: string;
  showLogoOnDesktop?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  onMobileMenuToggle,
  userName = 'CMPDI Analyst',
  userRole = 'Analyst',
  showLogoOnDesktop = true,
}) => {
  const router = useRouter();
  const { selectedSubsidiary, setSelectedSubsidiary, selectedFiscalYear } = useScope();
  const [searchQuery, setSearchQuery] = useState('');
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    router.push(`/query?q=${encodeURIComponent(searchQuery.trim())}`);
  };

  return (
    <header className="sticky top-0 z-20 h-16 bg-[#151A1D] border-b border-[#30383D] px-3 sm:px-4 lg:px-6 flex items-center justify-between shadow-sm gap-2 sm:gap-4">
      {/* Left: Mobile Toggle, Header Branding & Context Indicator */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        {onMobileMenuToggle && (
          <button
            onClick={onMobileMenuToggle}
            className="p-2 rounded-lg bg-[#1C2226] border border-[#30383D] text-[#9BA5A8] hover:text-[#E8ECEB] lg:hidden transition-colors shrink-0"
            aria-label="Open mobile navigation"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}

        {/* Header Branding */}
        <div className={cn('flex items-center min-w-0 shrink-0', !showLogoOnDesktop && 'lg:hidden')}>
          <Logo size="sm" showText={true} />
        </div>

        {/* Global Operational Context Badge */}
        <div className="flex items-center gap-1.5 sm:gap-2 px-2 sm:px-3 py-1 sm:py-1.5 rounded-lg bg-[#1C2226] border border-[#30383D] text-[11px] sm:text-xs font-mono shadow-sm shrink-0">
          <Database className="h-3.5 w-3.5 text-[#C58B3A] shrink-0" />
          <span className="text-[#9BA5A8] hidden xs:inline">Scope:</span>
          <select
            value={selectedSubsidiary}
            onChange={(e) => setSelectedSubsidiary(e.target.value)}
            className="bg-[#151A1D] border border-[#30383D] text-[#E8ECEB] font-bold rounded-md px-1 sm:px-1.5 py-0.5 focus:outline-none focus:border-[#C58B3A] text-[11px] sm:text-xs transition-colors cursor-pointer max-w-[110px] sm:max-w-none truncate"
            aria-label="Select Subsidiary Scope"
          >
            <option value="ALL CIL">ALL CIL (Corporate)</option>
            {CIL_SUBSIDIARIES.filter((s) => s.value !== 'ALL').map((sub) => (
              <option key={sub.value} value={sub.value}>
                {sub.value}
              </option>
            ))}
          </select>
          <span className="text-[#30383D] hidden md:inline">|</span>
          <span className="text-[#C58B3A] font-semibold hidden md:inline">{selectedFiscalYear}</span>
        </div>
      </div>

      {/* Center Search Affordance */}
      <form onSubmit={handleSearchSubmit} className="hidden lg:flex w-56 xl:w-80 relative items-center">
        <Input
          ref={searchInputRef}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search mining metrics, documents..."
          leftIcon={<Search className="h-4 w-4 text-[#9BA5A8]" />}
          className="bg-[#151A1D] border-[#30383D] text-[#E8ECEB] placeholder:text-[#9BA5A8]/70 text-xs py-2 pr-12 focus:border-[#C58B3A]"
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none hidden xl:block">
          <kbd className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#242C30] border border-[#30383D] text-[#9BA5A8]">
            Ctrl K
          </kbd>
        </div>
      </form>

      {/* Right User & System Status */}
      <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
        {/* System Health / Status Indicator */}
        <div className="hidden 2xl:flex items-center gap-2 px-2.5 py-1 rounded-md bg-[#242C30]/50 border border-[#30383D] text-[11px] font-mono text-[#9BA5A8]">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#4F8A62] opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#4F8A62]" />
          </span>
          <span>Live Platform</span>
        </div>

        <Badge variant="amber" size="sm" className="hidden xl:inline-flex gap-1 items-center">
          <Shield className="h-3 w-3" />
          <span>{userRole}</span>
        </Badge>

        <button
          className="relative p-2 rounded-lg bg-[#1C2226] border border-[#30383D] text-[#9BA5A8] hover:text-[#E8ECEB] transition-colors"
          title="Notifications"
          aria-label="View notifications"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-[#C58B3A]" />
        </button>

        <div className="h-8 w-px bg-[#30383D] mx-0.5 hidden sm:block" />

        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-[#242C30] border border-[#30383D] text-[#C58B3A] font-bold flex items-center justify-center text-xs shrink-0">
            {userName ? userName.charAt(0) : 'U'}
          </div>
          <div className="hidden xl:flex flex-col text-left">
            <span className="text-xs font-semibold text-[#E8ECEB] leading-none">{userName}</span>
            <span className="text-[10px] text-[#9BA5A8] font-mono mt-0.5">Connected</span>
          </div>
        </div>
      </div>
    </header>
  );
};
