// Main application controller for VIParser frontend

class VIParserApp {
    constructor() {
        this.currentPage = 1;
        this.itemsPerPage = 20;
        this.isLoading = false;
        
        // Initialize components
        this.table = new ProductTable('products-table', this.onDataChange.bind(this));
        this.pagination = new Pagination('pagination', this.onPageChange.bind(this));
        
        // Bind methods
        this.loadProducts = this.loadProducts.bind(this);
        this.retryLoad = this.retryLoad.bind(this);
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
            const response = await api.getProducts({
                page,
                perPage: this.itemsPerPage,
                sortBy: 'created_at',
                sortOrder: 'desc'
            });

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