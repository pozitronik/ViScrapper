// Main application controller for VIParser frontend

class VIParserApp {
    constructor() {
        this.currentPage = 1;
        this.itemsPerPage = this.loadPageSizePreference();
        this.isLoading = false;
        this.currentSearch = this.loadSearchPreference();
        this.currentSort = this.loadSortPreference();
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
            this.onScrapingStatus.bind(this),
            this.onBulkPostEvent.bind(this)
        );
        
        // Bind methods
        this.loadProducts = this.loadProducts.bind(this);
        this.retryLoad = this.retryLoad.bind(this);
        this.handleSearch = debounce(this.handleSearch.bind(this), 500);
        this.clearSearch = this.clearSearch.bind(this);
        this.handleRefresh = this.handleRefresh.bind(this);
        this.handlePageSizeChange = this.handlePageSizeChange.bind(this);
    }

    /**
     * Initialize the application
     */
    async init() {
        console.log('Initializing VIParser frontend...');
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Set initial page size in UI
        this.setPageSizeUI();
        
        // Set initial sort indicators in UI
        this.setSortUI();
        
        // Set initial search value in UI
        this.setSearchUI();
        
        // Test API connection
        const connected = await this.testConnection();
        if (!connected) {
            showError('Could not connect to the API server. Please make sure the backend is running on http://localhost:8000');
            return;
        }
        
        // Apply any persisted filters before loading data
        this.currentFilters = this.filters.getApiFilters();
        
        // Load initial data
        await this.loadProducts();
        
        // Update unposted products count for Telegram bulk post button
        await this.updateUnpostedCount();
        
        // Check for product highlighting from URL
        this.handleProductHighlighting();
        
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

        // Page size selector
        const pageSizeSelect = document.getElementById('page-size-select');
        if (pageSizeSelect) {
            pageSizeSelect.addEventListener('change', this.handlePageSizeChange);
        }

        // Bulk post telegram button
        const bulkPostBtn = document.getElementById('bulk-post-telegram');
        if (bulkPostBtn) {
            bulkPostBtn.addEventListener('click', this.handleBulkPostTelegram.bind(this));
        }

        // Bulk post modal handlers
        this.setupBulkPostModalHandlers();

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
     * Fetch all products by getting all pages
     */
    async fetchAllProducts() {
        const allProducts = [];
        let currentPage = 1;
        let totalItems = 0;
        
        while (true) {
            const options = {
                page: currentPage,
                perPage: 100, // Use maximum allowed per page
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
            
            // Add products from this page
            allProducts.push(...response.data);
            totalItems = response.pagination.total;
            
            // Check if we have more pages
            if (!response.pagination.has_next || response.data.length === 0) {
                break;
            }
            
            currentPage++;
        }
        
        return {
            data: allProducts,
            total: totalItems
        };
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
            if (this.itemsPerPage === 'all') {
                // Fetch all products by getting all pages
                const allProducts = await this.fetchAllProducts();
                
                // Update table with all products
                this.table.updateData(allProducts.data, allProducts.total);
                
                // Hide pagination
                this.pagination.container.innerHTML = '';
                
                // Set current page to 1 for consistency
                this.currentPage = 1;
            } else {
                // Normal pagination
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
            }
            
            showLoading(false);
            
        } catch (error) {
            console.error('Failed to load products:', error);
            showError(`Failed to load products: ${error.message}`);
            
            // If this was caused by "all" option, reset to a reasonable default
            if (this.itemsPerPage === 'all') {
                console.log('Resetting page size from "all" to 20 due to error');
                this.itemsPerPage = 20;
                this.savePageSizePreference(20);
                this.setPageSizeUI();
                
                // Try loading again with the default page size
                setTimeout(() => {
                    this.loadProducts(1, false);
                }, 1000);
            }
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
            const response = await api.updateProduct(productId, updateData);
            
            console.log(`Successfully updated product ${productId}`);
            
            // For selling_price updates, we need to refresh the product data
            // to get the updated sell_price calculation
            if (field === 'selling_price') {
                // Get the updated product data
                const updatedProductResponse = await api.getProduct(productId);
                const updatedProduct = updatedProductResponse.data || updatedProductResponse;
                
                // Update the row with new data
                this.table.updateProductRow(updatedProduct);
            }
            
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
     * Handle page size change from select dropdown
     */
    async handlePageSizeChange(event) {
        const newPageSizeValue = event.target.value;
        let newPageSize = newPageSizeValue === 'all' ? 'all' : parseInt(newPageSizeValue);
        
        if (newPageSize && newPageSize !== this.itemsPerPage) {
            console.log(`Changing page size from ${this.itemsPerPage} to ${newPageSize}`);
            
            // Update page size and reset to first page
            this.itemsPerPage = newPageSize;
            this.currentPage = 1;
            
            // Save preference to localStorage
            this.savePageSizePreference(newPageSize);
            
            // Update select dropdown to current selection
            const pageSizeSelect = document.getElementById('page-size-select');
            if (pageSizeSelect) {
                pageSizeSelect.value = newPageSizeValue;
            }
            
            // Reload data with new page size
            await this.loadProducts(1, true);
        }
    }

    /**
     * Handle search input
     */
    async handleSearch(query, immediate = false) {
        this.currentSearch = query;
        
        // Save search persistently
        this.saveSearchPreference(query);
        
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
        
        // Clear persistent search
        this.saveSearchPreference('');
        
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

        // Save preference to localStorage
        this.saveSortPreference(this.currentSort);

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
        
        // Show appropriate notification based on update info
        let message = `Product updated: ${product.name || 'Unnamed Product'}`;
        let type = 'info';
        
        if (product._update_info) {
            const updateInfo = product._update_info;
            const matchType = updateInfo.match_type ? updateInfo.match_type.toUpperCase() : '';
            
            if (updateInfo.was_updated) {
                const summary = updateInfo.update_summary;
                const updates = [];
                
                if (summary.fields_updated && summary.fields_updated.length > 0) {
                    updates.push(`${summary.fields_updated.length} field(s)`);
                }
                if (summary.images_added > 0) {
                    updates.push(`${summary.images_added} image(s)`);
                }
                if (summary.sizes_added > 0) {
                    updates.push(`${summary.sizes_added} size(s)`);
                }
                
                if (updates.length > 0) {
                    message = `Product updated (${matchType} match): ${updates.join(', ')} updated`;
                } else {
                    message = `Product updated (${matchType} match)`;
                }
                type = 'success';
            } else {
                message = `Product already exists with identical data (${matchType} match)`;
                type = 'info';
            }
        }
        
        this.showNotification(message, type);
        
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

    /**
     * Load page size preference from localStorage
     */
    loadPageSizePreference() {
        try {
            const savedPageSize = localStorage.getItem('viparser_page_size');
            if (savedPageSize) {
                if (savedPageSize === 'all') {
                    return 'all';
                }
                const pageSize = parseInt(savedPageSize);
                // Validate that it's one of the allowed values
                if ([10, 20, 50, 100].includes(pageSize)) {
                    return pageSize;
                }
            }
        } catch (error) {
            console.error('Error loading page size preference:', error);
        }
        return 20; // Default value
    }

    /**
     * Save page size preference to localStorage
     */
    savePageSizePreference(pageSize) {
        try {
            localStorage.setItem('viparser_page_size', pageSize.toString());
        } catch (error) {
            console.error('Error saving page size preference:', error);
        }
    }

    /**
     * Set the page size in the UI dropdown
     */
    setPageSizeUI() {
        const pageSizeSelect = document.getElementById('page-size-select');
        if (pageSizeSelect) {
            pageSizeSelect.value = this.itemsPerPage === 'all' ? 'all' : this.itemsPerPage.toString();
        }
    }

    /**
     * Set the sort indicators in the UI
     */
    setSortUI() {
        this.updateSortIndicators(this.currentSort.sortBy, this.currentSort.sortOrder);
    }

    /**
     * Handle product highlighting from URL parameters
     */
    handleProductHighlighting() {
        const urlParams = new URLSearchParams(window.location.search);
        const highlightId = urlParams.get('highlight');
        
        if (highlightId) {
            // Remove the parameter from URL without refreshing
            const newUrl = window.location.pathname;
            window.history.replaceState({}, document.title, newUrl);
            
            // Highlight the product row
            setTimeout(() => {
                this.highlightProductRow(parseInt(highlightId));
            }, 500);
        }
    }

    /**
     * Highlight a specific product row
     */
    highlightProductRow(productId) {
        const row = document.querySelector(`tr[data-product-id="${productId}"]`);
        if (row) {
            // Add highlight class
            row.classList.add('highlighted');
            
            // Scroll to the row
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Remove highlight after 3 seconds
            setTimeout(() => {
                row.classList.remove('highlighted');
            }, 3000);
        }
    }

    /**
     * Load sort preference from localStorage
     */
    loadSortPreference() {
        try {
            const savedSort = localStorage.getItem('viparser_sort');
            if (savedSort) {
                const sortData = JSON.parse(savedSort);
                // Validate the data
                if (sortData.sortBy && sortData.sortOrder && 
                    ['asc', 'desc'].includes(sortData.sortOrder)) {
                    return sortData;
                }
            }
        } catch (error) {
            console.error('Error loading sort preference:', error);
        }
        // Default sort: newest first
        return { sortBy: 'created_at', sortOrder: 'desc' };
    }

    /**
     * Save sort preference to localStorage
     */
    saveSortPreference(sortData) {
        try {
            localStorage.setItem('viparser_sort', JSON.stringify(sortData));
        } catch (error) {
            console.error('Error saving sort preference:', error);
        }
    }

    /**
     * Load search preference from localStorage
     */
    loadSearchPreference() {
        try {
            const savedSearch = localStorage.getItem('viparser_search');
            return savedSearch || '';
        } catch (error) {
            console.error('Error loading search preference:', error);
            return '';
        }
    }

    /**
     * Save search preference to localStorage
     */
    saveSearchPreference(searchQuery) {
        try {
            localStorage.setItem('viparser_search', searchQuery);
        } catch (error) {
            console.error('Error saving search preference:', error);
        }
    }

    /**
     * Set the search value in the UI input
     */
    setSearchUI() {
        const searchInput = document.getElementById('search-input');
        if (searchInput && this.currentSearch) {
            searchInput.value = this.currentSearch;
            this.toggleClearButton(this.currentSearch);
        }
    }

    /**
     * Setup bulk post modal event handlers
     */
    setupBulkPostModalHandlers() {
        // Modal controls
        const modal = document.getElementById('bulk-post-modal');
        const closeBtn = document.getElementById('bulk-post-close');
        const cancelBtn = document.getElementById('bulk-post-cancel');
        const startBtn = document.getElementById('bulk-post-start');
        const doneBtn = document.getElementById('bulk-post-done');

        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeBulkPostModal());
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.closeBulkPostModal());
        }

        if (startBtn) {
            startBtn.addEventListener('click', () => this.startBulkPost());
        }

        if (doneBtn) {
            doneBtn.addEventListener('click', () => this.closeBulkPostModal());
        }

        // Close modal when clicking outside
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeBulkPostModal();
                }
            });
        }
    }

    /**
     * Handle bulk post telegram button click
     */
    async handleBulkPostTelegram() {
        try {
            // Get unposted products count
            await this.updateUnpostedCount();

            // Get channel information
            const channelsResponse = await this.fetchChannels();
            
            // Open modal
            this.openBulkPostModal(channelsResponse);

        } catch (error) {
            console.error('Error opening bulk post modal:', error);
            this.showNotification('Failed to load bulk post information', 'error');
        }
    }

    /**
     * Update unposted products count
     */
    async updateUnpostedCount() {
        try {
            const response = await fetch('/api/v1/telegram/unposted-count');
            const data = await response.json();
            
            const count = data.success ? data.data.unposted_count : 0;
            const countElement = document.getElementById('unposted-count');
            const bulkPostBtn = document.getElementById('bulk-post-telegram');
            
            if (countElement) {
                countElement.textContent = count;
            }
            
            // Disable button if no unposted products
            if (bulkPostBtn) {
                bulkPostBtn.disabled = count === 0;
                if (count === 0) {
                    bulkPostBtn.title = 'No unposted products available';
                } else {
                    bulkPostBtn.title = `Post ${count} unposted products to Telegram`;
                }
            }

            return count;
        } catch (error) {
            console.error('Error updating unposted count:', error);
            return 0;
        }
    }

    /**
     * Fetch channels information
     */
    async fetchChannels() {
        const response = await fetch('/api/v1/telegram/channels?active_only=true');
        const data = await response.json();
        
        if (!data.success) {
            throw new Error('Failed to fetch channels');
        }

        // Return all active channels for bulk posting (user can choose)
        return data.data;
    }

    /**
     * Open bulk post modal
     */
    openBulkPostModal(channels) {
        const modal = document.getElementById('bulk-post-modal');
        const unpostedCountEl = document.getElementById('modal-unposted-count');
        const channelCountEl = document.getElementById('modal-channel-count');

        // Store channels for later use in startBulkPost
        this.availableChannels = channels;

        // Update modal content
        const unpostedCount = document.getElementById('unposted-count').textContent;
        if (unpostedCountEl) {
            unpostedCountEl.textContent = unpostedCount;
        }

        if (channelCountEl) {
            if (channels.length === 0) {
                channelCountEl.textContent = 'No active channels configured';
                channelCountEl.style.color = '#dc3545';
            } else {
                const channelNames = channels.map(c => c.name).join(', ');
                channelCountEl.textContent = `${channels.length} channels (${channelNames})`;
                channelCountEl.style.color = '#28a745';
            }
        }

        // Reset modal state
        this.resetBulkPostModal();

        // Show modal
        if (modal) {
            modal.classList.remove('hidden');
        }

        // Disable start button if no channels
        const startBtn = document.getElementById('bulk-post-start');
        if (startBtn) {
            startBtn.disabled = channels.length === 0;
        }
    }

    /**
     * Close bulk post modal
     */
    closeBulkPostModal() {
        const modal = document.getElementById('bulk-post-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
        this.resetBulkPostModal();
    }

    /**
     * Reset bulk post modal to initial state
     */
    resetBulkPostModal() {
        // Hide progress and results sections
        const progressSection = document.getElementById('bulk-post-progress');
        const resultsSection = document.getElementById('bulk-post-results');
        
        if (progressSection) {
            progressSection.classList.add('hidden');
        }
        
        if (resultsSection) {
            resultsSection.classList.add('hidden');
        }

        // Reset progress
        const progressFill = document.getElementById('bulk-progress-fill');
        const progressText = document.getElementById('bulk-progress-text');
        const progressPercent = document.getElementById('bulk-progress-percent');

        if (progressFill) {
            progressFill.style.width = '0%';
        }
        
        if (progressText) {
            progressText.textContent = 'Preparing...';
        }
        
        if (progressPercent) {
            progressPercent.textContent = '0%';
        }

        // Show/hide buttons
        const startBtn = document.getElementById('bulk-post-start');
        const cancelBtn = document.getElementById('bulk-post-cancel');
        const doneBtn = document.getElementById('bulk-post-done');

        if (startBtn) {
            startBtn.classList.remove('hidden');
            startBtn.disabled = false;
        }
        
        if (cancelBtn) {
            cancelBtn.classList.remove('hidden');
        }
        
        if (doneBtn) {
            doneBtn.classList.add('hidden');
        }
    }

    /**
     * Start bulk posting process
     */
    async startBulkPost() {
        const startBtn = document.getElementById('bulk-post-start');
        const cancelBtn = document.getElementById('bulk-post-cancel');
        const progressSection = document.getElementById('bulk-post-progress');

        // Hide start button and show progress
        if (startBtn) {
            startBtn.classList.add('hidden');
        }
        
        if (cancelBtn) {
            cancelBtn.style.display = 'none';
        }
        
        if (progressSection) {
            progressSection.classList.remove('hidden');
        }

        // Initialize timer
        this.startTimer();
        
        // Get unposted products first to create message items
        const unpostedResponse = await fetch('/api/v1/telegram/unposted-count');
        const unpostedData = await unpostedResponse.json();
        const totalProducts = unpostedData.success ? unpostedData.data.unposted_count : 0;
        
        // Store total products for WebSocket handlers
        this.totalProducts = totalProducts;

        try {
            // Get available channels (stored from modal opening)
            const channels = this.availableChannels || [];
            
            if (channels.length === 0) {
                throw new Error('No channels available for posting');
            }
            
            const channelIds = channels.map(c => c.id);
            
            // Build query string with channel IDs
            const queryParams = new URLSearchParams();
            channelIds.forEach(id => queryParams.append('channel_ids', id));
            
            // WebSocket events will handle the progress updates
            // Just start the bulk posting process
            const response = await fetch(`/api/v1/telegram/bulk-post-unposted?${queryParams}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                // Show results (WebSocket already handled final status updates)
                this.showBulkPostResults(data.data);
            } else {
                // Stop timer on error
                this.stopTimer();
                throw new Error(data.message || 'Bulk posting failed');
            }

        } catch (error) {
            console.error('Bulk posting error:', error);
            
            // Stop timer on error
            this.stopTimer();
            
            // Update progress status
            this.updateProgressStatus(0, totalProducts, 'Error occurred during posting');
            
            this.showNotification(`Bulk posting failed: ${error.message}`, 'error');
            
            // Reset modal on error
            this.resetBulkPostModal();
        }
    }

    /**
     * Show bulk post results
     */
    showBulkPostResults(results) {
        const progressSection = document.getElementById('bulk-post-progress');
        const resultsSection = document.getElementById('bulk-post-results');
        const progressFill = document.getElementById('bulk-progress-fill');
        const progressText = document.getElementById('bulk-progress-text');
        const progressPercent = document.getElementById('bulk-progress-percent');

        // Complete progress bar
        if (progressFill) {
            progressFill.style.width = '100%';
        }
        
        if (progressText) {
            progressText.textContent = 'Completed';
        }
        
        if (progressPercent) {
            progressPercent.textContent = '100%';
        }

        // Show results after a brief delay
        setTimeout(() => {
            if (progressSection) {
                progressSection.classList.add('hidden');
            }
            
            if (resultsSection) {
                resultsSection.classList.remove('hidden');
            }

            // Update result numbers
            const successEl = document.getElementById('result-success');
            const failedEl = document.getElementById('result-failed');

            if (successEl) {
                successEl.textContent = results.posted_count || 0;
            }
            
            if (failedEl) {
                failedEl.textContent = results.failed_count || 0;
            }

            // Show detailed results
            this.showDetailedResults(results.results || []);

            // Show done button
            const doneBtn = document.getElementById('bulk-post-done');
            if (doneBtn) {
                doneBtn.classList.remove('hidden');
            }

        }, 1000);
    }

    /**
     * Show detailed results in the modal
     */
    showDetailedResults(results) {
        const detailsContainer = document.getElementById('bulk-post-details');
        if (!detailsContainer) return;

        detailsContainer.innerHTML = '';

        if (results.length === 0) {
            detailsContainer.innerHTML = '<p>No results to display</p>';
            return;
        }

        results.forEach(result => {
            const resultItem = document.createElement('div');
            resultItem.className = `result-item ${result.success ? 'success' : 'error'}`;

            const name = document.createElement('div');
            name.className = 'result-item-name';
            name.textContent = result.product_name || `Product #${result.product_id}`;

            const status = document.createElement('div');
            status.className = 'result-item-status';
            
            if (result.success) {
                status.textContent = `✓ Posted (${result.posts_created || 0})`;
            } else {
                status.textContent = `✗ Failed`;
                if (result.error) {
                    status.title = result.error;
                }
            }

            resultItem.appendChild(name);
            resultItem.appendChild(status);
            detailsContainer.appendChild(resultItem);
        });
    }

    /**
     * Start the timer for bulk posting
     */
    startTimer() {
        this.startTime = Date.now();
        this.timerInterval = setInterval(() => {
            const elapsed = Date.now() - this.startTime;
            const minutes = Math.floor(elapsed / 60000);
            const seconds = Math.floor((elapsed % 60000) / 1000);
            const timerElement = document.getElementById('bulk-timer');
            if (timerElement) {
                timerElement.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }

    /**
     * Stop the timer
     */
    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    /**
     * Initialize progress display with message items
     */
    initializeProgress(totalProducts) {
        const statusElement = document.getElementById('progress-status');
        const countsElement = document.getElementById('progress-counts');
        const messageList = document.getElementById('message-list');

        if (statusElement) {
            statusElement.textContent = 'Preparing to post...';
        }
        
        if (countsElement) {
            countsElement.textContent = `(0/${totalProducts})`;
        }

        if (messageList) {
            messageList.innerHTML = '';
            
            // Create placeholders for each product
            for (let i = 1; i <= totalProducts; i++) {
                const messageItem = document.createElement('div');
                messageItem.className = 'message-item';
                messageItem.id = `message-item-${i}`;
                
                messageItem.innerHTML = `
                    <div class="message-status" id="status-${i}">⏳</div>
                    <div class="message-details">
                        <div class="message-product" id="product-name-${i}">Product ${i}</div>
                        <div class="message-info">
                            <span class="message-channels" id="channels-${i}">Waiting...</span>
                        </div>
                    </div>
                    <div class="message-time" id="time-${i}">--:--</div>
                `;
                
                messageList.appendChild(messageItem);
            }
        }
    }

    /**
     * Update status of a specific message
     */
    updateMessageStatus(index, status, productName = '', channels = '', error = '') {
        const messageItem = document.getElementById(`message-item-${index}`);
        const statusElement = document.getElementById(`status-${index}`);
        const productNameElement = document.getElementById(`product-name-${index}`);
        const channelsElement = document.getElementById(`channels-${index}`);
        const timeElement = document.getElementById(`time-${index}`);

        if (!messageItem || !statusElement) return;

        // Update product name if provided
        if (productName && productNameElement) {
            productNameElement.textContent = productName;
        }

        // Update time
        if (timeElement) {
            const now = new Date();
            timeElement.textContent = now.toLocaleTimeString().substring(0, 5);
        }

        // Remove old status classes
        messageItem.className = 'message-item';
        statusElement.className = 'message-status';

        switch (status) {
            case 'sending':
                messageItem.classList.add('sending');
                statusElement.classList.add('sending');
                statusElement.textContent = '⏳';
                if (channelsElement) {
                    channelsElement.textContent = channels || 'Sending...';
                }
                break;
            case 'sent':
                messageItem.classList.add('sent');
                statusElement.classList.add('sent');
                statusElement.textContent = '✅';
                if (channelsElement) {
                    channelsElement.textContent = channels || 'Posted successfully';
                }
                break;
            case 'waiting':
                messageItem.classList.add('waiting');
                statusElement.classList.add('waiting');
                statusElement.textContent = '⏸️';
                if (channelsElement) {
                    channelsElement.textContent = 'Rate limit - waiting...';
                }
                break;
            case 'error':
                messageItem.classList.add('error');
                statusElement.classList.add('error');
                statusElement.textContent = '❌';
                if (channelsElement) {
                    channelsElement.textContent = error || 'Failed to send';
                }
                break;
        }
    }

    /**
     * Update overall progress status
     */
    updateProgressStatus(completed, total, status = '') {
        const statusElement = document.getElementById('progress-status');
        const countsElement = document.getElementById('progress-counts');

        if (statusElement && status) {
            statusElement.textContent = status;
        }
        
        if (countsElement) {
            countsElement.textContent = `(${completed}/${total})`;
        }
    }

    /**
     * Handle bulk post WebSocket events
     */
    onBulkPostEvent(message) {
        console.log('Bulk post event received:', message);
        
        switch (message.type) {
            case 'bulk_post_started':
                this.handleBulkPostStarted(message);
                break;
            case 'bulk_post_product_start':
                this.handleBulkPostProductStart(message);
                break;
            case 'bulk_post_product_success':
                this.handleBulkPostProductSuccess(message);
                break;
            case 'bulk_post_product_error':
                this.handleBulkPostProductError(message);
                break;
            case 'bulk_post_completed':
                this.handleBulkPostCompleted(message);
                break;
        }
    }

    /**
     * Handle bulk post started event
     */
    handleBulkPostStarted(message) {
        const { total_products, channels } = message;
        
        // Initialize progress display
        this.initializeProgress(total_products);
        this.updateProgressStatus(0, total_products, 'Bulk posting started...');
        
        console.log(`Bulk posting started: ${total_products} products to ${channels.length} channels`);
    }

    /**
     * Handle product start event
     */
    handleBulkPostProductStart(message) {
        const { product_index, product_name, channels } = message;
        const channelNames = channels.join(', ');
        
        this.updateMessageStatus(product_index, 'sending', product_name, `Posting to ${channelNames}`);
        this.updateProgressStatus(product_index - 1, this.totalProducts, `Posting ${product_name}...`);
    }

    /**
     * Handle product success event
     */
    handleBulkPostProductSuccess(message) {
        const { product_index, product_name, posts_created, channels_posted } = message;
        
        this.updateMessageStatus(product_index, 'sent', product_name, `Posted successfully (${posts_created} posts)`);
        this.updateProgressStatus(product_index, this.totalProducts, `${product_name} posted successfully`);
    }

    /**
     * Handle product error event
     */
    handleBulkPostProductError(message) {
        const { product_index, product_name, error } = message;
        
        this.updateMessageStatus(product_index, 'error', product_name, '', error);
        this.updateProgressStatus(product_index, this.totalProducts, `${product_name} failed`);
    }

    /**
     * Handle bulk post completed event
     */
    handleBulkPostCompleted(message) {
        const { total_products, posted_count, failed_count } = message;
        
        // Stop timer
        this.stopTimer();
        
        this.updateProgressStatus(posted_count, total_products, 'Bulk posting completed!');
        
        // Show notification
        this.showNotification(`Bulk posting completed: ${posted_count} posted, ${failed_count} failed`, 'success');
        
        // Refresh products and unposted count
        this.loadProducts();
        this.updateUnpostedCount();
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
        // Show error via console since app might not be fully initialized
        alert(`Application initialization failed: ${error.message}`);
    }
});

// Global refresh function for debugging
window.refreshData = () => {
    if (window.app) {
        window.app.refresh();
    }
};