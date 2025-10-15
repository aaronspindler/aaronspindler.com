// Empty service worker for cleanup
// This file exists only to prevent 404 errors while old service workers are being unregistered
// It will be automatically unregistered by base.js
self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', () => {
  self.clients.claim();
  // Unregister itself after activation
  self.registration.unregister().then(() => {
    console.log('Service worker unregistered itself');
  });
});
