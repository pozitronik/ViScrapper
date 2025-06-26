// Utility functions for the VIParser frontend

/**
 * Format currency value
 */
function formatCurrency(value, currency = 'USD') {
    if (value === null || value === undefined || isNaN(value)) {
        return '';
    }
    
    try {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency.toUpperCase(),
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(value);
    } catch {
        return `${value.toFixed(2)} ${currency}`;
    }
}

/**
 * Format date to readable string
 */
function formatDate(dateString, options = {}) {
    if (!dateString) return '';
    
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return '';
        
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        
        return new Intl.DateTimeFormat('en-US', { ...defaultOptions, ...options }).format(date);
    } catch {
        return '';
    }
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
function formatRelativeTime(dateString) {
    if (!dateString) return '';
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) return 'just now';
        if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} min ago`;
        if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
        if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 86400)} days ago`;
        
        return formatDate(dateString, { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
        return '';
    }
}

/**
 * Truncate text to specified length
 */
function truncateText(text, maxLength = 50) {
    if (!text || text.length <= maxLength) return text;
    return text.slice(0, maxLength - 3) + '...';
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show/hide loading state
 */
function showLoading(show = true) {
    const loading = document.getElementById('loading');
    const tableContainer = document.getElementById('table-container');
    const error = document.getElementById('error');
    
    if (show) {
        loading.classList.remove('hidden');
        tableContainer.classList.add('hidden');
        error.classList.add('hidden');
    } else {
        loading.classList.add('hidden');
        tableContainer.classList.remove('hidden');
    }
}

/**
 * Show error state
 */
function showError(message) {
    const loading = document.getElementById('loading');
    const tableContainer = document.getElementById('table-container');
    const error = document.getElementById('error');
    const errorMessage = document.getElementById('error-message');
    
    loading.classList.add('hidden');
    tableContainer.classList.add('hidden');
    error.classList.remove('hidden');
    errorMessage.textContent = message;
}

/**
 * Create DOM element with attributes and content
 */
function createElement(tag, attributes = {}, content = '') {
    const element = document.createElement(tag);
    
    Object.entries(attributes).forEach(([key, value]) => {
        if (key === 'className') {
            element.className = value;
        } else if (key === 'dataset') {
            Object.entries(value).forEach(([dataKey, dataValue]) => {
                element.dataset[dataKey] = dataValue;
            });
        } else {
            element.setAttribute(key, value);
        }
    });
    
    if (content) {
        if (typeof content === 'string') {
            element.innerHTML = content;
        } else {
            element.appendChild(content);
        }
    }
    
    return element;
}

/**
 * Debounce function for search and other frequent operations
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Get availability class for styling
 */
function getAvailabilityClass(availability) {
    if (!availability) return '';
    
    const lower = availability.toLowerCase();
    if (lower.includes('in stock') || lower.includes('available')) {
        return 'availability-in-stock';
    } else if (lower.includes('out of stock') || lower.includes('unavailable')) {
        return 'availability-out-of-stock';
    } else if (lower.includes('limited') || lower.includes('low stock')) {
        return 'availability-limited';
    }
    return '';
}