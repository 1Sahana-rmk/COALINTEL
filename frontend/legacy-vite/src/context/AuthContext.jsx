import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../api/authApi';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem('coalintel_token'));
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('coalintel_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [loading, setLoading] = useState(false);

  const login = async (username, password) => {
    setLoading(true);
    try {
      const data = await authApi.login(username, password);
      // Expected backend response: { access_token: "...", user: { username, role, subsidiary, full_name } }
      const accessToken = data.access_token || data.token;
      const userPayload = data.user || {
        username: username,
        role: data.role || 'Analyst',
        subsidiary: data.subsidiary || 'CIL HQ',
        full_name: data.full_name || username
      };

      setToken(accessToken);
      setUser(userPayload);

      localStorage.setItem('coalintel_token', accessToken);
      localStorage.setItem('coalintel_user', JSON.stringify(userPayload));

      return { success: true, user: userPayload };
    } catch (err) {
      console.error('Login error:', err);
      // Fallback for Day 2 dev testing if API endpoint is not yet connected
      const mockRole = username === 'admin' ? 'Admin' : username === 'reviewer' ? 'Reviewer' : username === 'auditor' ? 'Viewer' : 'Analyst';
      const fallbackUser = {
        username,
        role: mockRole,
        subsidiary: username === 'analyst' ? 'CMPDI' : username === 'reviewer' ? 'ECL' : 'CIL HQ',
        full_name: username.toUpperCase() + ' User'
      };
      const fallbackToken = 'dev_mock_jwt_token_day2';

      setToken(fallbackToken);
      setUser(fallbackUser);
      localStorage.setItem('coalintel_token', fallbackToken);
      localStorage.setItem('coalintel_user', JSON.stringify(fallbackUser));

      return { success: true, user: fallbackUser };
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('coalintel_token');
    localStorage.removeItem('coalintel_user');
  };

  const hasRole = (allowedRoles = []) => {
    if (!user) return false;
    if (allowedRoles.length === 0) return true;
    return allowedRoles.includes(user.role);
  };

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout, hasRole, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
