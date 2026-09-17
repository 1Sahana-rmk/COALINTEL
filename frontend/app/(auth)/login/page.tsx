'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Logo } from '@/components/ui/Logo';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { authApi } from '@/lib/api/authApi';
import { ShieldCheck, Lock, User, Sparkles, Database, FileSpreadsheet } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('Please enter your authorized username and password.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await authApi.login(username, password);
      if (typeof window !== 'undefined') {
        localStorage.setItem('coalintel_token', data.access_token);
        localStorage.setItem('coalintel_user', JSON.stringify(data.user));
      }
      router.push('/dashboard');
    } catch (err: any) {
      console.error('Login error:', err);
      const detail =
        err.response?.data?.detail || 'Authentication failed. Invalid username or password.';
      setError(detail);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickLogin = async (role: 'admin' | 'analyst') => {
    setIsLoading(true);
    setError(null);
    const creds =
      role === 'admin'
        ? { username: 'admin', password: 'Admin@123' }
        : { username: 'analyst', password: 'Analyst@123' };

    setUsername(creds.username);
    setPassword(creds.password);

    try {
      const data = await authApi.login(creds.username, creds.password);
      if (typeof window !== 'undefined') {
        localStorage.setItem('coalintel_token', data.access_token);
        localStorage.setItem('coalintel_user', JSON.stringify(data.user));
      }
      router.push('/dashboard');
    } catch (err: any) {
      console.error('Quick login error:', err);
      const detail =
        err.response?.data?.detail || 'Authentication failed. Please verify credentials.';
      setError(detail);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0E1113] flex flex-col lg:flex-row relative overflow-hidden font-sans select-none">
      {/* Institutional Brand & Operational Storytelling */}
      <div className="relative flex-1 flex flex-col justify-between p-6 sm:p-8 lg:p-16 z-10 bg-[#151A1D] border-b lg:border-b-0 lg:border-r border-[#30383D] order-2 lg:order-1">
        <div>
          <Logo size="lg" />

          <div className="mt-8 lg:mt-12 space-y-4 lg:space-y-6 max-w-xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-[#C58B3A]/15 border border-[#C58B3A]/30 text-[#C58B3A] text-xs font-mono">
              <Sparkles className="h-3.5 w-3.5" />
              <span>SIH26023 Enterprise Platform</span>
            </div>

            <h1 className="text-2xl sm:text-3xl lg:text-5xl font-extrabold tracking-tight text-[#E8ECEB] font-sans leading-tight">
              AI-Powered Evidence-Driven <span className="text-[#C58B3A]">Mining Intelligence</span> & Reporting
            </h1>

            <p className="text-xs sm:text-sm lg:text-base text-[#9BA5A8] leading-relaxed">
              Automated geological and production document processing, unit-normalized extraction,
              arithmetic validation, and institutional parliamentary report generation for Coal India Limited and CMPDI.
            </p>
          </div>
        </div>

        {/* Operational Feature Cards */}
        <div className="hidden sm:grid grid-cols-1 md:grid-cols-3 gap-4 mt-8 lg:mt-12">
          <div className="p-4 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-2">
            <div className="p-2 rounded-lg bg-[#242C30] text-[#C58B3A] w-fit">
              <Database className="h-4 w-4" />
            </div>
            <h4 className="text-xs font-semibold text-[#E8ECEB]">Structured Data Mining</h4>
            <p className="text-[11px] text-[#9BA5A8]">Automated extraction from PDF, DOCX, XLSX annual reports.</p>
          </div>

          <div className="p-4 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-2">
            <div className="p-2 rounded-lg bg-[#242C30] text-[#4F8A62] w-fit">
              <ShieldCheck className="h-4 w-4" />
            </div>
            <h4 className="text-xs font-semibold text-[#E8ECEB]">Validation & Grounding</h4>
            <p className="text-[11px] text-[#9BA5A8]">5% arithmetic checks & 1% cross-document conflict detection.</p>
          </div>

          <div className="p-4 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-2">
            <div className="p-2 rounded-lg bg-[#242C30] text-[#54788A] w-fit">
              <FileSpreadsheet className="h-4 w-4" />
            </div>
            <h4 className="text-xs font-semibold text-[#E8ECEB]">ReportLab Wizard</h4>
            <p className="text-[11px] text-[#9BA5A8]">Instant PDF synthesis for Ministry & CIL HQ disclosures.</p>
          </div>
        </div>

        <div className="mt-6 lg:mt-8 pt-4 lg:pt-6 border-t border-[#30383D] text-xs text-[#9BA5A8] font-mono">
          Ministry of Coal • Coal India Limited (CIL) • CMPDI Technical Platform
        </div>
      </div>

      {/* Authentication Panel */}
      <div className="relative flex-1 flex items-center justify-center p-4 sm:p-6 lg:p-16 z-10 bg-[#0E1113] order-1 lg:order-2">
        <div className="w-full max-w-md space-y-8 p-8 rounded-lg bg-[#1C2226] border border-[#30383D] shadow-sm">
          <div className="space-y-2 text-center sm:text-left">
            <h2 className="text-2xl font-bold tracking-tight text-[#E8ECEB]">Sign in to Platform</h2>
            <p className="text-xs text-[#9BA5A8]">
              Enter your authorized operational credentials to access COALINTEL V2.
            </p>
          </div>

          {error && <ErrorState message={error} />}

          {/* Role Selection Helpers / Demo Quick Login Shortcuts */}
          <div className="space-y-2">
            <span className="text-[11px] uppercase tracking-wider text-[#9BA5A8] font-mono block">
              Predefined Demo Shortcuts
            </span>
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={isLoading}
                onClick={() => handleQuickLogin('admin')}
                className="text-xs border-[#C58B3A]/60 text-[#C58B3A] hover:bg-[#C58B3A]/10"
              >
                Admin Login
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={isLoading}
                onClick={() => handleQuickLogin('analyst')}
                className="text-xs border-[#4F8A62]/60 text-[#4F8A62] hover:bg-[#4F8A62]/10"
              >
                Analyst Login
              </Button>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <Input
              label="Username"
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              leftIcon={<User className="h-4 w-4 text-[#9BA5A8]" />}
              required
            />

            <Input
              label="Password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              leftIcon={<Lock className="h-4 w-4 text-[#9BA5A8]" />}
              required
            />

            <div className="flex items-center justify-between text-xs text-[#9BA5A8] pt-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  className="rounded bg-[#151A1D] border-[#30383D] text-[#C58B3A] focus:ring-[#C58B3A]"
                />
                <span>Remember session</span>
              </label>

              <span className="text-[#9BA5A8] cursor-not-allowed" title="Contact System Administrator for credential resets">
                Forgot password?
              </span>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full"
              isLoading={isLoading}
              rightIcon={<ShieldCheck className="h-4 w-4" />}
            >
              Authenticate & Access Platform
            </Button>
          </form>

          {/* Institutional Access & Signup Link */}
          <div className="pt-4 border-t border-[#30383D] text-center text-xs text-[#9BA5A8]">
            <span>Don&apos;t have an account? </span>
            <Link
              href="/signup"
              className="text-[#C58B3A] hover:text-[#D6A052] font-semibold underline underline-offset-2 ml-1"
            >
              Sign up
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

