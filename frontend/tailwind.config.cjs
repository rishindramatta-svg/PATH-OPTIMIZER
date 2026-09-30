/** Design tokens sampled from the supplied PNG references. */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#F8FAFC', surface: '#FFFFFF', ink: '#0F172A', body: '#334155', muted: '#94A3B8', line: '#E2E8F0',
        brand: { DEFAULT: '#4338CA', soft: '#EEF2FF', deep: '#3730A3' },
        mastery: { DEFAULT: '#14B8A6', soft: '#F0FDFA' },
        danger: { DEFAULT: '#E11D48', soft: '#FFF1F2' },
        warning: { DEFAULT: '#D97706', soft: '#FEF3C7' },
        violet: { DEFAULT: '#8B5CF6', soft: '#F5F3FF' },
      },
      fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'] },
      borderRadius: { card: '20px', panel: '16px', control: '12px', tag: '7px', pill: '9999px' },
      boxShadow: { card: '0 2px 8px rgba(15, 23, 42, .04)', raised: '0 12px 28px rgba(15, 23, 42, .07)' },
      spacing: { 4.5: '1.125rem', 5.5: '1.375rem', 7.5: '1.875rem', 13: '3.25rem', 15: '3.75rem' },
    },
  },
  plugins: [],
};

