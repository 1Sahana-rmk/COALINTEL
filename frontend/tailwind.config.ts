import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // COALINTEL — Professional Industrial UI Palette
        mine: {
          bg: '#0E1113',      // Primary Background
          sidebar: '#151A1D', // Sidebar / Navigation
          card: '#1C2226',    // Dashboard Cards / Flat surfaces
          hover: '#242C30',   // Card Hover / Elevated surfaces
          border: '#30383D',  // Thin 1px borders
        },
        industrial: {
          text: '#E8ECEB',       // Primary Text / Main headings
          muted: '#9BA5A8',      // Secondary Text / Descriptions
        },

        // Structure & Surfaces (with backwards-compatible aliases)
        coal: {
          50: '#E8ECEB',
          100: '#9BA5A8',
          700: '#30383D', // Borders
          800: '#242C30', // Card hover / Elevated surface
          850: '#1C2226', // Cards
          900: '#151A1D', // Sidebar / Navigation
          950: '#0E1113', // Primary background
          DEFAULT: '#0E1113',
        },
        ash: {
          DEFAULT: '#0E1113',
          50: '#151A1D',
          100: '#1C2226',
          200: '#242C30',
          300: '#30383D',
        },
        surface: {
          DEFAULT: '#1C2226', // Cards
          dark: '#151A1D',    // Sidebar
          elevated: '#242C30', // Card hover
        },
        steel: {
          DEFAULT: '#30383D', // Borders
          100: '#151A1D',
          200: '#1C2226',
          300: '#242C30',
          400: '#30383D',
          500: '#9BA5A8',
        },

        // Primary Brand / Accent: #C58B3A (Hover: #D6A052)
        amber: {
          DEFAULT: '#C58B3A', // Primary Brand / Accent
          hover: '#D6A052',   // Accent Hover
          300: '#E4B774',
          400: '#D6A052',
          500: '#C58B3A',
          600: '#B0782C',
          700: '#8A5D20',
          900: '#2E2214',
        },
        brand: {
          DEFAULT: '#C58B3A',
          hover: '#D6A052',
          50: '#FAF4EB',
          100: '#F2E4CF',
          300: '#E4B774',
          400: '#D6A052',
          500: '#C58B3A',
          600: '#B0782C',
          900: '#151A1D',
        },
        gold: {
          DEFAULT: '#C58B3A',
          400: '#D6A052',
          500: '#C58B3A',
          600: '#B0782C',
          900: '#2E2214',
        },

        // Secondary Charts & Technical Info: #54788A
        info: {
          DEFAULT: '#54788A',
          400: '#688FA3',
          500: '#54788A',
          600: '#436170',
          900: '#142026',
        },
        teal: {
          DEFAULT: '#54788A', // Mapped to industrial info slate
          50: '#F0F5F7',
          100: '#DCE8EE',
          200: '#B5CDD8',
          300: '#688FA3',
          400: '#54788A',
          500: '#54788A',
          600: '#436170',
          700: '#344B57',
          800: '#22323A',
          900: '#142026',
        },

        // Positive Metrics / Success: #4F8A62
        success: {
          DEFAULT: '#4F8A62',
          400: '#62A578',
          500: '#4F8A62',
          600: '#3E6F4E',
          900: '#13261A',
        },
        green: {
          DEFAULT: '#4F8A62',
          400: '#62A578',
          500: '#4F8A62',
          600: '#3E6F4E',
          900: '#13261A',
        },

        // Warnings: #D6A23A
        warning: {
          DEFAULT: '#D6A23A',
          400: '#E2B558',
          500: '#D6A23A',
          600: '#BA8829',
          900: '#33240A',
        },

        // Critical Anomalies / Error: #C94B45
        danger: {
          DEFAULT: '#C94B45',
          400: '#D96660',
          500: '#C94B45',
          600: '#A93833',
          900: '#331211',
        },
        error: {
          DEFAULT: '#C94B45',
          400: '#D96660',
          500: '#C94B45',
          600: '#A93833',
          900: '#331211',
        },

        // Typography Tokens
        ink: {
          DEFAULT: '#E8ECEB', // Primary text
          primary: '#E8ECEB',
          muted: '#9BA5A8',   // Secondary text
        },
        slateText: {
          DEFAULT: '#9BA5A8',
        },
        navy: {
          800: '#242C30',
          900: '#1C2226',
          950: '#151A1D',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        DEFAULT: '8px',
        sm: '4px',
        md: '6px',
        lg: '8px',
        xl: '10px',
        '2xl': '10px',
        '3xl': '10px',
      },
      boxShadow: {
        subtle: '0 1px 2px 0 rgba(0, 0, 0, 0.35)',
        card: '0 2px 4px 0 rgba(0, 0, 0, 0.3)',
        dropdown: '0 4px 12px 0 rgba(0, 0, 0, 0.45)',
        'glow-amber': '0 0 0 1px rgba(197, 139, 58, 0.35)',
        'glow-gold': '0 0 0 1px rgba(197, 139, 58, 0.35)',
        'glow-teal': '0 0 0 1px rgba(84, 120, 138, 0.35)',
        'glow-red': '0 0 0 1px rgba(201, 75, 69, 0.35)',
        'glow-emerald': '0 0 0 1px rgba(79, 138, 98, 0.35)',
        'card-light': '0 1px 3px 0 rgba(0, 0, 0, 0.3)',
        'card-dark': '0 2px 6px 0 rgba(0, 0, 0, 0.4)',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        slideInRight: {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
      },
      animation: {
        'fade-in': 'fadeIn 200ms ease-out forwards',
        'slide-up': 'slideUp 250ms ease-out forwards',
        'slide-in-right': 'slideInRight 250ms cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'pulse-subtle': 'pulseSubtle 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};

export default config;
