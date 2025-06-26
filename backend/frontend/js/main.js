// Main application controller for VIParser frontend

class VIParserApp {
    constructor() {
        this.currentPage = 1;
        this.itemsPerPage = 20;
        this.isLoading = false;
        this.currentSearch = '';
        this.currentSort = { sortBy: 'created_at', sortOrder: 'desc' };
        this.currentFilters = {};
        
        // Initialize components
        this.table = new ProductTable(
            'products-table', 
            this.onDataChange.bind(this), 
            this.onUpdateProduct.bind(this),
            this.onDeleteProducts.bind(this),
            this.onExportProducts.bind(this)
        );
        this.pagination = new Pagination('pagination', this.onPageChange.bind(this));
        this.filters = new ProductFilters(this.onFiltersChange.bind(this));
        this.keyboardShortcuts = new KeyboardShortcuts(this);
        
        // Initialize WebSocket client for real-time updates
        this.websocketClient = new WebSocketClient(
            this.onProductCreated.bind(this),
            this.onProductUpdated.bind(this), 
            this.onProductDeleted.bind(this),
            this.onScrapingStatus.bind(this)
        );
        
        // Bind methods
        this.loadProducts = this.loadProducts.bind(this);
        this.retryLoad = this.retryLoad.bind(this);
        this.handleSearch = debounce(this.handleSearch.bind(this), 500);
        this.clearSearch = this.clearSearch.bind(this);
        this.handleRefresh = this.handleRefresh.bind(this);
    }

    /**
     * Initialize the application
     */
    async init() {
        console.log('Initializing VIParser frontend...');
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Test API connection
        const connected = await this.testConnection();
        if (!connected) {
            showError('Could not connect to the API server. Please make sure the backend is running on http://localhost:8000');
            return;
        }
        
        // Load initial data
        await this.loadProducts();
        
        // Connect WebSocket for real-time updates
        console.log('Connecting WebSocket...');
        this.websocketClient.connect();
        
        // Check WebSocket status after a brief delay
        setTimeout(() => {
            console.log('WebSocket status:', this.websocketClient.getStatus());
        }, 1000);
        
        console.log('VIParser frontend initialized successfully');
    }

    /**
     * Set up global event listeners
     */
    setupEventListeners() {
        // Retry button
        const retryBtn = document.getElementById('retry-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', this.retryLoad);
        }

        // Search functionality
        const searchInput = document.getElementById('search-input');
        const clearSearchBtn = document.getElementById('clear-search');
        const refreshBtn = document.getElementById('refresh-btn');

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.handleSearch(e.target.value);
                this.toggleClearButton(e.target.value);
            });

            searchInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.handleSearch(e.target.value, true); // Force immediate search
                }
                if (e.key === 'Escape') {
                    this.clearSearch();
                    searchInput.blur();
                }
            });
        }

        if (clearSearchBtn) {
            clearSearchBtn.addEventListener('click', this.clearSearch);
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', this.handleRefresh);
        }

        // Table sorting
        this.setupTableSorting();

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Only handle shortcuts when not typing in inputs
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            switch (e.key) {
                case 'r':
                case 'R':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.retryLoad();
                    }
                    break;
                case 'ArrowLeft':
                    if (e.ctrlKey) {
                        e.preventDefault();
                        this.pagination.prevPage();
                    }
                    break;
                case 'ArrowRight':
                    if (e.ctrlKey) {
                        e.preventDefault();
                        this.pagination.nextPage();
                    }
                    break;
                case 'Home':
                    if (e.ctrlKey) {
                        e.preventDefault();
                        this.pagination.firstPage();
                    }
                    break;
                case 'End':
                    if (e.ctrlKey) {
                        e.preventDefault();
                        this.pagination.lastPage();
                    }
                    break;
            }
        });

        // Window resize handler for responsive design
        window.addEventListener('resize', debounce(() => {
            this.handleResize();
        }, 250));
    }

    /**
     * Test API connection
     */
    async testConnection() {
        try {
            return await api.testConnection();
        } catch (error) {
            console.error('Connection test failed:', error);
            return false;
        }
    }

    /**
     * Load products from API
     */
    async loadProducts(page = this.currentPage, showLoadingState = true) {
        if (this.isLoading) return;
        
        this.isLoading = true;
        
        if (showLoadingState) {
            showLoading(true);
        }

        try {
            const options = {
                page,
                perPage: this.itemsPerPage,
                sortBy: this.currentSort.sortBy,
                sortOrder: this.currentSort.sortOrder
            };

            // Add search if present
            if (this.currentSearch.trim()) {
                options.search = this.currentSearch.trim();
            }

            // Add filters if present
            Object.assign(options, this.currentFilters);

            const response = await api.getProducts(options);

            // Update table with products
            this.table.updateData(response.data, response.pagination.total);
            
            // Update pagination
            this.pagination.update(response.pagination);
            
            // Update current page
            this.currentPage = response.pagination.page;
            
            showLoading(false);
            
        } catch (error) {
            console.error('Failed to load products:', error);
            showError(`Failed to load products: ${error.message}`);
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Handle page change from pagination
     */
    async onPageChange(page) {
        if (page !== this.currentPage) {
            await this.loadProducts(page, false); // Don't show loading for page changes
        }
    }

    /**
     * Handle data change from table
     */
    onDataChange(products, totalCount) {
        // This can be used for additional processing when data changes
        console.log(`Loaded ${products.length} products (${totalCount} total)`);
    }

    /**
     * Handle filters change
     */
    async onFiltersChange(filters) {
        this.currentFilters = filters;
        
        // Reset to first page when filters change
        this.currentPage = 1;
        
        await this.loadProducts(1, false);
    }

    /**
     * Handle product update from inline editing
     */
    async onUpdateProduct(productId, field, newValue) {
        try {
            console.log(`Updating product ${productId}: ${field} = ${newValue}`);
            
            // Create update object
            const updateData = {};
            updateData[field] = newValue;
            
            // Call API to update product
            await api.updateProduct(productId, updateData);
            
            console.log(`Successfully updated product ${productId}`);
            
        } catch (error) {
            console.error(`Failed to update product ${productId}:`, error);
            throw error; // Re-throw so inline editor can handle it
        }
    }

    /**
     * Handle mass delete operation
     */
    async onDeleteProducts(productIds) {
        try {
            console.log(`Deleting ${productIds.length} products:`, productIds);
            
            // Delete products one by one (could be optimized with batch API)
            const deletePromises = productIds.map(id => api.deleteProduct(id));
            await Promise.all(deletePromises);
            
            console.log(`Successfully deleted ${productIds.length} products`);
            
            // Reload the current page to reflect changes
            await this.loadProducts(this.currentPage, false);
            
        } catch (error) {
            console.error('Failed to delete products:', error);
            throw error; // Re-throw so row selection can handle it
        }
    }

    /**
     * Handle export operation
     */
    async onExportProducts(products) {
        try {
            console.log(`Exporting ${products.length} products`);
            
            // Create CSV content
            const csvContent = this.generateCSV(products);
            
            // Download CSV file
            this.downloadFile(csvContent, 'products.csv', 'text/csv');
            
            console.log(`Successfully exported ${products.length} products`);
            
        } catch (error) {
            console.error('Failed to export products:', error);
            throw error;
        }
    }

    /**
     * Generate CSV content from products
     */
    generateCSV(products) {
        if (products.length === 0) return '';
        
        // Define CSV headers
        const headers = [
            'ID', 'Name', 'SKU', 'Price', 'Currency', 'Availability', 
            'Color', 'Composition', 'Item', 'Comment', 'Created At', 'Product URL'
        ];
        
        // Create CSV rows
        const rows = products.map(product => [
            product.id,
            product.name || '',
            product.sku || '',
            product.price || '',
            product.currency || '',
            product.availability || '',
            product.color || '',
            product.composition || '',
            product.item || '',
            product.comment || '',
            product.created_at || '',
            product.product_url || ''
        ]);
        
        // Combine headers and rows
        const allRows = [headers, ...rows];
        
        // Convert to CSV string
        return allRows.map(row => 
            row.map(field => `"${String(field).replace(/"/g, '""')}"`).join(',')
        ).join('\n');
    }

    /**
     * Download file to user's computer
     */
    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Clean up the URL object
        URL.revokeObjectURL(url);
    }

    /**
     * Retry loading data
     */
    async retryLoad() {
        await this.loadProducts(1, true);
    }

    /**
     * Handle window resize
     */
    handleResize() {
        // Add any responsive behavior here
        // For now, just log the resize
        console.log('Window resized, adjusting layout...');
    }

    /**
     * Refresh current data
     */
    async refresh() {
        await this.loadProducts(this.currentPage, true);
    }

    /**
     * Go to specific page
     */
    async goToPage(page) {
        await this.loadProducts(page, false);
    }

    /**
     * Change items per page
     */
    async setItemsPerPage(count) {
        this.itemsPerPage = count;
        await this.loadProducts(1, true);
    }

    /**
     * Handle search input
     */
    async handleSearch(query, immediate = false) {
        this.currentSearch = query;
        
        // Reset to first page when searching
        this.currentPage = 1;
        
        if (immediate || query.length === 0 || query.length >= 2) {
            await this.loadProducts(1, false);
        }
    }

    /**
     * Clear search
     */
    async clearSearch() {
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.value = '';
        }
        
        this.currentSearch = '';
        this.toggleClearButton('');
        await this.loadProducts(1, false);
    }

    /**
     * Public method to refresh data (for keyboard shortcuts)
     */
    async refresh() {
        await this.loadProducts(this.currentPage, true);
    }

    /**
     * Toggle clear search button visibility
     */
    toggleClearButton(value) {
        const clearBtn = document.getElementById('clear-search');
        if (clearBtn) {
            if (value.trim()) {
                clearBtn.classList.remove('hidden');
            } else {
                clearBtn.classList.add('hidden');
            }
        }
    }

    /**
     * Handle refresh button click
     */
    async handleRefresh() {
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.classList.add('loading');
        }
        
        try {
            await this.loadProducts(this.currentPage, true);
        } finally {
            if (refreshBtn) {
                refreshBtn.classList.remove('loading');
            }
        }
    }

    /**
     * Set up table column sorting
     */
    setupTableSorting() {
        const table = document.getElementById('products-table');
        if (!table) return;

        // Add click listeners to sortable headers
        const sortableHeaders = table.querySelectorAll('th.sortable');
        sortableHeaders.forEach(header => {
            header.addEventListener('click', () => {
                const column = header.dataset.column;
                this.handleSort(column);
            });
        });
    }

    /**
     * Handle column sorting
     */
    async handleSort(column) {
        // Determine new sort order
        let newOrder = 'asc';
        
        if (this.currentSort.sortBy === column) {
            // Toggle if same column
            newOrder = this.currentSort.sortOrder === 'asc' ? 'desc' : 'asc';
        }

        // Update current sort
        this.currentSort.sortBy = column;
        this.currentSort.sortOrder = newOrder;

        // Update visual indicators
        this.updateSortIndicators(column, newOrder);

        // Reset to first page and reload
        await this.loadProducts(1, false);
    }

    /**
     * Update visual sort indicators on table headers
     */
    updateSortIndicators(activeColumn, order) {
        const table = document.getElementById('products-table');
        if (!table) return;

        // Remove all sort classes
        const headers = table.querySelectorAll('th.sortable');
        headers.forEach(header => {
            header.classList.remove('sort-asc', 'sort-desc');
        });

        // Add sort class to active column
        const activeHeader = table.querySelector(`th[data-column="${activeColumn}"]`);
        if (activeHeader) {
            activeHeader.classList.add(`sort-${order}`);
        }
    }

    /**
     * Handle new product created via WebSocket
     */
    onProductCreated(product) {
        console.log('New product created:', product);
        console.log('Current page:', this.currentPage);
        console.log('Current sort:', this.currentSort);
        console.log('Current products count:', this.table.products.length);
        
        // Show notification
        this.showNotification(`New product added: ${product.name || 'Unnamed Product'}`, 'success');
        
        // If we're on the first page and sorting by created_at desc, add the product to the top
        if (this.currentPage === 1 && this.currentSort.sortBy === 'created_at' && this.currentSort.sortOrder === 'desc') {
            console.log('Adding product to current view');
            
            // Add product to the beginning of the current products array
            this.table.products.unshift(product);
            
            // Remove the last product if we have more than itemsPerPage
            if (this.table.products.length > this.itemsPerPage) {
                this.table.products.pop();
            }
            
            // Re-render the table
            this.table.renderRows();
            this.table.rowSelection.initializeTable(this.table.table, this.table.products);
            
            console.log('Product added to table. New count:', this.table.products.length);
        } else {
            console.log('Not adding product to current view - conditions not met');
        }
    }

    /**
     * Handle product updated via WebSocket
     */
    onProductUpdated(product) {
        console.log('Product updated:', product);
        
        // Show notification
        this.showNotification(`Product updated: ${product.name || 'Unnamed Product'}`, 'info');
        
        // Find and update the product in current data
        const productIndex = this.table.products.findIndex(p => p.id === product.id);
        if (productIndex !== -1) {
            this.table.products[productIndex] = product;
            this.table.renderRows();
            this.table.rowSelection.initializeTable(this.table.table, this.table.products);
        }
    }

    /**
     * Handle product deleted via WebSocket
     */
    onProductDeleted(productId) {
        console.log('Product deleted:', productId);
        
        // Show notification
        this.showNotification(`Product deleted (ID: ${productId})`, 'warning');
        
        // Remove product from current data
        const productIndex = this.table.products.findIndex(p => p.id === productId);
        if (productIndex !== -1) {
            this.table.products.splice(productIndex, 1);
            this.table.renderRows();
            this.table.rowSelection.initializeTable(this.table.table, this.table.products);
            
            // Update total count
            const currentTotal = parseInt(this.table.totalCountElement.textContent.split(' ')[0]) - 1;
            this.table.updateTotalCount(currentTotal);
        }
    }

    /**
     * Handle scraping status updates via WebSocket
     */
    onScrapingStatus(status, details) {
        console.log('Scraping status:', status, details);
        
        // Show appropriate notifications based on status
        switch (status) {
            case 'started':
                this.showNotification('Scraping started...', 'info');
                break;
            case 'in_progress':
                this.showNotification(`Scraping in progress: ${details.message || ''}`, 'info');
                break;
            case 'completed':
                this.showNotification('Scraping completed successfully!', 'success');
                break;
            case 'error':
                this.showNotification(`Scraping error: ${details.error || 'Unknown error'}`, 'error');
                break;
        }
    }

    /**
     * Show notification to user
     */
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = createElement('div', {
            className: `notification notification-${type}`
        });
        
        notification.innerHTML = `
            <span>${escapeHtml(message)}</span>
            <button class="notification-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        // Add to page
        let notificationContainer = document.querySelector('.notification-container');
        if (!notificationContainer) {
            notificationContainer = createElement('div', { className: 'notification-container' });
            document.body.appendChild(notificationContainer);
        }
        
        notificationContainer.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
}

// Application initialization
document.addEventListener('DOMContentLoaded', async () => {
    // Create global app instance
    window.app = new VIParserApp();
    
    // Initialize the application
    try {
        await app.init();
    } catch (error) {
        console.error('Failed to initialize application:', error);
        showError(`Application initialization failed: ${error.message}`);
    }
});

// Global refresh function for debugging
window.refreshData = () => {
    if (window.app) {
        window.app.refresh();
    }
};