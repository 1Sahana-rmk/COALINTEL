import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { AppShell } from './components/layout/AppShell';
import { ProtectedRoute } from './components/layout/ProtectedRoute';

import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { DocumentDetailPage } from './pages/DocumentDetailPage';
import { QueryAssistantPage } from './pages/QueryAssistantPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { ValidationPage } from './pages/ValidationPage';
import { ConflictResolverPage } from './pages/ConflictResolverPage';
import { ReportWizardPage } from './pages/ReportWizardPage';
import { AuditLogsPage } from './pages/AuditLogsPage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            {/* Public Login Route */}
            <Route path="/login" element={<LoginPage />} />

            {/* Authenticated Protected Shell Routes */}
            <Route
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/documents" element={<DocumentsPage />} />
              <Route path="/documents/:id" element={<DocumentDetailPage />} />
              <Route path="/query" element={<QueryAssistantPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/validation" element={<ValidationPage />} />
              <Route
                path="/conflicts"
                element={
                  <ProtectedRoute allowedRoles={['Admin', 'Reviewer']}>
                    <ConflictResolverPage />
                  </ProtectedRoute>
                }
              />
              <Route path="/reports" element={<ReportWizardPage />} />
              <Route
                path="/audit"
                element={
                  <ProtectedRoute allowedRoles={['Admin']}>
                    <AuditLogsPage />
                  </ProtectedRoute>
                }
              />
            </Route>

            {/* Default Fallback */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
