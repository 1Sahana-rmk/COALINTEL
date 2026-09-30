'use client';

import React from 'react';
import { Globe2 } from 'lucide-react';
import { Locale } from '@/lib/i18n';
import { useLanguage } from '@/context/LanguageContext';

export const LanguageSelector: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  const { locale, setLocale, t } = useLanguage();
  return (
    <label className="inline-flex items-center gap-1.5 text-[11px] font-mono text-[#9BA5A8]">
      <Globe2 className="h-3.5 w-3.5 text-[#C58B3A]" />
      {!compact && <span>{t('language.label')}</span>}
      <select
        value={locale}
        onChange={(event) => setLocale(event.target.value as Locale)}
        aria-label={t('language.label')}
        className="rounded-md border border-[#30383D] bg-[#151A1D] px-1.5 py-1 text-[#E8ECEB] focus:outline-none focus:border-[#C58B3A]"
      >
        <option value="en">{t('language.english')}</option>
        <option value="hi">{t('language.hindi')}</option>
      </select>
    </label>
  );
};
