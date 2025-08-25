// Lazy load images
document.addEventListener('DOMContentLoaded', () => {
  // Native lazy loading fallback
  if ('loading' in HTMLImageElement.prototype) {
    const images = document.querySelectorAll('img[loading="lazy"]');
    images.forEach(img => {
      if (img.dataset.src) {
        img.src = img.dataset.src;
      }
    });
  } else {
    // Fallback for browsers that don't support native lazy loading
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/lazysizes/5.3.2/lazysizes.min.js';
    script.integrity = 'sha512-q583ppKrCRc7N5O0n2nzUiJ+suUv7Et1JGels4bXOaMFQcamPk9HjdUknZuuFjBNs7tsMuadge5k9RzdmO+1GQ==';
    script.crossOrigin = 'anonymous';
    document.body.appendChild(script);
  }

  // Add print styles dynamically
  const printStyles = `
    @media print {
      .header, .footer, .tree { display: none !important; }
      body { max-width: 100% !important; }
      a { text-decoration: none !important; color: #000 !important; }
    }
  `;
  const style = document.createElement('style');
  style.textContent = printStyles;
  document.head.appendChild(style);
});

// Optimize web font loading
if (document.fonts && document.fonts.ready) {
  document.fonts.ready.then(() => {
    document.body.classList.add('fonts-loaded');
  });
}

// Prefetch links on hover
document.addEventListener('DOMContentLoaded', () => {
  const prefetched = new Set();
  
  document.querySelectorAll('a[href^="/"]').forEach(link => {
    link.addEventListener('mouseenter', () => {
      const href = link.getAttribute('href');
      if (!prefetched.has(href) && href !== window.location.pathname) {
        const prefetchLink = document.createElement('link');
        prefetchLink.rel = 'prefetch';
        prefetchLink.href = href;
        document.head.appendChild(prefetchLink);
        prefetched.add(href);
      }
    });
  });
});