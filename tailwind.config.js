module.exports = {
    content: [
        "./app/templates/**/*.html",
        "./app/static/js/**/*.js"
    ],
    theme: {
        extend: {
            animation: {
                'ping-slow': 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
            }
        }
    },
    plugins: [require("daisyui")],
    daisyui: {
        themes: [{
            "scandy": {
                "primary": "#004d99",      // NetBox Blue
                "primary-content": "#ffffff",
                "secondary": "#6c757d",    // Gray
                "secondary-content": "#ffffff",
                "accent": "#ffc107",       // Warning/Yellow
                "accent-content": "#2b333d",
                "neutral": "#2b333d",      // NetBox Dark Sidebar color
                "neutral-content": "#ffffff",
                "base-100": "#ffffff",     // White
                "base-200": "#f5f8fa",     // NetBox background
                "base-300": "#e9ecef",     // Light gray borders
                "base-content": "#333333", // Dark text
                "info": "#17a2b8",
                "success": "#28a745",
                "warning": "#ffc107",
                "error": "#dc3545",
            }
        }],
    }
}
