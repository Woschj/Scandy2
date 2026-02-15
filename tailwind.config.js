module.exports = {
    content: [
        "./app/templates/**/*.html",
        "./app/static/js/**/*.js"
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
            },
            animation: {
                'ping-slow': 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
            }
        }
    },
    plugins: [require("daisyui")],
    daisyui: {
        themes: [{
            "scandy": {
                "primary": "#4f46e5",      // Indigo 600
                "primary-content": "#ffffff",
                "secondary": "#64748b",    // Slate 500
                "secondary-content": "#ffffff",
                "accent": "#f59e0b",       // Amber 500
                "accent-content": "#ffffff",
                "neutral": "#0f172a",      // Slate 900
                "neutral-content": "#ffffff",
                "base-100": "#ffffff",     // White
                "base-200": "#f8fafc",     // Slate 50
                "base-300": "#f1f5f9",     // Slate 100
                "base-content": "#0f172a", // Slate 900
                "info": "#0ea5e9",
                "success": "#10b981",
                "warning": "#f59e0b",
                "error": "#ef4444",
                "--rounded-box": "1rem",
                "--rounded-btn": "0.5rem",
                "--rounded-badge": "1.9rem",
                "--animation-btn": "0.25s",
                "--animation-input": "0.2s",
                "--btn-focus-scale": "0.95",
                "--border-btn": "1px",
                "--tab-radius": "0.5rem",
            }
        }],
    }
}
