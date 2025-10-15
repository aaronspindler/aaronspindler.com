/**
 * Search autocomplete functionality
 */
(function() {
    'use strict';

    const searchInput = document.getElementById('header-search-input');
    if (!searchInput) return;

    const searchForm = searchInput.closest('form');
    let autocompleteContainer = null;
    let currentRequest = null;
    let debounceTimer = null;
    let selectedIndex = -1;

    // Create autocomplete container
    function createAutocompleteContainer() {
        if (autocompleteContainer) return;

        autocompleteContainer = document.createElement('div');
        autocompleteContainer.className = 'search-autocomplete';
        autocompleteContainer.setAttribute('role', 'listbox');
        autocompleteContainer.style.display = 'none';

        // Insert after the search form
        searchForm.parentNode.insertBefore(autocompleteContainer, searchForm.nextSibling);
    }

    // Fetch suggestions from API
    function fetchSuggestions(query) {
        if (currentRequest) {
            currentRequest.abort();
        }

        if (query.length < 2) {
            hideSuggestions();
            return;
        }

        const controller = new AbortController();
        currentRequest = controller;

        fetch(`/api/search/autocomplete/?q=${encodeURIComponent(query)}`, {
            signal: controller.signal
        })
        .then(response => response.json())
        .then(data => {
            displaySuggestions(data.suggestions);
        })
        .catch(error => {
            if (error.name !== 'AbortError') {
                console.error('Autocomplete error:', error);
            }
        })
        .finally(() => {
            currentRequest = null;
        });
    }

    // Display suggestions
    function displaySuggestions(suggestions) {
        if (!suggestions || suggestions.length === 0) {
            hideSuggestions();
            return;
        }

        createAutocompleteContainer();
        autocompleteContainer.innerHTML = '';
        selectedIndex = -1;

        suggestions.forEach((suggestion, index) => {
            const item = document.createElement('a');
            item.className = 'search-autocomplete-item';
            item.href = suggestion.url;
            item.setAttribute('role', 'option');
            item.setAttribute('data-index', index);

            if (suggestion.external) {
                item.target = '_blank';
                item.rel = 'noopener noreferrer';
            }

            const title = document.createElement('span');
            title.className = 'autocomplete-title';
            title.textContent = suggestion.title + ' ';

            const type = document.createElement('span');
            type.className = 'autocomplete-type';
            type.textContent = suggestion.type;

            if (suggestion.category) {
                type.className += ' category-' + suggestion.category;
            }

            title.appendChild(type);
            item.appendChild(title);

            // Handle click
            item.addEventListener('click', function(e) {
                // Let the link work naturally
                hideSuggestions();
            });

            // Handle hover
            item.addEventListener('mouseenter', function() {
                setSelectedIndex(index);
            });

            autocompleteContainer.appendChild(item);
        });

        autocompleteContainer.style.display = 'block';
        searchInput.setAttribute('aria-expanded', 'true');
    }

    // Hide suggestions
    function hideSuggestions() {
        if (autocompleteContainer) {
            autocompleteContainer.style.display = 'none';
            autocompleteContainer.innerHTML = '';
        }
        selectedIndex = -1;
        searchInput.setAttribute('aria-expanded', 'false');
    }

    // Set selected index
    function setSelectedIndex(index) {
        const items = autocompleteContainer.querySelectorAll('.search-autocomplete-item');
        items.forEach((item, i) => {
            if (i === index) {
                item.classList.add('selected');
                item.setAttribute('aria-selected', 'true');
            } else {
                item.classList.remove('selected');
                item.setAttribute('aria-selected', 'false');
            }
        });
        selectedIndex = index;
    }

    // Navigate selection
    function navigateSelection(direction) {
        const items = autocompleteContainer?.querySelectorAll('.search-autocomplete-item');
        if (!items || items.length === 0) return;

        let newIndex = selectedIndex + direction;

        if (newIndex < 0) {
            newIndex = items.length - 1;
        } else if (newIndex >= items.length) {
            newIndex = 0;
        }

        setSelectedIndex(newIndex);
        items[newIndex].scrollIntoView({ block: 'nearest' });
    }

    // Handle input
    searchInput.addEventListener('input', function(e) {
        const query = e.target.value.trim();

        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            fetchSuggestions(query);
        }, 150);
    });

    // Handle keyboard navigation
    searchInput.addEventListener('keydown', function(e) {
        if (!autocompleteContainer || autocompleteContainer.style.display === 'none') {
            return;
        }

        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                navigateSelection(1);
                break;
            case 'ArrowUp':
                e.preventDefault();
                navigateSelection(-1);
                break;
            case 'Enter':
                if (selectedIndex >= 0) {
                    e.preventDefault();
                    const items = autocompleteContainer.querySelectorAll('.search-autocomplete-item');
                    if (items[selectedIndex]) {
                        items[selectedIndex].click();
                    }
                }
                break;
            case 'Escape':
                e.preventDefault();
                hideSuggestions();
                searchInput.blur();
                break;
        }
    });

    // Close on click outside
    document.addEventListener('click', function(e) {
        if (!searchForm.contains(e.target) && !autocompleteContainer?.contains(e.target)) {
            hideSuggestions();
        }
    });

    // Close on blur (with small delay to allow clicks)
    searchInput.addEventListener('blur', function() {
        setTimeout(() => {
            if (!autocompleteContainer?.matches(':hover')) {
                hideSuggestions();
            }
        }, 200);
    });

    // Initialize
    searchInput.setAttribute('autocomplete', 'off');
    searchInput.setAttribute('aria-autocomplete', 'list');
    searchInput.setAttribute('aria-expanded', 'false');
})();
