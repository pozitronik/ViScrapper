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
        
        // Filter inputs
        this.priceMinInput = document.getElementById('price-min');
        this.priceMaxInput = document.getElementById('price-max');
        this.availabilitySelect = document.getElementById('availability-filter');
        this.colorInput = document.getElementById('color-filter');
        this.dateFromInput = document.getElementById('date-from');
        this.dateToInput = document.getElementById('date-to');
        this.imagesSelect = document.getElementById('images-filter');
        
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
        
        this.updateClearFiltersButton();
        
        if (this.onFiltersChange) {
            this.onFiltersChange({});
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
            }
        });

        this.updateClearFiltersButton();
    }
}

// Export for use in other modules
window.ProductFilters = ProductFilters;