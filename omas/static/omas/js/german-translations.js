/**
 * German-English Translation System for Omas Coffee
 * Provides hover tooltips for German terms throughout the site
 */

(function() {
    'use strict';

    // Translation dictionary - German term to English meaning
    const translations = {
        // Main phrases
        'Mit Erinnerung Gebraut': 'Brewed with Memory',
        'Omas': 'Grandma\'s',

        // Coffee culture terms
        'Kaffeezeit': 'Coffee Time - The traditional German afternoon coffee break, typically at 3 PM',
        'Gemütlichkeit': 'A feeling of warmth, coziness, belonging, and contentment',

        // Food terms
        'Streuselkuchen': 'Crumb Cake - A traditional German cake with a crumbly topping',

        // Additional phrases
        'Kaffee ist nicht nur ein Getränk': 'Coffee is not just a drink',
        'sondern eine Lebensart': 'but a way of life',

        // Single words that might appear
        'Oma': 'Grandma',
        'Kaffee': 'Coffee',
        'Getränk': 'Drink',
        'Lebensart': 'Way of life',
        'Erinnerung': 'Memory',
        'Gebraut': 'Brewed'
    };

    // Case-insensitive lookup function
    function getTranslation(term) {
        // Try exact match first
        if (translations[term]) {
            return translations[term];
        }

        // Try case-insensitive match
        const lowerTerm = term.toLowerCase();
        for (const [key, value] of Object.entries(translations)) {
            if (key.toLowerCase() === lowerTerm) {
                return value;
            }
        }

        return null;
    }

    // Create tooltip element
    let tooltip = null;

    function createTooltip() {
        if (tooltip) return tooltip;

        tooltip = document.createElement('div');
        tooltip.className = 'german-tooltip';
        tooltip.style.position = 'absolute';
        tooltip.style.display = 'none';
        tooltip.style.zIndex = '10000';
        document.body.appendChild(tooltip);

        return tooltip;
    }

    // Position tooltip near element
    function positionTooltip(element, tooltipEl) {
        const rect = element.getBoundingClientRect();
        const tooltipRect = tooltipEl.getBoundingClientRect();

        // Calculate position
        let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
        let top = rect.top - tooltipRect.height - 10;

        // Adjust if tooltip goes off screen
        if (left < 10) {
            left = 10;
        } else if (left + tooltipRect.width > window.innerWidth - 10) {
            left = window.innerWidth - tooltipRect.width - 10;
        }

        // If tooltip would appear above viewport, show below instead
        if (top < 10) {
            top = rect.bottom + 10;
            tooltipEl.classList.add('tooltip-below');
        } else {
            tooltipEl.classList.remove('tooltip-below');
        }

        tooltipEl.style.left = left + window.scrollX + 'px';
        tooltipEl.style.top = top + window.scrollY + 'px';
    }

    // Show tooltip
    function showTooltip(element, translation) {
        const tooltipEl = createTooltip();

        // Set content with both German and English
        const germanText = element.getAttribute('data-german') || element.textContent.trim();
        // Escape HTML to prevent XSS
        const escapeHtml = (text) => {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        };
        tooltipEl.innerHTML = `
            <div class="tooltip-german">${escapeHtml(germanText)}</div>
            <div class="tooltip-english">${escapeHtml(translation)}</div>
        `;

        // Show and position
        tooltipEl.style.display = 'block';
        positionTooltip(element, tooltipEl);

        // Add active class for animation
        setTimeout(() => tooltipEl.classList.add('active'), 10);
    }

    // Hide tooltip
    function hideTooltip() {
        if (tooltip) {
            tooltip.classList.remove('active');
            setTimeout(() => {
                if (tooltip) {
                    tooltip.style.display = 'none';
                }
            }, 200);
        }
    }

    // Process element to add translation capability
    function processElement(element) {
        // Skip if already processed
        if (element.hasAttribute('data-translation-processed')) {
            return;
        }

        const text = element.textContent.trim();
        const translation = element.getAttribute('data-translation') || getTranslation(text);

        if (translation) {
            // Mark as translatable
            element.classList.add('translatable-german');
            element.setAttribute('data-translation-processed', 'true');

            // Store original German if not already stored
            if (!element.hasAttribute('data-german')) {
                element.setAttribute('data-german', text);
            }

            // Add hover events
            element.addEventListener('mouseenter', function() {
                showTooltip(element, translation);
            });

            element.addEventListener('mouseleave', function() {
                hideTooltip();
            });

            // Touch support for mobile
            element.addEventListener('touchstart', function(e) {
                e.preventDefault();
                showTooltip(element, translation);

                // Auto-hide after 3 seconds
                setTimeout(hideTooltip, 3000);
            });
        }
    }

    // Scan document for German text
    function scanForGermanText() {
        // Look for elements with data-german attribute
        document.querySelectorAll('[data-german]').forEach(processElement);

        // Look for specific German terms in text
        const walker = document.createTreeWalker(
            document.body,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode: function(node) {
                    // Skip script and style elements
                    const parent = node.parentElement;
                    if (parent && (parent.tagName === 'SCRIPT' || parent.tagName === 'STYLE')) {
                        return NodeFilter.FILTER_REJECT;
                    }

                    // Skip already processed elements
                    if (parent && parent.hasAttribute('data-translation-processed')) {
                        return NodeFilter.FILTER_REJECT;
                    }

                    // Check if text contains German terms
                    const text = node.textContent.trim();
                    if (text && getTranslation(text)) {
                        return NodeFilter.FILTER_ACCEPT;
                    }

                    return NodeFilter.FILTER_REJECT;
                }
            }
        );

        const nodesToProcess = [];
        while (walker.nextNode()) {
            nodesToProcess.push(walker.currentNode);
        }

        // Wrap German terms in spans for hover functionality
        nodesToProcess.forEach(node => {
            const text = node.textContent.trim();
            const translation = getTranslation(text);

            if (translation && node.parentElement) {
                const span = document.createElement('span');
                span.textContent = text;
                span.className = 'german-term';
                span.setAttribute('data-german', text);
                span.setAttribute('data-translation', translation);

                // Replace text node with span
                node.parentElement.insertBefore(span, node);
                node.parentElement.removeChild(node);

                // Process the new span
                processElement(span);
            }
        });
    }

    // Initialize when DOM is ready
    function init() {
        scanForGermanText();

        // Hide tooltip when clicking anywhere
        document.addEventListener('click', function(e) {
            if (!e.target.classList.contains('translatable-german') &&
                !e.target.classList.contains('german-term')) {
                hideTooltip();
            }
        });

        // Hide tooltip on scroll
        let scrollTimeout;
        window.addEventListener('scroll', function() {
            hideTooltip();
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                // Re-position if tooltip is visible
                if (tooltip && tooltip.style.display === 'block') {
                    const activeElement = document.querySelector('.translatable-german:hover, .german-term:hover');
                    if (activeElement) {
                        const translation = activeElement.getAttribute('data-translation') ||
                                          getTranslation(activeElement.textContent.trim());
                        if (translation) {
                            positionTooltip(activeElement, tooltip);
                        }
                    }
                }
            }, 100);
        });
    }

    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
