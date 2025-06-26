// Row selection and mass operations for product table

class RowSelection {
    constructor(onSelectionChange, onDeleteSelected, onExportSelected) {
        this.onSelectionChange = onSelectionChange;
        this.onDeleteSelected = onDeleteSelected;
        this.onExportSelected = onExportSelected;
        this.selectedRows = new Set();
        this.allProducts = [];
        
        // Get DOM elements
        this.selectAllCheckbox = document.getElementById('select-all');
        this.selectionInfo = document.getElementById('selection-info');
        this.selectionCount = document.getElementById('selection-count');
        this.deleteSelectedBtn = document.getElementById('delete-selected');
        this.exportSelectedBtn = document.getElementById('export-selected');
        this.clearSelectionBtn = document.getElementById('clear-selection');
        
        this.setupEventListeners();
    }

    /**
     * Set up event listeners for selection controls
     */
    setupEventListeners() {
        // Select all checkbox
        if (this.selectAllCheckbox) {
            this.selectAllCheckbox.addEventListener('change', (e) => {
                this.toggleSelectAll(e.target.checked);
            });
        }

        // Mass operation buttons
        if (this.deleteSelectedBtn) {
            this.deleteSelectedBtn.addEventListener('click', () => {
                this.handleDeleteSelected();
            });
        }

        if (this.exportSelectedBtn) {
            this.exportSelectedBtn.addEventListener('click', () => {
                this.handleExportSelected();
            });
        }

        if (this.clearSelectionBtn) {
            this.clearSelectionBtn.addEventListener('click', () => {
                this.clearSelection();
            });
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl+A to select all
            if ((e.ctrlKey || e.metaKey) && e.key === 'a' && !this.isInputFocused()) {
                e.preventDefault();
                this.selectAll();
            }
            
            // Delete key to delete selected
            if (e.key === 'Delete' && this.selectedRows.size > 0 && !this.isInputFocused()) {
                e.preventDefault();
                this.handleDeleteSelected();
            }
            
            // Escape to clear selection
            if (e.key === 'Escape' && this.selectedRows.size > 0) {
                this.clearSelection();
            }
        });
    }

    /**
     * Initialize selection for table rows
     */
    initializeTable(tableElement, products) {
        this.table = tableElement;
        this.allProducts = products;
        this.addCheckboxesToRows();
    }

    /**
     * Add event listeners to existing checkboxes in table rows
     */
    addCheckboxesToRows() {
        if (!this.table) return;

        const rows = this.table.querySelectorAll('tbody tr');
        rows.forEach((row, index) => {
            const productId = parseInt(row.dataset.productId);
            if (!productId) return;

            // Find existing checkbox in the row
            const checkbox = row.querySelector('.row-checkbox');
            if (checkbox) {
                // Remove any existing event listeners and add new one
                checkbox.removeEventListener('change', this.handleCheckboxChange);
                checkbox.addEventListener('change', (e) => {
                    this.toggleRowSelection(productId, e.target.checked);
                });
            }
        });
    }

    /**
     * Toggle selection for a specific row
     */
    toggleRowSelection(productId, selected) {
        const row = this.table.querySelector(`tr[data-product-id="${productId}"]`);
        const checkbox = this.table.querySelector(`input[data-product-id="${productId}"]`);

        if (selected) {
            this.selectedRows.add(productId);
            if (row) row.classList.add('selected');
            if (checkbox) checkbox.checked = true;
        } else {
            this.selectedRows.delete(productId);
            if (row) row.classList.remove('selected');
            if (checkbox) checkbox.checked = false;
        }

        this.updateSelectionState();
    }

    /**
     * Toggle select all functionality
     */
    toggleSelectAll(selectAll) {
        if (selectAll) {
            this.selectAll();
        } else {
            this.clearSelection();
        }
    }

    /**
     * Select all visible rows
     */
    selectAll() {
        this.allProducts.forEach(product => {
            this.selectedRows.add(product.id);
        });

        // Update UI
        const checkboxes = this.table.querySelectorAll('.row-checkbox');
        const rows = this.table.querySelectorAll('tbody tr');
        
        checkboxes.forEach(checkbox => checkbox.checked = true);
        rows.forEach(row => row.classList.add('selected'));
        
        if (this.selectAllCheckbox) {
            this.selectAllCheckbox.checked = true;
        }

        this.updateSelectionState();
    }

    /**
     * Clear all selections
     */
    clearSelection() {
        this.selectedRows.clear();

        // Update UI
        const checkboxes = this.table.querySelectorAll('.row-checkbox');
        const rows = this.table.querySelectorAll('tbody tr');
        
        checkboxes.forEach(checkbox => checkbox.checked = false);
        rows.forEach(row => row.classList.remove('selected'));
        
        if (this.selectAllCheckbox) {
            this.selectAllCheckbox.checked = false;
        }

        this.updateSelectionState();
    }

    /**
     * Update selection state and UI
     */
    updateSelectionState() {
        const selectedCount = this.selectedRows.size;
        const totalCount = this.allProducts.length;

        // Update selection info
        if (this.selectionCount) {
            this.selectionCount.textContent = `${selectedCount} selected`;
        }

        // Show/hide selection info bar
        if (this.selectionInfo) {
            if (selectedCount > 0) {
                this.selectionInfo.classList.remove('hidden');
            } else {
                this.selectionInfo.classList.add('hidden');
            }
        }

        // Update select all checkbox state
        if (this.selectAllCheckbox) {
            if (selectedCount === 0) {
                this.selectAllCheckbox.checked = false;
                this.selectAllCheckbox.indeterminate = false;
            } else if (selectedCount === totalCount) {
                this.selectAllCheckbox.checked = true;
                this.selectAllCheckbox.indeterminate = false;
            } else {
                this.selectAllCheckbox.checked = false;
                this.selectAllCheckbox.indeterminate = true;
            }
        }

        // Enable/disable action buttons
        const hasSelection = selectedCount > 0;
        if (this.deleteSelectedBtn) {
            this.deleteSelectedBtn.disabled = !hasSelection;
        }
        if (this.exportSelectedBtn) {
            this.exportSelectedBtn.disabled = !hasSelection;
        }

        // Notify listeners
        if (this.onSelectionChange) {
            this.onSelectionChange(Array.from(this.selectedRows), this.getSelectedProducts());
        }
    }

    /**
     * Get selected product objects
     */
    getSelectedProducts() {
        return this.allProducts.filter(product => this.selectedRows.has(product.id));
    }

    /**
     * Get selected product IDs
     */
    getSelectedIds() {
        return Array.from(this.selectedRows);
    }

    /**
     * Handle delete selected action
     */
    async handleDeleteSelected() {
        const selectedCount = this.selectedRows.size;
        if (selectedCount === 0) return;

        const confirmed = confirm(
            `Are you sure you want to delete ${selectedCount} selected product${selectedCount > 1 ? 's' : ''}? This action cannot be undone.`
        );

        if (confirmed && this.onDeleteSelected) {
            const selectedIds = this.getSelectedIds();
            try {
                await this.onDeleteSelected(selectedIds);
                this.clearSelection();
            } catch (error) {
                console.error('Failed to delete selected products:', error);
                alert('Failed to delete some products. Please try again.');
            }
        }
    }

    /**
     * Handle export selected action
     */
    async handleExportSelected() {
        if (this.selectedRows.size === 0) return;

        if (this.onExportSelected) {
            const selectedProducts = this.getSelectedProducts();
            try {
                await this.onExportSelected(selectedProducts);
            } catch (error) {
                console.error('Failed to export selected products:', error);
                alert('Failed to export products. Please try again.');
            }
        }
    }

    /**
     * Update products data when table changes
     */
    updateProducts(products) {
        this.allProducts = products;
        
        // Remove selections for products that no longer exist
        const currentIds = new Set(products.map(p => p.id));
        const selectedIds = Array.from(this.selectedRows);
        
        selectedIds.forEach(id => {
            if (!currentIds.has(id)) {
                this.selectedRows.delete(id);
            }
        });

        this.updateSelectionState();
    }

    /**
     * Check if an input element is currently focused
     */
    isInputFocused() {
        const activeElement = document.activeElement;
        return activeElement && (
            activeElement.tagName === 'INPUT' ||
            activeElement.tagName === 'TEXTAREA' ||
            activeElement.tagName === 'SELECT' ||
            activeElement.isContentEditable
        );
    }

    /**
     * Select products by IDs
     */
    selectProducts(productIds) {
        productIds.forEach(id => {
            this.selectedRows.add(id);
        });
        
        // Update UI
        productIds.forEach(id => {
            const row = this.table.querySelector(`tr[data-product-id="${id}"]`);
            const checkbox = this.table.querySelector(`input[data-product-id="${id}"]`);
            
            if (row) row.classList.add('selected');
            if (checkbox) checkbox.checked = true;
        });

        this.updateSelectionState();
    }

    /**
     * Get selection statistics
     */
    getSelectionStats() {
        return {
            selectedCount: this.selectedRows.size,
            totalCount: this.allProducts.length,
            selectedIds: Array.from(this.selectedRows),
            allSelected: this.selectedRows.size === this.allProducts.length && this.allProducts.length > 0
        };
    }
}

// Export for use in other modules
window.RowSelection = RowSelection;