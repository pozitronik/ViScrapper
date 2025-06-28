// Filter management for product table

class ProductFilters {
    constructor(onFiltersChange) {
        this.onFiltersChange = onFiltersChange;
        this.isVisible = false;
        this.activeFilters = {};
        
        // Get DOM elements
        this.filterBtn = document.getElementById('filter-btn');
        this.clearFiltersBtn = document.getElementById('clear-filters');
        this.filterPanel = document.getElementById('filter-panel');
        this.filterSummary = document.getElementById('filter-summary');
        this.activeFilterTags = document.getElementById('active-filter-tags');
        this.clearAllFiltersBtn = document.getElementById('clear-all-filters');
        
        // Filter inputs
        this.priceMinInput = document.getElementById('price-min');
        this.priceMaxInput = document.getElementById('price-max');
        this.availabilitySelect = document.getElementById('availability-filter');
        this.colorInput = document.getElementById('color-filter');
        this.dateFromInput = document.getElementById('date-from');
        this.dateToInput = document.getElementById('date-to');
        this.imagesSelect = document.getElementById('images-filter');
        this.postedSelect = document.getElementById('posted-filter');
        
        // Load persisted filters
        this.loadPersistedFilters();
        
        this.setupEventListeners();
    }

    /**
     * Set up event listeners for filter controls
     */
    setupEventListeners() {
        // Toggle filter panel
        if (this.filterBtn) {
            this.filterBtn.addEventListener('click', () => {
                this.toggleFilterPanel();
            });
        }

        // Clear all filters
        if (this.clearFiltersBtn) {
            this.clearFiltersBtn.addEventListener('click', () => {
                this.clearAllFilters();
            });
        }

        // Clear all filters from summary
        if (this.clearAllFiltersBtn) {
            this.clearAllFiltersBtn.addEventListener('click', () => {
                this.clearAllFilters();
            });
        }

        // Price range filters
        if (this.priceMinInput) {
            this.priceMinInput.addEventListener('input', debounce(() => {
                this.updateFilter('priceMin', this.priceMinInput.value);
            }, 500));
        }

        if (this.priceMaxInput) {
            this.priceMaxInput.addEventListener('input', debounce(() => {
                this.updateFilter('priceMax', this.priceMaxInput.value);
            }, 500));
        }

        // Availability filter
        if (this.availabilitySelect) {
            this.availabilitySelect.addEventListener('change', () => {
                this.updateFilter('availability', this.availabilitySelect.value);
            });
        }

        // Color filter
        if (this.colorInput) {
            this.colorInput.addEventListener('input', debounce(() => {
                this.updateFilter('color', this.colorInput.value);
            }, 500));
        }

        // Date range filters
        if (this.dateFromInput) {
            this.dateFromInput.addEventListener('change', () => {
                this.updateFilter('dateFrom', this.dateFromInput.value);
            });
        }

        if (this.dateToInput) {
            this.dateToInput.addEventListener('change', () => {
                this.updateFilter('dateTo', this.dateToInput.value);
            });
        }

        // Images filter
        if (this.imagesSelect) {
            this.imagesSelect.addEventListener('change', () => {
                this.updateFilter('hasImages', this.imagesSelect.value);
            });
        }

        // Posted filter
        if (this.postedSelect) {
            this.postedSelect.addEventListener('change', () => {
                this.updateFilter('posted', this.postedSelect.value);
            });
        }
    }

    /**
     * Toggle filter panel visibility
     */
    toggleFilterPanel() {
        this.isVisible = !this.isVisible;
        
        if (this.filterPanel) {
            if (this.isVisible) {
                this.filterPanel.classList.remove('hidden');
                this.filterBtn.textContent = '🔍 Hide Filters';
            } else {
                this.filterPanel.classList.add('hidden');
                this.filterBtn.innerHTML = '<span class="filter-icon">🔍</span> Filters';
            }
        }
    }

    /**
     * Update a specific filter
     */
    updateFilter(key, value) {
        if (value === '' || value === null || value === undefined) {
            delete this.activeFilters[key];
        } else {
            this.activeFilters[key] = value;
        }

        this.updateClearFiltersButton();
        this.updateFilterSummary();
        
        // Save filters persistently
        this.savePersistedFilters();
        
        if (this.onFiltersChange) {
            this.onFiltersChange(this.getApiFilters());
        }
    }

    /**
     * Clear all filters
     */
    clearAllFilters() {
        this.activeFilters = {};
        
        // Reset all input values
        if (this.priceMinInput) this.priceMinInput.value = '';
        if (this.priceMaxInput) this.priceMaxInput.value = '';
        if (this.availabilitySelect) this.availabilitySelect.value = '';
        if (this.colorInput) this.colorInput.value = '';
        if (this.dateFromInput) this.dateFromInput.value = '';
        if (this.dateToInput) this.dateToInput.value = '';
        if (this.imagesSelect) this.imagesSelect.value = '';
        if (this.postedSelect) this.postedSelect.value = '';
        
        this.updateClearFiltersButton();
        this.updateFilterSummary();
        
        // Clear persisted filters
        this.clearPersistedFilters();
        
        if (this.onFiltersChange) {
            this.onFiltersChange({});
        }
    }

    /**
     * Update filter summary display
     */
    updateFilterSummary() {
        if (!this.filterSummary || !this.activeFilterTags) return;

        const hasActiveFilters = Object.keys(this.activeFilters).length > 0;

        if (!hasActiveFilters) {
            this.filterSummary.classList.add('hidden');
            return;
        }

        // Show filter summary
        this.filterSummary.classList.remove('hidden');

        // Clear existing tags
        this.activeFilterTags.innerHTML = '';

        // Create filter tags
        Object.entries(this.activeFilters).forEach(([key, value]) => {
            const tag = this.createFilterTag(key, value);
            if (tag) {
                this.activeFilterTags.appendChild(tag);
            }
        });
    }

    /**
     * Create a filter tag for the summary
     */
    createFilterTag(key, value) {
        const filterLabel = this.getFilterLabel(key, value);
        if (!filterLabel) return null;

        const tag = createElement('div', { className: 'filter-tag' });
        
        const label = createElement('span', {}, filterLabel);
        tag.appendChild(label);

        const removeBtn = createElement('button', {
            className: 'filter-tag-remove',
            title: 'Remove filter'
        }, '×');

        removeBtn.addEventListener('click', () => {
            this.removeFilter(key);
        });

        tag.appendChild(removeBtn);
        return tag;
    }

    /**
     * Get human-readable label for filter
     */
    getFilterLabel(key, value) {
        switch (key) {
            case 'priceMin':
                return `Price ≥ $${value}`;
            case 'priceMax':
                return `Price ≤ $${value}`;
            case 'availability':
                return `Status: ${value}`;
            case 'color':
                return `Color: ${value}`;
            case 'dateFrom':
                return `From: ${new Date(value).toLocaleDateString()}`;
            case 'dateTo':
                return `To: ${new Date(value).toLocaleDateString()}`;
            case 'hasImages':
                return value === 'true' ? 'With Images' : 'Without Images';
            case 'posted':
                return value === 'posted' ? 'Posted to Telegram' : 'Not Posted';
            default:
                return null;
        }
    }

    /**
     * Remove a specific filter
     */
    removeFilter(key) {
        // Clear the input
        switch (key) {
            case 'priceMin':
                if (this.priceMinInput) this.priceMinInput.value = '';
                break;
            case 'priceMax':
                if (this.priceMaxInput) this.priceMaxInput.value = '';
                break;
            case 'availability':
                if (this.availabilitySelect) this.availabilitySelect.value = '';
                break;
            case 'color':
                if (this.colorInput) this.colorInput.value = '';
                break;
            case 'dateFrom':
                if (this.dateFromInput) this.dateFromInput.value = '';
                break;
            case 'dateTo':
                if (this.dateToInput) this.dateToInput.value = '';
                break;
            case 'hasImages':
                if (this.imagesSelect) this.imagesSelect.value = '';
                break;
            case 'posted':
                if (this.postedSelect) this.postedSelect.value = '';
                break;
        }

        // Remove from active filters
        delete this.activeFilters[key];

        // Update UI
        this.updateClearFiltersButton();
        this.updateFilterSummary();
        
        // Save filters persistently
        this.savePersistedFilters();

        // Notify change
        if (this.onFiltersChange) {
            this.onFiltersChange(this.getApiFilters());
        }
    }

    /**
     * Update clear filters button visibility
     */
    updateClearFiltersButton() {
        if (this.clearFiltersBtn) {
            const hasActiveFilters = Object.keys(this.activeFilters).length > 0;
            if (hasActiveFilters) {
                this.clearFiltersBtn.classList.remove('hidden');
            } else {
                this.clearFiltersBtn.classList.add('hidden');
            }
        }
    }

    /**
     * Get filters formatted for API requests
     */
    getApiFilters() {
        const apiFilters = {};

        // Price range
        if (this.activeFilters.priceMin) {
            apiFilters.min_price = parseFloat(this.activeFilters.priceMin);
        }
        if (this.activeFilters.priceMax) {
            apiFilters.max_price = parseFloat(this.activeFilters.priceMax);
        }

        // Availability
        if (this.activeFilters.availability) {
            apiFilters.availability = this.activeFilters.availability;
        }

        // Color
        if (this.activeFilters.color) {
            apiFilters.color = this.activeFilters.color.trim();
        }

        // Date range
        if (this.activeFilters.dateFrom) {
            apiFilters.created_after = this.activeFilters.dateFrom;
        }
        if (this.activeFilters.dateTo) {
            apiFilters.created_before = this.activeFilters.dateTo;
        }

        // Has images
        if (this.activeFilters.hasImages) {
            apiFilters.has_images = this.activeFilters.hasImages === 'true';
        }

        // Posted status
        if (this.activeFilters.posted) {
            apiFilters.telegram_posted = this.activeFilters.posted === 'posted';
        }

        return apiFilters;
    }

    /**
     * Get current active filters
     */
    getActiveFilters() {
        return { ...this.activeFilters };
    }

    /**
     * Check if any filters are active
     */
    hasActiveFilters() {
        return Object.keys(this.activeFilters).length > 0;
    }

    /**
     * Hide filter panel
     */
    hidePanel() {
        this.isVisible = false;
        if (this.filterPanel) {
            this.filterPanel.classList.add('hidden');
            this.filterBtn.innerHTML = '<span class="filter-icon">🔍</span> Filters';
        }
    }

    /**
     * Set filters programmatically
     */
    setFilters(filters) {
        this.clearAllFilters();
        
        // Update inputs based on provided filters
        Object.entries(filters).forEach(([key, value]) => {
            switch (key) {
                case 'min_price':
                    if (this.priceMinInput) this.priceMinInput.value = value;
                    this.activeFilters.priceMin = value;
                    break;
                case 'max_price':
                    if (this.priceMaxInput) this.priceMaxInput.value = value;
                    this.activeFilters.priceMax = value;
                    break;
                case 'availability':
                    if (this.availabilitySelect) this.availabilitySelect.value = value;
                    this.activeFilters.availability = value;
                    break;
                case 'color':
                    if (this.colorInput) this.colorInput.value = value;
                    this.activeFilters.color = value;
                    break;
                case 'created_after':
                    if (this.dateFromInput) this.dateFromInput.value = value;
                    this.activeFilters.dateFrom = value;
                    break;
                case 'created_before':
                    if (this.dateToInput) this.dateToInput.value = value;
                    this.activeFilters.dateTo = value;
                    break;
                case 'has_images':
                    if (this.imagesSelect) this.imagesSelect.value = value ? 'true' : 'false';
                    this.activeFilters.hasImages = value ? 'true' : 'false';
                    break;
                case 'telegram_posted':
                    if (this.postedSelect) this.postedSelect.value = value ? 'posted' : 'not_posted';
                    this.activeFilters.posted = value ? 'posted' : 'not_posted';
                    break;
            }
        });

        this.updateClearFiltersButton();
        this.updateFilterSummary();
    }

    /**
     * Load persisted filters from localStorage
     */
    loadPersistedFilters() {
        try {
            const savedFilters = localStorage.getItem('viparser_filters');
            if (savedFilters) {
                const filters = JSON.parse(savedFilters);
                
                // Apply filters to UI elements
                Object.entries(filters).forEach(([key, value]) => {
                    switch (key) {
                        case 'priceMin':
                            if (this.priceMinInput) this.priceMinInput.value = value;
                            break;
                        case 'priceMax':
                            if (this.priceMaxInput) this.priceMaxInput.value = value;
                            break;
                        case 'availability':
                            if (this.availabilitySelect) this.availabilitySelect.value = value;
                            break;
                        case 'color':
                            if (this.colorInput) this.colorInput.value = value;
                            break;
                        case 'dateFrom':
                            if (this.dateFromInput) this.dateFromInput.value = value;
                            break;
                        case 'dateTo':
                            if (this.dateToInput) this.dateToInput.value = value;
                            break;
                        case 'hasImages':
                            if (this.imagesSelect) this.imagesSelect.value = value;
                            break;
                        case 'posted':
                            if (this.postedSelect) this.postedSelect.value = value;
                            break;
                    }
                });
                
                // Set active filters
                this.activeFilters = filters;
                
                // Update UI
                this.updateClearFiltersButton();
                this.updateFilterSummary();
            }
        } catch (error) {
            console.error('Error loading persisted filters:', error);
        }
    }

    /**
     * Save current filters to localStorage
     */
    savePersistedFilters() {
        try {
            localStorage.setItem('viparser_filters', JSON.stringify(this.activeFilters));
        } catch (error) {
            console.error('Error saving persisted filters:', error);
        }
    }

    /**
     * Clear persisted filters from localStorage
     */
    clearPersistedFilters() {
        try {
            localStorage.removeItem('viparser_filters');
        } catch (error) {
            console.error('Error clearing persisted filters:', error);
        }
    }
}

// Export for use in other modules
window.ProductFilters = ProductFilters;