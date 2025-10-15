(() => {
    'use strict';

    // Theme management
    const ThemeToggle = {
        // Constants
        STORAGE_KEY: 'theme-preference',
        THEME_LIGHT: 'light',
        THEME_DARK: 'dark',
        THEME_AUTO: 'auto',

        // Initialize theme system
        init() {
            this.createToggleButton();
            this.loadTheme();
            this.bindEvents();
            this.watchSystemPreference();
        },

        // Create the toggle button dynamically
        createToggleButton() {
            // Check if button already exists
            if (document.getElementById('theme-toggle')) return;

            // Create button element
            const button = document.createElement('button');
            button.id = 'theme-toggle';
            button.className = 'theme-toggle-btn';
            button.setAttribute('role', 'switch');
            button.setAttribute('aria-checked', this.isDarkMode() ? 'true' : 'false');

            // Add transition class after initial load
            setTimeout(() => {
                button.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            }, 100);

            // Set initial icon
            this.updateButtonIcon(button);

            // Create a container for the toggle
            const toggleContainer = document.createElement('div');
            toggleContainer.className = 'theme-toggle-container';
            toggleContainer.appendChild(button);

            // Add to body for fixed positioning
            document.body.appendChild(toggleContainer);
        },

        // Update button icon based on current theme
        updateButtonIcon(button = null) {
            const btn = button || document.getElementById('theme-toggle');
            if (!btn) return;

            const currentTheme = this.getCurrentTheme();
            const isDark = currentTheme === this.THEME_DARK ||
                          (currentTheme === this.THEME_AUTO && this.prefersDark());

            // Update data attribute for CSS styling
            btn.setAttribute('data-theme', currentTheme);

            // Update button with simple text indicator
            btn.innerHTML = `<span class="theme-text"></span>`;

            // Update tooltip
            this.updateTooltip(btn, currentTheme, isDark);
        },

        // Update tooltip to show current theme
        updateTooltip(button, theme, isDark) {
            const nextTheme = theme === this.THEME_AUTO ? this.THEME_LIGHT :
                            theme === this.THEME_LIGHT ? this.THEME_DARK : this.THEME_AUTO;

            const currentMode = theme === this.THEME_AUTO ?
                              `AUTO (${isDark ? 'DARK' : 'LIGHT'})` : theme.toUpperCase();

            button.setAttribute('title', `Theme: ${currentMode} → ${nextTheme.toUpperCase()}`);
            button.setAttribute('aria-label', `Toggle theme. Current: ${currentMode}`);
        },

        // Get current theme from localStorage or system
        getCurrentTheme() {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            if (stored && [this.THEME_LIGHT, this.THEME_DARK, this.THEME_AUTO].includes(stored)) {
                return stored;
            }
            return this.THEME_AUTO;
        },

        // Set theme
        setTheme(theme) {
            // Store preference
            if (theme === this.THEME_AUTO) {
                localStorage.removeItem(this.STORAGE_KEY);
            } else {
                localStorage.setItem(this.STORAGE_KEY, theme);
            }

            // Apply theme
            this.applyTheme(theme);
            this.updateButtonIcon();
        },

        // Apply theme to document
        applyTheme(theme) {
            const root = document.documentElement;

            // Add transition class for smooth theme change
            root.classList.add('theme-transition');

            // Remove existing theme classes
            root.classList.remove('theme-light', 'theme-dark', 'theme-auto');

            if (theme === this.THEME_AUTO) {
                // Let CSS media query handle it
                root.classList.add('theme-auto');
            } else {
                // Force specific theme
                root.classList.add(`theme-${theme}`);
            }

            // Update ARIA attribute
            const button = document.getElementById('theme-toggle');
            if (button) {
                button.setAttribute('aria-checked', this.isDarkMode() ? 'true' : 'false');
            }

            // Remove transition class after animation
            setTimeout(() => {
                root.classList.remove('theme-transition');
            }, 300);

            // Dispatch custom event for other components
            window.dispatchEvent(new CustomEvent('themechange', {
                detail: { theme, isDark: this.isDarkMode() }
            }));
        },

        // Load saved theme on page load
        loadTheme() {
            const theme = this.getCurrentTheme();
            this.applyTheme(theme);
        },

        // Check if system prefers dark mode
        prefersDark() {
            return window.matchMedia &&
                   window.matchMedia('(prefers-color-scheme: dark)').matches;
        },

        // Check if currently in dark mode
        isDarkMode() {
            const theme = this.getCurrentTheme();
            return theme === this.THEME_DARK ||
                   (theme === this.THEME_AUTO && this.prefersDark());
        },

        // Toggle between themes
        toggle() {
            const current = this.getCurrentTheme();
            let next;

            // Cycle: auto -> light -> dark -> auto
            if (current === this.THEME_AUTO) {
                next = this.THEME_LIGHT;
            } else if (current === this.THEME_LIGHT) {
                next = this.THEME_DARK;
            } else {
                next = this.THEME_AUTO;
            }

            this.setTheme(next);
        },

        // Bind events
        bindEvents() {
            // Button click
            const button = document.getElementById('theme-toggle');
            if (button) {
                button.addEventListener('click', () => this.toggle());
            }

            // Keyboard shortcut (Alt+T)
            document.addEventListener('keydown', (e) => {
                if (e.altKey && e.key === 't') {
                    e.preventDefault();
                    this.toggle();
                }
            });
        },

        // Watch for system preference changes
        watchSystemPreference() {
            if (!window.matchMedia) return;

            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

            // Use addEventListener (supported in all modern browsers)
            const handleChange = () => {
                if (this.getCurrentTheme() === this.THEME_AUTO) {
                    this.applyTheme(this.THEME_AUTO);
                    this.updateButtonIcon();
                }
            };

            if (mediaQuery.addEventListener) {
                mediaQuery.addEventListener('change', handleChange);
            } else if (mediaQuery.addListener) {
                // Fallback for very old browsers (deprecated but kept for compatibility)
                mediaQuery.addListener(handleChange);
            }
        }
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => ThemeToggle.init());
    } else {
        ThemeToggle.init();
    }

    // Expose to window for debugging
    window.ThemeToggle = ThemeToggle;
})();
