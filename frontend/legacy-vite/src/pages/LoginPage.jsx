import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { HardDrive, Lock, User, Building2, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Select } from '../components/common/Select';

export const LoginPage = () => {
  const navigate = useNavigate();
  const { login, loading } = useAuth();
  const { addToast } = useToast();

  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('Admin@123');
  const [subsidiary, setSubsidiary] = useState('CIL HQ');

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!username || !password) {
      addToast('Please enter both username and password.', 'warning');
      return;
    }

    const result = await login(username, password);
    if (result.success) {
      addToast(`Welcome back, ${result.user.full_name || username}!`, 'success');
      navigate('/dashboard');
    } else {
      addToast('Invalid credentials provided.', 'error');
    }
  };

  const setQuickAccount = (userRole, userPass) => {
    setUsername(userRole);
    setPassword(userPass);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Background Decorative Grids */}
      <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] opacity-40"></div>

      <div className="max-w-md w-full bg-slate-900/90 border border-slate-800 rounded-2xl shadow-2xl p-8 relative z-10 backdrop-blur-xl">
        {/* Brand Title Header */}
        <div className="text-center space-y-2 mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-amber-500/10 text-amber-500 border border-amber-500/20 mb-2">
            <HardDrive className="w-7 h-7" />
          </div>
          <h2 className="text-2xl font-bold text-white tracking-wider">COALINTEL</h2>
          <p className="text-xs text-slate-400">
            AI-Powered Evidence-Driven Mining Intelligence Platform
          </p>
          <div className="inline-block px-3 py-1 bg-slate-800 text-slate-300 text-[10px] font-semibold rounded-full border border-slate-700">
            Ministry of Coal • SIH26023
          </div>
        </div>

        {/* Login Form */}
        <form onSubmit={handleLogin} className="space-y-5">
          <Input
            label="Username / ID"
            icon={User}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter username"
            required
          />

          <Input
            label="Password"
            type="password"
            icon={Lock}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
            required
          />

          <Select
            label="Subsidiary Context"
            value={subsidiary}
            onChange={(e) => setSubsidiary(e.target.value)}
            options={[
              { value: 'CIL HQ', label: 'Coal India Limited (CIL HQ)' },
              { value: 'CMPDI', label: 'Central Mine Planning & Design Institute (CMPDI)' },
              { value: 'ECL', label: 'Eastern Coalfields Limited (ECL)' },
              { value: 'BCCL', label: 'Bharat Coking Coal Limited (BCCL)' },
              { value: 'CCL', label: 'Central Coalfields Limited (CCL)' },
              { value: 'WCL', label: 'Western Coalfields Limited (WCL)' },
              { value: 'SECL', label: 'South Eastern Coalfields Limited (SECL)' },
              { value: 'NCL', label: 'Northern Coalfields Limited (NCL)' },
              { value: 'MCL', label: 'Mahanadi Coalfields Limited (MCL)' },
            ]}
          />

          <Button
            type="submit"
            variant="primary"
            className="w-full py-2.5 mt-2"
            isLoading={loading}
            icon={ArrowRight}
          >
            Authenticate Session
          </Button>
        </form>

        {/* Day 1 Pre-seeded Accounts Quick Test Bar */}
        <div className="mt-8 pt-6 border-t border-slate-800 text-center">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-3">
            Quick Login (Pre-Seeded RBAC Profiles)
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              type="button"
              onClick={() => setQuickAccount('admin', 'Admin@123')}
              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 text-left"
            >
              <div className="font-semibold text-amber-400">admin</div>
              <div className="text-[10px] text-slate-400">Role: Admin</div>
            </button>
            <button
              type="button"
              onClick={() => setQuickAccount('analyst', 'Analyst@123')}
              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 text-left"
            >
              <div className="font-semibold text-emerald-400">analyst</div>
              <div className="text-[10px] text-slate-400">Role: Analyst</div>
            </button>
            <button
              type="button"
              onClick={() => setQuickAccount('reviewer', 'Reviewer@123')}
              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 text-left"
            >
              <div className="font-semibold text-blue-400">reviewer</div>
              <div className="text-[10px] text-slate-400">Role: Reviewer</div>
            </button>
            <button
              type="button"
              onClick={() => setQuickAccount('auditor', 'Auditor@123')}
              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 text-left"
            >
              <div className="font-semibold text-purple-400">auditor</div>
              <div className="text-[10px] text-slate-400">Role: Viewer</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
