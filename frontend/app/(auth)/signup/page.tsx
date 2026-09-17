'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Logo } from '@/components/ui/Logo';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ErrorState } from '@/components/ui/ErrorState';
import { authApi } from '@/lib/api/authApi';
import { ShieldCheck, Lock, User, Mail, Building2, Sparkles } from 'lucide-react';

const SUBSIDIARIES = [
  'CIL HQ',
  'ECL',
  'BCCL',
  'CCL',
  'WCL',
  'SECL',
  'MCL',
  'NCL',
  'NEC',
  'CMPDI',
];

export default function SignupPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [subsidiary, setSubsidiary] = useState('CIL HQ');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!username.trim() || username.trim().length < 3) {
      setError('Username must be at least 3 characters.');
      return;
    }

    if (!password || password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setIsLoading(true);

    try {
      const data = await authApi.signup({
        username: username.trim(),
        password,
        full_name: fullName.trim() || undefined,
        email: email.trim() || undefined,
        subsidiary,
      });

      if (typeof window !== 'undefined') {
        localStorage.setItem('coalintel_token', data.access_token);
        localStorage.setItem('coalintel_user', JSON.stringify(data.user));
      }

      router.push('/dashboard');
    } catch (err: any) {
      console.error('Signup error:', err);
      const detail =
        err.response?.data?.detail || 'Failed to create account. Please check your details.';
      setError(detail);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0E1113] flex flex-col lg:flex-row relative overflow-hidden font-sans select-none">
      {/* Brand & Storytelling Panel */}
      <div className="relative flex-1 flex flex-col justify-between p-6 sm:p-8 lg:p-16 z-10 bg-[#151A1D] border-b lg:border-b-0 lg:border-r border-[#30383D] order-2 lg:order-1">
        <div>
          <Logo size="lg" />

          <div className="mt-8 lg:mt-12 space-y-4 lg:space-y-6 max-w-xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-[#C58B3A]/15 border border-[#C58B3A]/30 text-[#C58B3A] text-xs font-mono">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Analyst Self-Registration</span>
            </div>

            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-[#E8ECEB] font-sans leading-tight">
              Join the <span className="text-[#C58B3A]">COALINTEL</span> Operational Platform
            </h1>

            <p className="text-xs sm:text-sm text-[#9BA5A8] leading-relaxed">
              Create an analyst profile to upload geological reports, explore unit-normalized mine production data,
              run cross-document validation queries, and synthesize institutional reports.
            </p>

            <div className="p-4 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-[#E8ECEB]">Role Attribution</span>
                <Badge variant="success" size="sm">Analyst (Standard)</Badge>
              </div>

              <p className="text-[11px] text-[#9BA5A8]">
                Public registrations are granted safe, non-privileged Analyst workspace access. Privileged Admin and Reviewer roles require internal administrative elevation.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 lg:mt-8 pt-4 lg:pt-6 border-t border-[#30383D] text-xs text-[#9BA5A8] font-mono">
          Ministry of Coal • Coal India Limited (CIL) • CMPDI Technical Platform
        </div>
      </div>

      {/* Registration Form Panel */}
      <div className="relative flex-1 flex items-center justify-center p-4 sm:p-6 lg:p-12 z-10 bg-[#0E1113] order-1 lg:order-2 overflow-y-auto">
        <div className="w-full max-w-md space-y-6 p-8 rounded-lg bg-[#1C2226] border border-[#30383D] shadow-sm">
          <div className="space-y-1.5 text-center sm:text-left">
            <h2 className="text-2xl font-bold tracking-tight text-[#E8ECEB]">Create Analyst Account</h2>
            <p className="text-xs text-[#9BA5A8]">
              Enter your details to register for platform access.
            </p>
          </div>

          {error && <ErrorState message={error} />}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Username"
              type="text"
              placeholder="e.g. j_doe"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              leftIcon={<User className="h-4 w-4 text-[#9BA5A8]" />}
              required
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Input
                label="Full Name"
                type="text"
                placeholder="e.g. John Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />

              <Input
                label="Email"
                type="email"
                placeholder="e.g. analyst@cil.in"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                leftIcon={<Mail className="h-4 w-4 text-[#9BA5A8]" />}
              />
            </div>

            {/* Subsidiary Dropdown */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-[#E8ECEB] flex items-center gap-1.5">
                <Building2 className="h-3.5 w-3.5 text-[#9BA5A8]" />
                <span>Subsidiary / Division</span>
              </label>
              <select
                value={subsidiary}
                onChange={(e) => setSubsidiary(e.target.value)}
                className="w-full bg-[#151A1D] border border-[#30383D] rounded-md px-3 py-2 text-xs text-[#E8ECEB] focus:outline-none focus:border-[#C58B3A]"
              >
                {SUBSIDIARIES.map((sub) => (
                  <option key={sub} value={sub} className="bg-[#1C2226] text-[#E8ECEB]">
                    {sub}
                  </option>
                ))}
              </select>
            </div>

            <Input
              label="Password"
              type="password"
              placeholder="Minimum 6 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              leftIcon={<Lock className="h-4 w-4 text-[#9BA5A8]" />}
              required
            />

            <Input
              label="Confirm Password"
              type="password"
              placeholder="Re-enter password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              leftIcon={<Lock className="h-4 w-4 text-[#9BA5A8]" />}
              required
            />

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full mt-2"
              isLoading={isLoading}
              rightIcon={<ShieldCheck className="h-4 w-4" />}
            >
              Register & Access Platform
            </Button>
          </form>

          <div className="pt-4 border-t border-[#30383D] text-center text-xs text-[#9BA5A8]">
            <span>Already signed up? </span>
            <Link
              href="/login"
              className="text-[#C58B3A] hover:text-[#D6A052] font-semibold underline underline-offset-2 ml-1"
            >
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
