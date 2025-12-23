/**
 * Focal Point Editor for Django Admin
 * Allows clicking on images to set focal points interactively
 */

(function() {
    'use strict';

    // Initialize focal point editors when DOM is ready
    function initializeFocalPointEditors() {
        const images = document.querySelectorAll('[id^="focal-point-image-"]');

        images.forEach(image => {
            const photoId = image.dataset.photoId;
            const crosshair = document.getElementById(`focal-point-crosshair-${photoId}`);
            const coordsDisplay = document.getElementById(`focal-point-coords-${photoId}`);

            // Initialize crosshair position from current focal point
            updateCrosshairPosition(image, crosshair, parseFloat(image.dataset.focalX), parseFloat(image.dataset.focalY));

            // Handle image clicks
            image.addEventListener('click', function(event) {
                handleImageClick(event, image, crosshair, coordsDisplay, photoId);
            });
        });
    }

    function handleImageClick(event, image, crosshair, coordsDisplay, photoId) {
        // Get click coordinates relative to the image
        const rect = image.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        // Convert to normalized coordinates (0-1)
        const focalX = x / rect.width;
        const focalY = y / rect.height;

        // Update crosshair position
        updateCrosshairPosition(image, crosshair, focalX, focalY);

        // Update coordinates display
        coordsDisplay.textContent = `(${focalX.toFixed(3)}, ${focalY.toFixed(3)})`;

        // Send AJAX request to update focal point
        updateFocalPointServer(photoId, focalX, focalY, coordsDisplay);
    }

    function updateCrosshairPosition(image, crosshair, focalX, focalY) {
        if (!crosshair) return;

        const rect = image.getBoundingClientRect();
        const x = focalX * rect.width;
        const y = focalY * rect.height;

        crosshair.style.display = 'block';
        crosshair.style.left = `${x}px`;
        crosshair.style.top = `${y}px`;
    }

    function updateFocalPointServer(photoId, focalX, focalY, coordsDisplay) {
        // Get CSRF token from cookie
        const csrfToken = getCookie('csrftoken');

        // Construct the URL for the admin endpoint
        const url = `/admin/photos/photo/${photoId}/update-focal-point/`;

        // Show loading state
        const originalText = coordsDisplay.innerHTML;
        coordsDisplay.innerHTML = `<span style="color: #666;">Updating...</span>`;

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({
                focal_x: focalX,
                focal_y: focalY
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message briefly
                coordsDisplay.innerHTML = `<span style="color: green;">✓ Saved! Reloading...</span>`;

                // Show Django admin success message
                showDjangoMessage('Focal point updated. Reprocessing image...', 'success');

                // Reload the page after a short delay to show the updated override flag
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                coordsDisplay.innerHTML = `<span style="color: red;">Error: ${data.error}</span>`;
                setTimeout(() => {
                    coordsDisplay.innerHTML = originalText;
                }, 3000);
            }
        })
        .catch(error => {
            console.error('Error updating focal point:', error);
            coordsDisplay.innerHTML = `<span style="color: red;">Error updating focal point</span>`;
            setTimeout(() => {
                coordsDisplay.innerHTML = originalText;
            }, 3000);
        });
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function showDjangoMessage(message, level) {
        // Create Django-style message
        const messagesContainer = document.querySelector('.messagelist') || createMessageContainer();
        const messageItem = document.createElement('li');
        messageItem.className = level;
        messageItem.textContent = message;
        messagesContainer.appendChild(messageItem);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            messageItem.remove();
        }, 5000);
    }

    function createMessageContainer() {
        const container = document.createElement('ul');
        container.className = 'messagelist';
        const contentDiv = document.querySelector('#content');
        if (contentDiv) {
            contentDiv.insertBefore(container, contentDiv.firstChild);
        }
        return container;
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeFocalPointEditors);
    } else {
        initializeFocalPointEditors();
    }
})();
