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
            'composition': { type: 'textarea', required: false },
            'item': { type: 'text', required: false },
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
            if (e.key === 'Enter' && this.currentlyEditing) {
                const config = this.editableFields[this.currentlyEditing.field];
                const isOverlay = this.currentlyEditing.isOverlay;
                
                // For textarea fields (now handled by overlay), only save with Ctrl+Enter
                if (config && config.type === 'textarea') {
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.saveEdit();
                    }
                    // Otherwise let Enter create new line
                } else {
                    // For other fields, save with Enter (unless Shift is held)
                    if (!e.shiftKey) {
                        e.preventDefault();
                        this.saveEdit();
                    }
                }
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
        
        // Get field configuration
        const config = this.editableFields[field];
        
        // Check if this is a textarea field that needs overlay editing
        if (config && config.type === 'textarea') {
            this.startOverlayEdit(cell, productId, field, currentValue, originalContent);
        } else {
            this.startInlineEdit(cell, productId, field, currentValue, originalContent, config);
        }
    }

    /**
     * Start inline editing for simple fields
     */
    startInlineEdit(cell, productId, field, currentValue, originalContent, config) {
        // Create editor based on field type
        const editor = this.createEditor(field, currentValue);
        
        // Replace cell content
        cell.innerHTML = '';
        cell.classList.add('cell-editing');
        cell.appendChild(editor.element);

        // Create action buttons
        const actions = this.createEditActions(field);
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
     * Start overlay editing for textarea fields
     */
    startOverlayEdit(cell, productId, field, currentValue, originalContent) {
        // Mark cell as being edited with overlay
        cell.classList.add('cell-editing-overlay');
        
        // Create overlay editor
        const overlay = this.createOverlayEditor(field, currentValue);
        document.body.appendChild(overlay);
        
        // Position overlay near the cell
        this.positionOverlay(overlay, cell);
        
        // Focus the textarea
        const textarea = overlay.querySelector('.editor-overlay-textarea');
        if (textarea) {
            textarea.focus();
            textarea.select();
        }
        
        // Store references for cleanup
        this.currentlyEditing.editor = { element: overlay };
        this.currentlyEditing.originalContent = originalContent;
        this.currentlyEditing.isOverlay = true;
    }

    /**
     * Create overlay editor for textarea fields
     */
    createOverlayEditor(field, currentValue) {
        const overlay = createElement('div', { className: 'editor-overlay' });
        
        // Header
        const header = createElement('div', { className: 'editor-overlay-header' });
        const title = createElement('div', { className: 'editor-overlay-title' });
        title.textContent = `Edit ${field.charAt(0).toUpperCase() + field.slice(1)}`;
        
        const closeBtn = createElement('button', { 
            className: 'editor-overlay-close',
            title: 'Close (Esc)'
        }, '×');
        
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.cancelEdit();
        });
        
        header.appendChild(title);
        header.appendChild(closeBtn);
        
        // Body
        const body = createElement('div', { className: 'editor-overlay-body' });
        const textarea = createElement('textarea', { 
            className: 'editor-overlay-textarea',
            placeholder: `Enter ${field}...`
        });
        textarea.value = currentValue || '';
        body.appendChild(textarea);
        
        // Footer
        const footer = createElement('div', { className: 'editor-overlay-footer' });
        const shortcuts = createElement('div', { className: 'editor-overlay-shortcuts' });
        shortcuts.textContent = 'Ctrl+Enter to save • Esc to cancel';
        
        const actions = createElement('div', { className: 'editor-overlay-actions' });
        
        const saveBtn = createElement('button', { 
            className: 'btn btn-primary btn-sm',
            title: 'Save (Ctrl+Enter)'
        }, 'Save');
        
        const cancelBtn = createElement('button', { 
            className: 'btn btn-outline btn-sm',
            title: 'Cancel (Esc)'
        }, 'Cancel');
        
        saveBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.saveEdit();
        });
        
        cancelBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.cancelEdit();
        });
        
        actions.appendChild(cancelBtn);
        actions.appendChild(saveBtn);
        
        footer.appendChild(shortcuts);
        footer.appendChild(actions);
        
        overlay.appendChild(header);
        overlay.appendChild(body);
        overlay.appendChild(footer);
        
        return overlay;
    }

    /**
     * Position overlay near the cell
     */
    positionOverlay(overlay, cell) {
        const cellRect = cell.getBoundingClientRect();
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        
        // Default positioning
        let left = cellRect.left;
        let top = cellRect.bottom + 10;
        
        // Adjust if overlay would go off-screen horizontally
        const overlayWidth = 400; // Approximate overlay width
        if (left + overlayWidth > viewportWidth) {
            left = viewportWidth - overlayWidth - 20;
        }
        if (left < 20) {
            left = 20;
        }
        
        // Adjust if overlay would go off-screen vertically
        const overlayHeight = 300; // Approximate overlay height
        if (top + overlayHeight > viewportHeight) {
            top = cellRect.top - overlayHeight - 10;
        }
        if (top < 20) {
            top = 20;
        }
        
        overlay.style.left = `${left}px`;
        overlay.style.top = `${top}px`;
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
    createEditActions(field = null) {
        const actions = createElement('div', { className: 'edit-actions' });

        // Determine save shortcut based on field type
        const config = field ? this.editableFields[field] : null;
        const saveShortcut = (config && config.type === 'textarea') ? 'Ctrl+Enter' : 'Enter';

        const saveBtn = createElement('button', {
            className: 'edit-btn edit-btn-save',
            title: `Save (${saveShortcut})`
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

        const { cell, productId, field, editor, isOverlay } = this.currentlyEditing;
        
        // Get value from appropriate editor
        let newValue;
        if (isOverlay) {
            const textarea = editor.element.querySelector('.editor-overlay-textarea');
            newValue = textarea.value.trim();
        } else {
            newValue = this.getEditorValue(editor.focusElement);
        }

        // Validate the new value
        if (!this.validateValue(field, newValue)) {
            if (isOverlay) {
                this.showOverlayValidationError(editor.element, 'Invalid value');
            } else {
                this.showValidationError(cell, 'Invalid value');
            }
            return;
        }

        try {
            // Show loading state
            if (isOverlay) {
                this.showOverlaySavingState(editor.element);
            } else {
                this.showSavingState(cell);
            }

            // Call update function
            if (this.onUpdateProduct) {
                await this.onUpdateProduct(productId, field, newValue);
            }

            // Update succeeded - restore cell with new value
            this.restoreCell(cell, this.formatDisplayValue(field, newValue));
            
            // Clean up overlay if needed
            if (isOverlay) {
                document.body.removeChild(editor.element);
                cell.classList.remove('cell-editing-overlay');
            }
            
            // Show success animation
            cell.classList.add('cell-updated');
            
            this.currentlyEditing = null;

        } catch (error) {
            console.error('Failed to update product:', error);
            if (isOverlay) {
                this.showOverlayValidationError(editor.element, 'Failed to save changes');
            } else {
                this.showValidationError(cell, 'Failed to save changes');
            }
        }
    }

    /**
     * Cancel the current edit
     */
    cancelEdit() {
        if (!this.currentlyEditing) return;

        const { cell, originalContent, editor, isOverlay } = this.currentlyEditing;
        
        if (isOverlay) {
            // Remove overlay
            document.body.removeChild(editor.element);
            cell.classList.remove('cell-editing-overlay');
        } else {
            // Restore original content for inline editing
            cell.innerHTML = originalContent;
            cell.classList.remove('cell-editing');
        }

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
            case 'comment':
                const displayComment = value || '-';
                return `<span class="cell-comment" title="${escapeHtml(value)}">${escapeHtml(displayComment)}</span>`;
            case 'composition':
                if (!value || value === '-') {
                    return '<span class="cell-composition">-</span>';
                }
                return `<span class="cell-composition cell-composition-full">${escapeHtml(value)}</span>`;
            case 'item':
                const displayItem = value || '-';
                return `<span class="cell-item" title="${escapeHtml(value)}">${escapeHtml(displayItem)}</span>`;
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
                    const newActions = this.createEditActions(this.currentlyEditing.field);
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
     * Show overlay saving state
     */
    showOverlaySavingState(overlay) {
        const actions = overlay.querySelector('.editor-overlay-actions');
        if (actions) {
            actions.innerHTML = '<span style="color: #6b7280; font-size: 0.875rem;">Saving...</span>';
        }
    }

    /**
     * Show overlay validation error
     */
    showOverlayValidationError(overlay, message) {
        const actions = overlay.querySelector('.editor-overlay-actions');
        if (actions) {
            actions.innerHTML = `<span style="color: #dc2626; font-size: 0.875rem;">${message}</span>`;
            
            // Restore buttons after 2 seconds
            setTimeout(() => {
                if (this.currentlyEditing && this.currentlyEditing.editor.element === overlay) {
                    const saveBtn = createElement('button', { 
                        className: 'btn btn-primary btn-sm',
                        title: 'Save (Ctrl+Enter)'
                    }, 'Save');
                    
                    const cancelBtn = createElement('button', { 
                        className: 'btn btn-outline btn-sm',
                        title: 'Cancel (Esc)'
                    }, 'Cancel');
                    
                    saveBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        this.saveEdit();
                    });
                    
                    cancelBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        this.cancelEdit();
                    });
                    
                    actions.innerHTML = '';
                    actions.appendChild(cancelBtn);
                    actions.appendChild(saveBtn);
                }
            }, 2000);
        }
    }

    /**
     * Check if element is part of editing interface
     */
    isEditingElement(element) {
        return element.closest('.cell-editing') || 
               element.classList.contains('cell-editor') ||
               element.closest('.edit-actions') ||
               element.closest('.editor-overlay');
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