// Column Configuration Module for VIParser frontend

class ColumnConfigManager {
    constructor() {
        this.defaultColumns = [
            { id: 'select', name: 'Select', visible: true, fixed: true },
            { id: 'id', name: 'ID', visible: true, sortable: true },
            { id: 'images', name: 'Images', visible: true },
            { id: 'name', name: 'Name', visible: true, sortable: true },
            { id: 'sku', name: 'SKU', visible: true, sortable: true },
            { id: 'price', name: 'Price', visible: true, sortable: true },
            { id: 'selling_price', name: 'Selling Price', visible: true, sortable: true },
            { id: 'availability', name: 'Availability', visible: true, sortable: true },
            { id: 'color', name: 'Color', visible: true, sortable: true },
            { id: 'composition', name: 'Composition', visible: false, sortable: true },
            { id: 'item', name: 'Item', visible: false, sortable: true },
            { id: 'sizes', name: 'Sizes', visible: true },
            { id: 'comment', name: 'Comment', visible: false, sortable: true },
            { id: 'created_at', name: 'Created', visible: true, sortable: true },
            { id: 'product_url', name: 'URL', visible: false }
        ];
        
        this.currentColumns = [];
        this.isLoading = false;
        this.draggedElement = null;
        this.dragOverElement = null;
        
        // Bind methods
        this.init = this.init.bind(this);
        this.openModal = this.openModal.bind(this);
        this.closeModal = this.closeModal.bind(this);
        this.loadConfiguration = this.loadConfiguration.bind(this);
        this.saveConfiguration = this.saveConfiguration.bind(this);
        this.renderColumnList = this.renderColumnList.bind(this);
        this.updatePreview = this.updatePreview.bind(this);
        this.resetToDefault = this.resetToDefault.bind(this);
        this.showAllColumns = this.showAllColumns.bind(this);
    }

    /**
     * Initialize column configuration
     */
    init() {
        console.log('Initializing column configuration...');
        this.setupEventListeners();
        this.loadConfiguration();
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Column configuration button
        const configBtn = document.getElementById('configure-columns');
        if (configBtn) {
            configBtn.addEventListener('click', this.openModal);
        }

        // Modal controls
        const modal = document.getElementById('column-config-modal');
        if (modal) {
            // Close button
            const closeBtn = modal.querySelector('#column-config-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', this.closeModal);
            }

            // Cancel button
            const cancelBtn = modal.querySelector('#column-config-cancel');
            if (cancelBtn) {
                cancelBtn.addEventListener('click', this.closeModal);
            }

            // Save button
            const saveBtn = modal.querySelector('#column-config-save');
            if (saveBtn) {
                saveBtn.addEventListener('click', this.saveConfiguration);
            }

            // Reset button
            const resetBtn = modal.querySelector('#reset-columns');
            if (resetBtn) {
                resetBtn.addEventListener('click', this.resetToDefault);
            }

            // Show all button
            const showAllBtn = modal.querySelector('#show-all-columns');
            if (showAllBtn) {
                showAllBtn.addEventListener('click', this.showAllColumns);
            }

            // Click outside to close
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal();
                }
            });
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
                this.closeModal();
            }
        });
    }

    /**
     * Open column configuration modal
     */
    openModal() {
        const modal = document.getElementById('column-config-modal');
        if (modal) {
            modal.classList.remove('hidden');
            document.body.classList.add('modal-open');
            this.renderColumnList();
            this.updatePreview();
        }
    }

    /**
     * Close column configuration modal
     */
    closeModal() {
        const modal = document.getElementById('column-config-modal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.classList.remove('modal-open');
        }
    }

    /**
     * Load column configuration from local storage
     */
    loadConfiguration() {
        try {
            const saved = localStorage.getItem('viparser_column_config');
            if (saved) {
                const config = JSON.parse(saved);
                this.currentColumns = this.validateAndMergeConfig(config);
            } else {
                this.currentColumns = [...this.defaultColumns];
            }
            
            console.log('Loaded column configuration:', this.currentColumns);
            this.applyConfiguration();
        } catch (error) {
            console.error('Error loading column configuration:', error);
            this.currentColumns = [...this.defaultColumns];
            this.applyConfiguration();
        }
    }

    /**
     * Validate and merge saved config with default columns
     */
    validateAndMergeConfig(savedConfig) {
        const merged = [];
        const savedMap = new Map(savedConfig.map(col => [col.id, col]));
        
        // First, add columns in the saved order
        for (const savedCol of savedConfig) {
            const defaultCol = this.defaultColumns.find(col => col.id === savedCol.id);
            if (defaultCol) {
                merged.push({
                    ...defaultCol,
                    visible: savedCol.visible !== undefined ? savedCol.visible : defaultCol.visible
                });
            }
        }
        
        // Then, add any new default columns that weren't in the saved config
        for (const defaultCol of this.defaultColumns) {
            if (!savedMap.has(defaultCol.id)) {
                merged.push({ ...defaultCol });
            }
        }
        
        return merged;
    }

    /**
     * Save column configuration to local storage
     */
    async saveConfiguration() {
        try {
            const config = this.currentColumns.map(col => ({
                id: col.id,
                visible: col.visible
            }));
            
            localStorage.setItem('viparser_column_config', JSON.stringify(config));
            console.log('Saved column configuration:', config);
            
            this.applyConfiguration();
            this.closeModal();
            
            // Show success feedback
            showSuccess('Column configuration saved successfully');
            
        } catch (error) {
            console.error('Error saving column configuration:', error);
            showError('Failed to save column configuration');
        }
    }

    /**
     * Apply column configuration to the table
     */
    applyConfiguration() {
        const table = document.getElementById('products-table');
        if (!table) return;

        const thead = table.querySelector('thead tr');
        const tbody = table.querySelector('tbody');
        
        if (!thead) return;

        // Create a style element for column visibility
        let styleElement = document.getElementById('column-config-styles');
        if (!styleElement) {
            styleElement = document.createElement('style');
            styleElement.id = 'column-config-styles';
            document.head.appendChild(styleElement);
        }

        // Generate CSS rules for column visibility
        let css = '';
        
        // First, hide all columns
        css += `#products-table th, #products-table td { display: none; }\n`;
        
        // Then show visible columns
        this.currentColumns.forEach((column) => {
            if (column.visible) {
                const selector = column.id === 'select' ? '.select-column' : `[data-column="${column.id}"]`;
                css += `#products-table th${selector}, #products-table td${selector} { 
                    display: table-cell; 
                }\n`;
            }
        });

        // Apply the generated CSS
        styleElement.textContent = css;

        // Reorder columns by actually moving DOM elements
        this.reorderTableColumns(thead, tbody);

        console.log('Applied column configuration to table');
    }

    /**
     * Physically reorder table columns by moving DOM elements
     */
    reorderTableColumns(thead, tbody) {
        // Get current order of visible columns
        const visibleColumns = this.currentColumns.filter(col => col.visible);
        
        // Reorder header cells
        const headerCells = Array.from(thead.children);
        const newHeaderOrder = [];
        
        visibleColumns.forEach(column => {
            const selector = column.id === 'select' ? '.select-column' : `[data-column="${column.id}"]`;
            const cell = headerCells.find(cell => 
                cell.matches(selector) || 
                (column.id === 'select' && cell.classList.contains('select-column'))
            );
            if (cell) {
                newHeaderOrder.push(cell);
            }
        });

        // Remove all header cells and re-append in new order
        headerCells.forEach(cell => cell.remove());
        newHeaderOrder.forEach(cell => thead.appendChild(cell));

        // Reorder body cells for each row
        const bodyRows = Array.from(tbody.children);
        bodyRows.forEach(row => {
            const bodyCells = Array.from(row.children);
            const newBodyOrder = [];
            
            visibleColumns.forEach(column => {
                const selector = column.id === 'select' ? '.select-column' : `[data-column="${column.id}"]`;
                const cell = bodyCells.find(cell => 
                    cell.matches(selector) || 
                    (column.id === 'select' && cell.classList.contains('select-column'))
                );
                if (cell) {
                    newBodyOrder.push(cell);
                }
            });

            // Remove all body cells and re-append in new order
            bodyCells.forEach(cell => cell.remove());
            newBodyOrder.forEach(cell => row.appendChild(cell));
        });
    }

    /**
     * Render the column list in the modal
     */
    renderColumnList() {
        const container = document.getElementById('column-list');
        if (!container) return;

        container.innerHTML = this.currentColumns.map((column, index) => `
            <div class="column-item" data-column-id="${column.id}" data-index="${index}">
                <div class="column-info">
                    <span class="column-drag-handle" title="Drag to reorder">⋮⋮</span>
                    <div>
                        <div class="column-name">${column.name}</div>
                        ${column.fixed ? '<div class="column-description">Required column</div>' : ''}
                    </div>
                </div>
                <div class="column-visibility">
                    <label class="visibility-toggle">
                        <input type="checkbox" ${column.visible ? 'checked' : ''} 
                               ${column.fixed ? 'disabled' : ''} 
                               onchange="window.columnConfig.toggleColumnVisibility('${column.id}')">
                        <span class="toggle-slider"></span>
                    </label>
                </div>
            </div>
        `).join('');

        this.setupDragAndDrop();
        this.updateVisibilityCount();
    }

    /**
     * Set up drag and drop functionality
     */
    setupDragAndDrop() {
        const container = document.getElementById('column-list');
        if (!container) return;

        const items = container.querySelectorAll('.column-item');
        
        items.forEach(item => {
            item.draggable = true;
            
            item.addEventListener('dragstart', (e) => {
                this.draggedElement = item;
                item.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
            });

            item.addEventListener('dragend', (e) => {
                item.classList.remove('dragging');
                this.draggedElement = null;
                this.clearDragStyles();
            });

            item.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                
                if (this.draggedElement && item !== this.draggedElement) {
                    this.dragOverElement = item;
                    item.classList.add('drag-over');
                }
            });

            item.addEventListener('dragleave', (e) => {
                item.classList.remove('drag-over');
            });

            item.addEventListener('drop', (e) => {
                e.preventDefault();
                
                if (this.draggedElement && item !== this.draggedElement) {
                    this.reorderColumns(this.draggedElement, item);
                }
                
                this.clearDragStyles();
            });
        });
    }

    /**
     * Reorder columns based on drag and drop
     */
    reorderColumns(draggedItem, targetItem) {
        const draggedIndex = parseInt(draggedItem.dataset.index);
        const targetIndex = parseInt(targetItem.dataset.index);
        
        if (draggedIndex === targetIndex) return;

        // Move the column in the array
        const draggedColumn = this.currentColumns[draggedIndex];
        this.currentColumns.splice(draggedIndex, 1);
        this.currentColumns.splice(targetIndex, 0, draggedColumn);

        // Re-render the list
        this.renderColumnList();
        this.updatePreview();
    }

    /**
     * Clear drag and drop styles
     */
    clearDragStyles() {
        const items = document.querySelectorAll('.column-item');
        items.forEach(item => {
            item.classList.remove('dragging', 'drag-over');
        });
    }

    /**
     * Toggle column visibility
     */
    toggleColumnVisibility(columnId) {
        const column = this.currentColumns.find(col => col.id === columnId);
        if (column && !column.fixed) {
            column.visible = !column.visible;
            this.updatePreview();
            this.updateVisibilityCount();
        }
    }

    /**
     * Update the preview table
     */
    updatePreview() {
        const previewHeaders = document.getElementById('preview-headers');
        if (!previewHeaders) return;

        const visibleColumns = this.currentColumns.filter(col => col.visible);
        
        previewHeaders.innerHTML = visibleColumns.map(column => 
            `<th>${column.name}</th>`
        ).join('');
    }

    /**
     * Update visibility count display
     */
    updateVisibilityCount() {
        const countElement = document.getElementById('visible-columns-count');
        if (!countElement) return;

        const visibleCount = this.currentColumns.filter(col => col.visible).length;
        const totalCount = this.currentColumns.length;
        
        countElement.textContent = `${visibleCount} of ${totalCount} columns visible`;
    }

    /**
     * Reset to default configuration
     */
    resetToDefault() {
        if (confirm('Reset all columns to default configuration? This will undo all your customizations.')) {
            this.currentColumns = [...this.defaultColumns];
            this.renderColumnList();
            this.updatePreview();
        }
    }

    /**
     * Show all columns
     */
    showAllColumns() {
        this.currentColumns.forEach(column => {
            if (!column.fixed) {
                column.visible = true;
            }
        });
        
        this.renderColumnList();
        this.updatePreview();
    }

    /**
     * Get current column configuration
     */
    getConfiguration() {
        return [...this.currentColumns];
    }

    /**
     * Get visible columns
     */
    getVisibleColumns() {
        return this.currentColumns.filter(col => col.visible);
    }
}

// Create global instance
window.columnConfig = new ColumnConfigManager();

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (window.columnConfig) {
        window.columnConfig.init();
    }
});