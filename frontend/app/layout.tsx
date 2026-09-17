import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'COALINTEL V2 — Mining Intelligence & Reporting Platform',
  description:
    'AI-powered evidence-driven mining intelligence, automated document extraction, arithmetic validation, and institutional reporting platform for Coal India Limited (CIL) and Ministry of Coal.',
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-[#0E1113] text-[#E8ECEB] min-h-screen antialiased selection:bg-[#C58B3A]/30 selection:text-[#E8ECEB]">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
