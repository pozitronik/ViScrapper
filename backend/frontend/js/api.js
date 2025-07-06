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
     * Delete product by ID (with optional mode)
     */
    async deleteProduct(id, deleteMode = 'soft') {
        const params = { delete_mode: deleteMode };
        const queryString = this.buildQueryString(params);
        return await this.request(`/products/${id}${queryString}`, {
            method: 'DELETE'
        });
    }

    /**
     * Get deleted products with pagination
     */
    async getDeletedProducts(page = 1, perPage = 20) {
        const params = { page, per_page: perPage };
        const queryString = this.buildQueryString(params);
        return await this.request(`/products/deleted${queryString}`);
    }

    /**
     * Restore deleted product by ID
     */
    async restoreProduct(id) {
        return await this.request(`/products/${id}/restore`, {
            method: 'POST'
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

    // Template Management API methods

    /**
     * Get all templates
     */
    async getTemplates() {
        return await this.request('/templates');
    }

    /**
     * Get template by ID
     */
    async getTemplate(id) {
        return await this.request(`/templates/${id}`);
    }

    /**
     * Create new template
     */
    async createTemplate(templateData) {
        return await this.request('/templates', {
            method: 'POST',
            body: JSON.stringify(templateData)
        });
    }

    /**
     * Update template by ID
     */
    async updateTemplate(id, templateData) {
        return await this.request(`/templates/${id}`, {
            method: 'PUT',
            body: JSON.stringify(templateData)
        });
    }

    /**
     * Delete template by ID
     */
    async deleteTemplate(id) {
        return await this.request(`/templates/${id}`, {
            method: 'DELETE'
        });
    }
}

// Create global API client instance
const api = new ApiClient();

// Export for use in other modules
window.api = api;