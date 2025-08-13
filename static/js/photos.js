/**
 * Photos App - Enhanced Frontend JavaScript
 * Provides lightbox, search, and interactive features for the photo gallery
 */

(function() {
    'use strict';

    // ===========================
    // Lightbox Implementation
    // ===========================
    
    class PhotoLightbox {
        constructor() {
            this.currentIndex = 0;
            this.photos = [];
            this.touchStartX = null;
            this.touchStartY = null;
            this.init();
        }

        init() {
            this.createLightboxElements();
            this.bindEvents();
            this.collectPhotos();
        }

        createLightboxElements() {
            // Create lightbox container
            const lightbox = document.createElement('div');
            lightbox.className = 'lightbox';
            lightbox.innerHTML = `
                <div class="lightbox-overlay"></div>
                <div class="lightbox-content">
                    <button class="lightbox-close" aria-label="Close">&times;</button>
                    <button class="lightbox-prev" aria-label="Previous photo">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="15 18 9 12 15 6"></polyline>
                        </svg>
                    </button>
                    <button class="lightbox-next" aria-label="Next photo">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="9 18 15 12 9 6"></polyline>
                        </svg>
                    </button>
                    <div class="lightbox-image-container">
                        <div class="lightbox-loader">
                            <div class="spinner"></div>
                        </div>
                        <img class="lightbox-image" alt="">
                    </div>
                    <div class="lightbox-info">
                        <h3 class="lightbox-title"></h3>
                        <p class="lightbox-caption"></p>
                        <div class="lightbox-counter"></div>
                    </div>
                </div>
            `;
            document.body.appendChild(lightbox);

            // Store references
            this.lightbox = lightbox;
            this.overlay = lightbox.querySelector('.lightbox-overlay');
            this.image = lightbox.querySelector('.lightbox-image');
            this.loader = lightbox.querySelector('.lightbox-loader');
            this.closeBtn = lightbox.querySelector('.lightbox-close');
            this.prevBtn = lightbox.querySelector('.lightbox-prev');
            this.nextBtn = lightbox.querySelector('.lightbox-next');
            this.title = lightbox.querySelector('.lightbox-title');
            this.caption = lightbox.querySelector('.lightbox-caption');
            this.counter = lightbox.querySelector('.lightbox-counter');
            this.imageContainer = lightbox.querySelector('.lightbox-image-container');
        }

        collectPhotos() {
            // Collect all photos from the grid
            const photoElements = document.querySelectorAll('.photo-grid .photo-thumbnail');
            this.photos = Array.from(photoElements).map((img, index) => ({
                src: img.dataset.full || img.src,
                thumbnail: img.src,
                title: img.closest('.photo-card').querySelector('.photo-title')?.textContent || '',
                caption: img.closest('.photo-card').querySelector('.photo-caption')?.textContent || '',
                element: img,
                index: index
            }));
        }

        bindEvents() {
            // Photo click events
            document.addEventListener('click', (e) => {
                const photoThumbnail = e.target.closest('.photo-thumbnail');
                if (photoThumbnail) {
                    e.preventDefault();
                    const index = Array.from(document.querySelectorAll('.photo-thumbnail')).indexOf(photoThumbnail);
                    this.open(index);
                }
            });

            // Lightbox controls
            this.closeBtn.addEventListener('click', () => this.close());
            this.overlay.addEventListener('click', () => this.close());
            this.prevBtn.addEventListener('click', () => this.navigate(-1));
            this.nextBtn.addEventListener('click', () => this.navigate(1));

            // Keyboard navigation
            document.addEventListener('keydown', (e) => {
                if (!this.isOpen()) return;
                
                switch(e.key) {
                    case 'Escape':
                        this.close();
                        break;
                    case 'ArrowLeft':
                        this.navigate(-1);
                        break;
                    case 'ArrowRight':
                        this.navigate(1);
                        break;
                }
            });

            // Touch gestures
            this.imageContainer.addEventListener('touchstart', (e) => this.handleTouchStart(e), { passive: true });
            this.imageContainer.addEventListener('touchmove', (e) => this.handleTouchMove(e), { passive: true });
            this.imageContainer.addEventListener('touchend', (e) => this.handleTouchEnd(e), { passive: true });

            // Image load events
            this.image.addEventListener('load', () => {
                this.loader.style.display = 'none';
                this.image.style.display = 'block';
            });

            this.image.addEventListener('error', () => {
                this.loader.style.display = 'none';
                this.image.style.display = 'none';
                this.showError();
            });
        }

        handleTouchStart(e) {
            this.touchStartX = e.touches[0].clientX;
            this.touchStartY = e.touches[0].clientY;
        }

        handleTouchMove(e) {
            if (!this.touchStartX || !this.touchStartY) return;

            const touchEndX = e.touches[0].clientX;
            const touchEndY = e.touches[0].clientY;
            const deltaX = this.touchStartX - touchEndX;
            const deltaY = this.touchStartY - touchEndY;

            // Only handle horizontal swipes
            if (Math.abs(deltaX) > Math.abs(deltaY)) {
                e.preventDefault();
            }
        }

        handleTouchEnd(e) {
            if (!this.touchStartX) return;

            const touchEndX = e.changedTouches[0].clientX;
            const deltaX = this.touchStartX - touchEndX;
            const threshold = 50; // Minimum swipe distance

            if (Math.abs(deltaX) > threshold) {
                if (deltaX > 0) {
                    // Swipe left - next photo
                    this.navigate(1);
                } else {
                    // Swipe right - previous photo
                    this.navigate(-1);
                }
            }

            this.touchStartX = null;
            this.touchStartY = null;
        }

        open(index) {
            if (this.photos.length === 0) {
                this.collectPhotos();
            }

            this.currentIndex = index;
            this.lightbox.classList.add('active');
            document.body.style.overflow = 'hidden';
            this.showPhoto(index);
            this.updateNavigation();
        }

        close() {
            this.lightbox.classList.remove('active');
            document.body.style.overflow = '';
            this.image.src = '';
        }

        isOpen() {
            return this.lightbox.classList.contains('active');
        }

        navigate(direction) {
            const newIndex = this.currentIndex + direction;
            if (newIndex >= 0 && newIndex < this.photos.length) {
                this.currentIndex = newIndex;
                this.showPhoto(newIndex);
                this.updateNavigation();
            }
        }

        showPhoto(index) {
            const photo = this.photos[index];
            if (!photo) return;

            // Show loader
            this.loader.style.display = 'flex';
            this.image.style.display = 'none';

            // Update image
            this.image.src = photo.src;
            this.image.alt = photo.title || `Photo ${index + 1}`;

            // Update info
            this.title.textContent = photo.title || '';
            this.caption.textContent = photo.caption || '';
            this.counter.textContent = `${index + 1} / ${this.photos.length}`;

            // Show/hide info based on content
            const hasInfo = photo.title || photo.caption;
            this.title.style.display = photo.title ? 'block' : 'none';
            this.caption.style.display = photo.caption ? 'block' : 'none';
        }

        updateNavigation() {
            this.prevBtn.disabled = this.currentIndex === 0;
            this.nextBtn.disabled = this.currentIndex === this.photos.length - 1;
            
            this.prevBtn.style.display = this.photos.length > 1 ? 'block' : 'none';
            this.nextBtn.style.display = this.photos.length > 1 ? 'block' : 'none';
        }

        showError() {
            const errorMsg = document.createElement('div');
            errorMsg.className = 'lightbox-error';
            errorMsg.textContent = 'Failed to load image';
            this.imageContainer.appendChild(errorMsg);
            setTimeout(() => errorMsg.remove(), 3000);
        }
    }

    // ===========================
    // Album Search Functionality
    // ===========================

    class AlbumSearch {
        constructor() {
            this.searchInput = null;
            this.albums = [];
            this.init();
        }

        init() {
            if (!document.querySelector('.album-grid')) return;

            this.createSearchBar();
            this.collectAlbums();
            this.bindEvents();
        }

        createSearchBar() {
            const albumHeader = document.querySelector('.content h1');
            if (!albumHeader) return;

            const searchContainer = document.createElement('div');
            searchContainer.className = 'album-search-container';
            searchContainer.innerHTML = `
                <div class="search-wrapper">
                    <input type="text" 
                           class="album-search-input" 
                           placeholder="Search albums by title..."
                           aria-label="Search albums">
                    <button class="search-clear" aria-label="Clear search" style="display: none;">
                        &times;
                    </button>
                    <div class="search-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="11" cy="11" r="8"></circle>
                            <path d="m21 21-4.35-4.35"></path>
                        </svg>
                    </div>
                </div>
                <div class="search-results-info"></div>
            `;

            albumHeader.insertAdjacentElement('afterend', searchContainer);
            this.searchInput = searchContainer.querySelector('.album-search-input');
            this.clearBtn = searchContainer.querySelector('.search-clear');
            this.resultsInfo = searchContainer.querySelector('.search-results-info');
        }

        collectAlbums() {
            const albumCards = document.querySelectorAll('.album-card');
            this.albums = Array.from(albumCards).map(card => ({
                element: card,
                title: card.querySelector('.album-title')?.textContent.toLowerCase() || '',
                description: card.querySelector('.album-description')?.textContent.toLowerCase() || ''
            }));
        }

        bindEvents() {
            if (!this.searchInput) return;

            // Search input
            this.searchInput.addEventListener('input', (e) => {
                this.filterAlbums(e.target.value);
                this.clearBtn.style.display = e.target.value ? 'block' : 'none';
            });

            // Clear button
            this.clearBtn.addEventListener('click', () => {
                this.searchInput.value = '';
                this.filterAlbums('');
                this.clearBtn.style.display = 'none';
                this.searchInput.focus();
            });

            // Keyboard shortcut (Ctrl/Cmd + K)
            document.addEventListener('keydown', (e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                    e.preventDefault();
                    this.searchInput.focus();
                }
            });
        }

        filterAlbums(query) {
            const searchTerm = query.toLowerCase().trim();
            let visibleCount = 0;

            this.albums.forEach(album => {
                const matches = !searchTerm || 
                               album.title.includes(searchTerm) || 
                               album.description.includes(searchTerm);
                
                album.element.style.display = matches ? '' : 'none';
                if (matches) visibleCount++;
            });

            // Update results info
            if (searchTerm) {
                this.resultsInfo.textContent = `Found ${visibleCount} album${visibleCount !== 1 ? 's' : ''}`;
                this.resultsInfo.style.display = 'block';
            } else {
                this.resultsInfo.style.display = 'none';
            }

            // Show no results message
            const noResults = document.querySelector('.no-search-results');
            if (searchTerm && visibleCount === 0) {
                if (!noResults) {
                    const msg = document.createElement('div');
                    msg.className = 'no-search-results';
                    msg.textContent = 'No albums found matching your search.';
                    document.querySelector('.album-grid').appendChild(msg);
                }
            } else if (noResults) {
                noResults.remove();
            }
        }
    }

    // ===========================
    // Enhanced Photo Grid Effects
    // ===========================

    class PhotoGridEnhancements {
        constructor() {
            this.init();
        }

        init() {
            this.addHoverEffects();
            this.enhanceLazyLoading();
            this.addAlbumStats();
        }

        addHoverEffects() {
            // Add data attributes for enhanced hover
            const photoCards = document.querySelectorAll('.photo-card');
            photoCards.forEach((card, index) => {
                card.dataset.photoIndex = index;
                
                // Add zoom container for hover effect
                const container = card.querySelector('.photo-container');
                if (container) {
                    container.classList.add('photo-zoom-container');
                }
            });
        }

        enhanceLazyLoading() {
            // Intersection Observer for lazy loading with placeholders
            const images = document.querySelectorAll('img[loading="lazy"]');
            
            if ('IntersectionObserver' in window) {
                const imageObserver = new IntersectionObserver((entries, observer) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            
                            // Add loading class
                            img.classList.add('loading');
                            
                            // Create skeleton loader
                            const skeleton = document.createElement('div');
                            skeleton.className = 'skeleton-loader';
                            img.parentElement.appendChild(skeleton);
                            
                            // Load image
                            img.addEventListener('load', () => {
                                img.classList.remove('loading');
                                img.classList.add('loaded');
                                skeleton.remove();
                            }, { once: true });
                            
                            img.addEventListener('error', () => {
                                img.classList.remove('loading');
                                img.classList.add('error');
                                skeleton.remove();
                            }, { once: true });
                            
                            observer.unobserve(img);
                        }
                    });
                }, {
                    rootMargin: '50px'
                });

                images.forEach(img => imageObserver.observe(img));
            }
        }

        addAlbumStats() {
            // Add last updated info to album cards
            const albumCards = document.querySelectorAll('.album-card');
            albumCards.forEach(card => {
                const overlay = card.querySelector('.album-overlay');
                if (overlay && !overlay.querySelector('.album-stats')) {
                    const stats = document.createElement('div');
                    stats.className = 'album-stats';
                    
                    // Get photo count from existing element
                    const countElement = overlay.querySelector('.album-count');
                    if (countElement) {
                        stats.innerHTML = `
                            <span class="stat-item">${countElement.textContent}</span>
                        `;
                        overlay.appendChild(stats);
                    }
                }
            });
        }
    }

    // ===========================
    // Loading States & Transitions
    // ===========================

    class LoadingStates {
        constructor() {
            this.init();
        }

        init() {
            this.addPageTransitions();
            this.createSkeletonScreens();
            this.addRetryLogic();
        }

        addPageTransitions() {
            // Add fade-in animation to main content
            const content = document.querySelector('.content');
            if (content) {
                content.classList.add('fade-in');
            }

            // Smooth scroll for navigation
            document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                anchor.addEventListener('click', function (e) {
                    e.preventDefault();
                    const target = document.querySelector(this.getAttribute('href'));
                    if (target) {
                        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                });
            });
        }

        createSkeletonScreens() {
            // Create skeleton screen template
            const createSkeleton = (type) => {
                const skeleton = document.createElement('div');
                skeleton.className = `skeleton skeleton-${type}`;
                
                if (type === 'album') {
                    skeleton.innerHTML = `
                        <div class="skeleton-image"></div>
                        <div class="skeleton-text">
                            <div class="skeleton-line"></div>
                            <div class="skeleton-line short"></div>
                        </div>
                    `;
                } else if (type === 'photo') {
                    skeleton.innerHTML = `
                        <div class="skeleton-image square"></div>
                    `;
                }
                
                return skeleton;
            };

            // Add skeleton screens while images load
            const lazyImages = document.querySelectorAll('img[loading="lazy"]:not(.loaded)');
            lazyImages.forEach(img => {
                if (!img.complete) {
                    const skeleton = createSkeleton(img.closest('.album-card') ? 'album' : 'photo');
                    img.style.opacity = '0';
                    img.parentElement.appendChild(skeleton);
                    
                    img.addEventListener('load', () => {
                        skeleton.remove();
                        img.style.opacity = '1';
                    }, { once: true });
                }
            });
        }

        addRetryLogic() {
            // Add retry functionality for failed image loads
            document.addEventListener('error', (e) => {
                if (e.target.tagName === 'IMG') {
                    const img = e.target;
                    
                    // Skip if already retried
                    if (img.dataset.retried) return;
                    
                    // Create retry button
                    const retryContainer = document.createElement('div');
                    retryContainer.className = 'image-error-container';
                    retryContainer.innerHTML = `
                        <div class="error-message">Failed to load image</div>
                        <button class="retry-button">Retry</button>
                    `;
                    
                    img.style.display = 'none';
                    img.parentElement.appendChild(retryContainer);
                    
                    retryContainer.querySelector('.retry-button').addEventListener('click', () => {
                        img.dataset.retried = 'true';
                        img.style.display = '';
                        retryContainer.remove();
                        
                        // Force reload by updating src
                        const src = img.src;
                        img.src = '';
                        img.src = src;
                    });
                }
            }, true);
        }
    }

    // ===========================
    // Initialize Everything
    // ===========================

    document.addEventListener('DOMContentLoaded', () => {
        // Initialize all components
        const lightbox = new PhotoLightbox();
        const search = new AlbumSearch();
        const gridEnhancements = new PhotoGridEnhancements();
        const loadingStates = new LoadingStates();

        // Make lightbox available globally for potential external use
        window.photoLightbox = lightbox;

        // Add performance marks
        if (window.performance && window.performance.mark) {
            window.performance.mark('photos-js-initialized');
        }

        console.log('Photos app enhanced features initialized');
    });

})();