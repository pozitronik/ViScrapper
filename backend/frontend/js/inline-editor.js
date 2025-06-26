// Inline editing functionality for product table

class InlineEditor {
    constructor(onUpdateProduct) {
        this.onUpdateProduct = onUpdateProduct;
        this.currentlyEditing = null;
        this.originalValue = null;
        
        // Define which fields are editable and their types
        this.editableFields = {
            'name': { type: 'text', required: true },
            'sku': { type: 'text', required: false },
            'price': { type: 'number', required: false, step: '0.01', min: '0' },
            'availability': { type: 'select', options: ['In Stock', 'Out of Stock', 'Limited'] },
            'color': { type: 'text', required: false },
            'comment': { type: 'textarea', required: false }
        };
    }

    /**
     * Initialize inline editing for a table
     */
    initializeTable(tableElement) {
        this.table = tableElement;
        this.setupEventListeners();
    }

    /**
     * Set up global event listeners
     */
    setupEventListeners() {
        // Click outside to cancel editing
        document.addEventListener('click', (e) => {
            if (this.currentlyEditing && !this.isEditingElement(e.target)) {
                this.cancelEdit();
            }
        });

        // Escape key to cancel editing
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.currentlyEditing) {
                this.cancelEdit();
            }
            if (e.key === 'Enter' && this.currentlyEditing && !e.shiftKey) {
                e.preventDefault();
                this.saveEdit();
            }
        });
    }

    /**
     * Make a cell editable
     */
    makeEditable(cell, productId, field, currentValue) {
        if (!this.editableFields[field]) return;

        // Add editable class and click handler
        cell.classList.add('cell-editable');
        
        // Add edit indicator
        const indicator = createElement('div', { className: 'edit-indicator' });
        cell.appendChild(indicator);

        cell.addEventListener('click', (e) => {
            e.stopPropagation();
            this.startEdit(cell, productId, field, currentValue);
        });
    }

    /**
     * Start editing a cell
     */
    startEdit(cell, productId, field, currentValue) {
        // Cancel any existing edit
        if (this.currentlyEditing) {
            this.cancelEdit();
        }

        this.currentlyEditing = {
            cell,
            productId,
            field,
            originalValue: currentValue
        };

        // Store original content
        const originalContent = cell.innerHTML;
        
        // Create editor based on field type
        const editor = this.createEditor(field, currentValue);
        
        // Replace cell content
        cell.innerHTML = '';
        cell.classList.add('cell-editing');
        cell.appendChild(editor.element);

        // Create action buttons
        const actions = this.createEditActions();
        cell.appendChild(actions);

        // Focus the editor
        if (editor.focusElement) {
            editor.focusElement.focus();
            if (editor.focusElement.select) {
                editor.focusElement.select();
            }
        }

        // Store references for cleanup
        this.currentlyEditing.editor = editor;
        this.currentlyEditing.originalContent = originalContent;
    }

    /**
     * Create appropriate editor for field type
     */
    createEditor(field, currentValue) {
        const config = this.editableFields[field];
        let element, focusElement;

        switch (config.type) {
            case 'text':
                element = createElement('input', {
                    type: 'text',
                    className: 'cell-editor',
                    value: currentValue || '',
                    required: config.required
                });
                focusElement = element;
                break;

            case 'number':
                element = createElement('input', {
                    type: 'number',
                    className: 'cell-editor',
                    value: currentValue || '',
                    step: config.step,
                    min: config.min,
                    required: config.required
                });
                focusElement = element;
                break;

            case 'textarea':
                element = createElement('textarea', {
                    className: 'cell-editor cell-editor-textarea',
                    required: config.required
                });
                element.value = currentValue || '';
                focusElement = element;
                break;

            case 'select':
                element = createElement('select', {
                    className: 'cell-editor cell-editor-select',
                    required: config.required
                });
                
                // Add options
                config.options.forEach(option => {
                    const optionEl = createElement('option', {
                        value: option,
                        selected: option === currentValue
                    }, option);
                    element.appendChild(optionEl);
                });
                focusElement = element;
                break;

            default:
                throw new Error(`Unknown editor type: ${config.type}`);
        }

        return { element, focusElement };
    }

    /**
     * Create save/cancel action buttons
     */
    createEditActions() {
        const actions = createElement('div', { className: 'edit-actions' });

        const saveBtn = createElement('button', {
            className: 'edit-btn edit-btn-save',
            title: 'Save (Enter)'
        }, '✓');

        const cancelBtn = createElement('button', {
            className: 'edit-btn edit-btn-cancel',
            title: 'Cancel (Esc)'
        }, '✕');

        saveBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.saveEdit();
        });

        cancelBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.cancelEdit();
        });

        actions.appendChild(saveBtn);
        actions.appendChild(cancelBtn);

        return actions;
    }

    /**
     * Save the current edit
     */
    async saveEdit() {
        if (!this.currentlyEditing) return;

        const { cell, productId, field, editor } = this.currentlyEditing;
        const newValue = this.getEditorValue(editor.focusElement);

        // Validate the new value
        if (!this.validateValue(field, newValue)) {
            this.showValidationError(cell, 'Invalid value');
            return;
        }

        try {
            // Show loading state
            this.showSavingState(cell);

            // Call update function
            if (this.onUpdateProduct) {
                await this.onUpdateProduct(productId, field, newValue);
            }

            // Update succeeded - restore cell with new value
            this.restoreCell(cell, this.formatDisplayValue(field, newValue));
            
            // Show success animation
            cell.classList.add('cell-updated');
            
            this.currentlyEditing = null;

        } catch (error) {
            console.error('Failed to update product:', error);
            this.showValidationError(cell, 'Failed to save changes');
        }
    }

    /**
     * Cancel the current edit
     */
    cancelEdit() {
        if (!this.currentlyEditing) return;

        const { cell, originalContent } = this.currentlyEditing;
        
        // Restore original content
        cell.innerHTML = originalContent;
        cell.classList.remove('cell-editing');

        this.currentlyEditing = null;
    }

    /**
     * Get value from editor element
     */
    getEditorValue(element) {
        if (element.type === 'number') {
            return element.value ? parseFloat(element.value) : null;
        }
        return element.value.trim();
    }

    /**
     * Validate field value
     */
    validateValue(field, value) {
        const config = this.editableFields[field];
        
        // Check required fields
        if (config.required && (!value || value === '')) {
            return false;
        }

        // Type-specific validation
        if (config.type === 'number' && value !== null && value !== '') {
            return !isNaN(value) && isFinite(value);
        }

        return true;
    }

    /**
     * Format value for display
     */
    formatDisplayValue(field, value) {
        if (value === null || value === undefined || value === '') {
            return '<span class="text-muted">-</span>';
        }

        switch (field) {
            case 'price':
                return `<span class="cell-price">${formatCurrency(value)}</span>`;
            case 'availability':
                const availabilityClass = getAvailabilityClass(value);
                return `<span class="cell-availability ${availabilityClass}">${escapeHtml(value)}</span>`;
            case 'name':
                return `<span class="cell-name" title="${escapeHtml(value)}">${escapeHtml(value)}</span>`;
            default:
                return `<span title="${escapeHtml(value)}">${escapeHtml(value)}</span>`;
        }
    }

    /**
     * Show saving state
     */
    showSavingState(cell) {
        const actions = cell.querySelector('.edit-actions');
        if (actions) {
            actions.innerHTML = '<span style="color: #6b7280; font-size: 0.75rem;">Saving...</span>';
        }
    }

    /**
     * Show validation error
     */
    showValidationError(cell, message) {
        const actions = cell.querySelector('.edit-actions');
        if (actions) {
            actions.innerHTML = `<span style="color: #dc2626; font-size: 0.75rem;">${message}</span>`;
            
            // Restore buttons after 2 seconds
            setTimeout(() => {
                if (this.currentlyEditing && this.currentlyEditing.cell === cell) {
                    const newActions = this.createEditActions();
                    actions.replaceWith(newActions);
                }
            }, 2000);
        }
    }

    /**
     * Restore cell to non-editing state
     */
    restoreCell(cell, newContent) {
        cell.innerHTML = newContent;
        cell.classList.remove('cell-editing');
        
        // Re-add edit indicator
        const indicator = createElement('div', { className: 'edit-indicator' });
        cell.appendChild(indicator);
    }

    /**
     * Check if element is part of editing interface
     */
    isEditingElement(element) {
        return element.closest('.cell-editing') || 
               element.classList.contains('cell-editor') ||
               element.closest('.edit-actions');
    }

    /**
     * Get list of editable fields
     */
    getEditableFields() {
        return Object.keys(this.editableFields);
    }

    /**
     * Check if field is editable
     */
    isFieldEditable(field) {
        return this.editableFields.hasOwnProperty(field);
    }
}

// Export for use in other modules
window.InlineEditor = InlineEditor;