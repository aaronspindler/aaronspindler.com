// Optimized base.js with critical functionality only
(() => {
    'use strict';
    
    // Service worker cleanup (one-time operation)
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.getRegistrations().then(regs => {
            regs.forEach(reg => reg.unregister());
        });
    }
    
    // Performance optimization utilities
    const perf = {
        // Debounce function for event handlers
        debounce(func, wait) {
            let timeout;
            return function(...args) {
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(this, args), wait);
            };
        },
        
        // Throttle function for scroll/resize events
        throttle(func, limit) {
            let inThrottle;
            return function(...args) {
                if (!inThrottle) {
                    func.apply(this, args);
                    inThrottle = true;
                    setTimeout(() => inThrottle = false, limit);
                }
            };
        }
    };
    
    // Lazy loading with Intersection Observer
    const lazyLoad = () => {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                        }
                        if (img.dataset.srcset) {
                            img.srcset = img.dataset.srcset;
                            img.removeAttribute('data-srcset');
                        }
                        img.classList.add('loaded');
                        observer.unobserve(img);
                    }
                });
            }, {
                rootMargin: '50px 0px',
                threshold: 0.01
            });
            
            // Observe all lazy images
            document.querySelectorAll('img[data-src], img[data-srcset]').forEach(img => {
                imageObserver.observe(img);
            });
        } else {
            // Fallback for older browsers
            document.querySelectorAll('img[data-src]').forEach(img => {
                if (img.dataset.src) img.src = img.dataset.src;
            });
        }
    };
    
    // Smart prefetching with resource hints
    const smartPrefetch = () => {
        if ('requestIdleCallback' in window) {
            const prefetched = new Set();
            const prefetchLink = (href) => {
                if (prefetched.has(href)) return;
                
                const link = document.createElement('link');
                link.rel = 'prefetch';
                link.href = href;
                link.as = 'document';
                document.head.appendChild(link);
                prefetched.add(href);
            };
            
            // Prefetch on hover with idle callback
            document.querySelectorAll('a[href^="/"]').forEach(link => {
                link.addEventListener('mouseenter', () => {
                    requestIdleCallback(() => {
                        const href = link.getAttribute('href');
                        if (href && href !== window.location.pathname) {
                            prefetchLink(href);
                        }
                    }, { timeout: 500 });
                }, { passive: true });
            });
        }
    };
    
    // Font loading optimization
    const optimizeFonts = () => {
        if (document.fonts?.ready) {
            document.fonts.ready.then(() => {
                document.documentElement.classList.add('fonts-loaded');
            });
        }
    };
    
    // Main initialization
    const init = () => {
        // Run critical optimizations
        lazyLoad();
        smartPrefetch();
        optimizeFonts();
        
        // Add print styles
        const style = document.createElement('style');
        style.textContent = '@media print{.header,.footer,.tree{display:none!important}body{max-width:100%!important}a{text-decoration:none!important;color:#000!important}}';
        document.head.appendChild(style);
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { passive: true });
    } else {
        init();
    }
    
    // Export utilities for use by other scripts
    window.perfUtils = perf;
})();