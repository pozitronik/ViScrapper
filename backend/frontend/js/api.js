// API client for VIParser backend communication

class ApiClient {
    constructor(baseUrl = '/api/v1') {
        this.baseUrl = baseUrl;
    }

    /**
     * Make HTTP request with error handling
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, { ...defaultOptions, ...options });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => null);
                throw new Error(
                    errorData?.error?.message || 
                    `HTTP ${response.status}: ${response.statusText}`
                );
            }

            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    /**
     * Build query string from parameters
     */
    buildQueryString(params) {
        const searchParams = new URLSearchParams();
        
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
                searchParams.append(key, String(value));
            }
        });
        
        const queryString = searchParams.toString();
        return queryString ? `?${queryString}` : '';
    }

    /**
     * Get products with pagination and filtering
     */
    async getProducts(options = {}) {
        const {
            page = 1,
            perPage = 20,
            sortBy = 'created_at',
            sortOrder = 'desc',
            search = '',
            ...filters
        } = options;

        const params = {
            page,
            per_page: perPage,
            sort_by: sortBy,
            sort_order: sortOrder,
            ...filters
        };

        // Add search parameter if provided
        if (search) {
            params.q = search;
        }

        const queryString = this.buildQueryString(params);
        return await this.request(`/products${queryString}`);
    }

    /**
     * Get single product by ID
     */
    async getProduct(id) {
        return await this.request(`/products/${id}`);
    }

    /**
     * Update product by ID
     */
    async updateProduct(id, updateData) {
        return await this.request(`/products/${id}`, {
            method: 'PUT',
            body: JSON.stringify(updateData)
        });
    }

    /**
     * Get product statistics
     */
    async getProductStats() {
        return await this.request('/products/stats');
    }

    /**
     * Get recent products
     */
    async getRecentProducts(limit = 10) {
        const queryString = this.buildQueryString({ limit });
        return await this.request(`/products/recent${queryString}`);
    }

    /**
     * Search products
     */
    async searchProducts(query, page = 1, perPage = 20) {
        const params = { q: query, page, per_page: perPage };
        const queryString = this.buildQueryString(params);
        return await this.request(`/products/search${queryString}`);
    }

    /**
     * Health check
     */
    async checkHealth() {
        return await this.request('/health');
    }

    /**
     * Test connection
     */
    async testConnection() {
        try {
            await this.checkHealth();
            return true;
        } catch {
            return false;
        }
    }
}

// Create global API client instance
const api = new ApiClient();

// Export for use in other modules
window.api = api;