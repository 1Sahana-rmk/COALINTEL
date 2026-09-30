'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { ALL_FISCAL_YEARS_VALUE } from '@/lib/constants';

interface ScopeContextType {
  selectedSubsidiary: string;
  setSelectedSubsidiary: (subsidiary: string) => void;
  selectedFiscalYear: string;
  setSelectedFiscalYear: (fiscalYear: string) => void;
}

const ScopeContext = createContext<ScopeContextType | undefined>(undefined);

export const ScopeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedSubsidiary, setSelectedSubsidiaryState] = useState<string>('ALL');
  const [selectedFiscalYear, setSelectedFiscalYearState] = useState<string>(ALL_FISCAL_YEARS_VALUE);

  // Load initial scope state from localStorage on client-side mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedSub = localStorage.getItem('coalintel_selected_subsidiary');
      if (storedSub) {
        setSelectedSubsidiaryState(storedSub === 'ALL CIL' ? 'ALL' : storedSub);
      }
      const storedFy = localStorage.getItem('coalintel_selected_fiscal_year');
      if (storedFy) {
        setSelectedFiscalYearState(storedFy);
      }
    }
  }, []);

  const setSelectedSubsidiary = (subsidiary: string) => {
    setSelectedSubsidiaryState(subsidiary);
    if (typeof window !== 'undefined') {
      localStorage.setItem('coalintel_selected_subsidiary', subsidiary);
    }
  };

  const setSelectedFiscalYear = (fiscalYear: string) => {
    setSelectedFiscalYearState(fiscalYear);
    if (typeof window !== 'undefined') {
      localStorage.setItem('coalintel_selected_fiscal_year', fiscalYear);
    }
  };

  return (
    <ScopeContext.Provider
      value={{
        selectedSubsidiary,
        setSelectedSubsidiary,
        selectedFiscalYear,
        setSelectedFiscalYear,
      }}
    >
      {children}
    </ScopeContext.Provider>
  );
};

export const useScope = (): ScopeContextType => {
  const context = useContext(ScopeContext);
  if (!context) {
    throw new Error('useScope must be used within a ScopeProvider');
  }
  return context;
};
