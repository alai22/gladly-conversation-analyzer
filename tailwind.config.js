/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        halo: {
          black: '#000000',
          white: '#FFFFFF',
          yellow: {
            DEFAULT: '#FFDD00',
            dark: '#E6C700',
            light: '#FFF8CC',
          },
          blue: {
            DEFAULT: '#0066FF',
            dark: '#0052CC',
            light: '#E6F0FF',
          },
        },
        primary: {
          50: '#FFF8CC',
          100: '#FFF3A3',
          200: '#FFEB66',
          300: '#FFE333',
          400: '#FFDD00',
          500: '#FFDD00',
          600: '#E6C700',
          700: '#CCB300',
          800: '#B39E00',
          900: '#998A00',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      }
    },
  },
  plugins: [],
}

