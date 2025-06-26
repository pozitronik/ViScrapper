// Pagination functionality for the products table

class Pagination {
    constructor(containerId, onPageChange) {
        this.container = document.getElementById(containerId);
        this.onPageChange = onPageChange;
        this.currentPage = 1;
        this.totalPages = 1;
        this.totalItems = 0;
        this.itemsPerPage = 20;
    }

    /**
     * Update pagination data and render
     */
    update(paginationData) {
        this.currentPage = paginationData.page;
        this.totalPages = paginationData.pages;
        this.totalItems = paginationData.total;
        this.itemsPerPage = paginationData.per_page;
        this.hasNext = paginationData.has_next;
        this.hasPrev = paginationData.has_prev;
        
        this.render();
    }

    /**
     * Render pagination controls
     */
    render() {
        if (this.totalPages <= 1) {
            this.container.innerHTML = '';
            return;
        }

        const paginationHtml = `
            <div class="pagination">
                ${this.createPrevButton()}
                ${this.createPageNumbers()}
                ${this.createNextButton()}
            </div>
            <div class="pagination-info">
                ${this.createPaginationInfo()}
            </div>
        `;

        this.container.innerHTML = paginationHtml;
        this.attachEventListeners();
    }

    /**
     * Create previous button
     */
    createPrevButton() {
        const disabled = !this.hasPrev ? 'disabled' : '';
        return `
            <button class="pagination-btn" data-page="${this.currentPage - 1}" ${disabled}>
                &laquo; Previous
            </button>
        `;
    }

    /**
     * Create next button
     */
    createNextButton() {
        const disabled = !this.hasNext ? 'disabled' : '';
        return `
            <button class="pagination-btn" data-page="${this.currentPage + 1}" ${disabled}>
                Next &raquo;
            </button>
        `;
    }

    /**
     * Create page number buttons
     */
    createPageNumbers() {
        const pages = this.getVisiblePages();
        
        return pages.map(page => {
            if (page === '...') {
                return '<span class="pagination-ellipsis">...</span>';
            }
            
            const active = page === this.currentPage ? 'active' : '';
            return `
                <button class="pagination-btn ${active}" data-page="${page}">
                    ${page}
                </button>
            `;
        }).join('');
    }

    /**
     * Get visible page numbers with ellipsis
     */
    getVisiblePages() {
        const pages = [];
        const maxVisible = 7; // Maximum number of page buttons to show
        
        if (this.totalPages <= maxVisible) {
            // Show all pages if total is small
            for (let i = 1; i <= this.totalPages; i++) {
                pages.push(i);
            }
        } else {
            // Always show first page
            pages.push(1);
            
            let start = Math.max(2, this.currentPage - 2);
            let end = Math.min(this.totalPages - 1, this.currentPage + 2);
            
            // Add ellipsis after first page if needed
            if (start > 2) {
                pages.push('...');
            }
            
            // Add middle pages
            for (let i = start; i <= end; i++) {
                pages.push(i);
            }
            
            // Add ellipsis before last page if needed
            if (end < this.totalPages - 1) {
                pages.push('...');
            }
            
            // Always show last page
            if (this.totalPages > 1) {
                pages.push(this.totalPages);
            }
        }
        
        return pages;
    }

    /**
     * Create pagination info text
     */
    createPaginationInfo() {
        const start = (this.currentPage - 1) * this.itemsPerPage + 1;
        const end = Math.min(this.currentPage * this.itemsPerPage, this.totalItems);
        
        return `Showing ${start}-${end} of ${this.totalItems} products`;
    }

    /**
     * Attach event listeners to pagination buttons
     */
    attachEventListeners() {
        const buttons = this.container.querySelectorAll('.pagination-btn[data-page]');
        
        buttons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                
                if (button.disabled) return;
                
                const page = parseInt(button.dataset.page);
                if (page && page !== this.currentPage && page >= 1 && page <= this.totalPages) {
                    this.goToPage(page);
                }
            });
        });
    }

    /**
     * Navigate to specific page
     */
    goToPage(page) {
        if (page >= 1 && page <= this.totalPages && page !== this.currentPage) {
            this.currentPage = page;
            this.onPageChange(page);
        }
    }

    /**
     * Go to next page
     */
    nextPage() {
        if (this.hasNext) {
            this.goToPage(this.currentPage + 1);
        }
    }

    /**
     * Go to previous page
     */
    prevPage() {
        if (this.hasPrev) {
            this.goToPage(this.currentPage - 1);
        }
    }

    /**
     * Go to first page
     */
    firstPage() {
        this.goToPage(1);
    }

    /**
     * Go to last page
     */
    lastPage() {
        this.goToPage(this.totalPages);
    }
}

// Export for use in other modules
window.Pagination = Pagination;