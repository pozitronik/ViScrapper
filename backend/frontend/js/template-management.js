// Template Management Module for VIParser frontend

class TemplateManager {
    constructor() {
        this.templates = [];
        this.currentTemplate = null;
        this.isLoading = false;
        this.availablePlaceholders = null;
        
        // Bind methods
        this.init = this.init.bind(this);
        this.openTemplateModal = this.openTemplateModal.bind(this);
        this.closeTemplateModal = this.closeTemplateModal.bind(this);
        this.openTemplateEditor = this.openTemplateEditor.bind(this);
        this.closeTemplateEditor = this.closeTemplateEditor.bind(this);
        this.loadTemplates = this.loadTemplates.bind(this);
        this.saveTemplate = this.saveTemplate.bind(this);
        this.deleteTemplate = this.deleteTemplate.bind(this);
        this.validateTemplateForm = this.validateTemplateForm.bind(this);
        this.generatePreview = this.generatePreview.bind(this);
        this.searchTemplates = this.searchTemplates.bind(this);
    }

    /**
     * Initialize template management
     */
    init() {
        console.log('Initializing template management...');
        this.setupEventListeners();
        // Don't load templates immediately - wait for user to open modal
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        // Templates button in main interface
        const templatesBtn = document.getElementById('manage-templates'); console.log('Templates button found:', templatesBtn);
        if (templatesBtn) {
            templatesBtn.addEventListener('click', (e) => { console.log('Templates button clicked!'); this.openTemplateModal(e); });
        }

        // Template modal controls
        const templateModal = document.getElementById('template-management-modal');
        if (templateModal) {
            // Close button
            const closeBtn = templateModal.querySelector('#template-management-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', this.closeTemplateModal);
            }

            // Cancel button
            const cancelBtn = templateModal.querySelector('#template-management-cancel');
            if (cancelBtn) {
                cancelBtn.addEventListener('click', this.closeTemplateModal);
            }

            // Add template button
            const addBtn = templateModal.querySelector('#add-template');
            if (addBtn) {
                addBtn.addEventListener('click', () => this.openTemplateEditor());
            }

            // Search input
            const searchInput = templateModal.querySelector('#template-search');
            if (searchInput) {
                searchInput.addEventListener('input', 
                    debounce((e) => this.searchTemplates(e.target.value), 300)
                );
            }

            // Click outside to close
            templateModal.addEventListener('click', (e) => {
                if (e.target === templateModal) {
                    this.closeTemplateModal();
                }
            });
        }

        // Template editor modal controls
        const editorModal = document.getElementById('template-editor-modal');
        if (editorModal) {
            // Close button
            const closeBtn = editorModal.querySelector('#template-editor-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', this.closeTemplateEditor);
            }

            // Cancel button  
            const cancelBtn = editorModal.querySelector('#template-editor-cancel');
            if (cancelBtn) {
                cancelBtn.addEventListener('click', this.closeTemplateEditor);
            }

            // Save button
            const saveBtn = editorModal.querySelector('#template-save');
            if (saveBtn) {
                saveBtn.addEventListener('click', this.saveTemplate);
            }

            // Form inputs for real-time validation
            const nameInput = editorModal.querySelector('#template-name-input');
            const contentInput = editorModal.querySelector('#template-content-input');
            
            if (nameInput) {
                nameInput.addEventListener('input', this.validateTemplateForm);
            }
            
            if (contentInput) {
                contentInput.addEventListener('input', () => {
                    this.validateTemplateForm();
                    this.generatePreview();
                });
            }

            // Template editor tool buttons
            const showPlaceholdersBtn = editorModal.querySelector('#show-template-placeholders');
            const previewBtn = editorModal.querySelector('#preview-template');
            const validateBtn = editorModal.querySelector('#validate-template');
            
            console.log('Found editor buttons:', { showPlaceholdersBtn, previewBtn, validateBtn });
            
            if (showPlaceholdersBtn) {
                showPlaceholdersBtn.addEventListener('click', this.togglePlaceholders.bind(this));
            }
            
            if (previewBtn) {
                previewBtn.addEventListener('click', this.showPreview.bind(this));
            }
            
            if (validateBtn) {
                validateBtn.addEventListener('click', this.validateTemplate.bind(this));
            }

            // Keyboard shortcuts help button
            const keyboardShortcutsBtn = editorModal.querySelector('#show-keyboard-shortcuts');
            if (keyboardShortcutsBtn) {
                keyboardShortcutsBtn.addEventListener('click', this.showKeyboardShortcuts.bind(this));
            }

            // Placeholders search functionality
            const placeholdersSearchInput = editorModal.querySelector('#placeholders-search-input');
            if (placeholdersSearchInput) {
                placeholdersSearchInput.addEventListener('input', 
                    debounce((e) => this.filterPlaceholders(e.target.value), 300)
                );
                
                // Clear search on Escape
                placeholdersSearchInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Escape') {
                        e.target.value = '';
                        this.filterPlaceholders('');
                        contentInput?.focus();
                    }
                });
            }

            // Global keyboard shortcuts for template editor
            editorModal.addEventListener('keydown', (e) => {
                // Ctrl+S or Cmd+S to save
                if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                    e.preventDefault();
                    this.saveTemplate();
                }
                
                // Escape to close modal
                if (e.key === 'Escape' && e.target === editorModal) {
                    this.closeTemplateEditor();
                }
                
                // Ctrl+/ or Cmd+/ to toggle placeholders
                if ((e.ctrlKey || e.metaKey) && e.key === '/') {
                    e.preventDefault();
                    this.togglePlaceholders();
                }
                
                // Ctrl+Enter or Cmd+Enter to show preview
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                    e.preventDefault();
                    this.showPreview();
                }
            });

            // Click outside to close
            editorModal.addEventListener('click', (e) => {
                if (e.target === editorModal) {
                    this.closeTemplateEditor();
                }
            });
        }
    }

    /**
     * Open template management modal
     */
    async openTemplateModal() {
        const modal = document.getElementById('template-management-modal');
        if (modal) {
            modal.classList.remove('hidden');
            document.body.classList.add('modal-open');
            
            // Load templates if not already loaded
            await this.loadTemplates();
            
            // Set up event delegation for template actions
            this.setupTemplateActionsEventDelegation();
        }
    }

    /**
     * Close template management modal
     */
    closeTemplateModal() {
        const modal = document.getElementById('template-management-modal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.classList.remove('modal-open');
        }
    }

    /**
     * Open template editor modal
     */
    openTemplateEditor(template = null) {
        const modal = document.getElementById('template-editor-modal');
        if (modal) {
            // Set current template
            this.currentTemplate = template;
            
            // Populate form if editing
            const nameInput = modal.querySelector('#template-name-input');
            const descriptionInput = modal.querySelector('#template-description-input');
            const contentInput = modal.querySelector('#template-content-input');
            const modalTitle = modal.querySelector('.modal-title');
            const saveBtn = modal.querySelector('#template-save');
            
            if (template) {
                // Editing existing template
                if (modalTitle) modalTitle.textContent = 'Edit Template';
                if (saveBtn) saveBtn.textContent = 'Save Changes';
                if (nameInput) nameInput.value = template.name || '';
                if (descriptionInput) descriptionInput.value = template.description || '';
                if (contentInput) contentInput.value = template.template_content || '';
            } else {
                // Creating new template
                if (modalTitle) modalTitle.textContent = 'Create Template';
                if (saveBtn) saveBtn.textContent = 'Create Template';
                if (nameInput) nameInput.value = '';
                if (descriptionInput) descriptionInput.value = '';
                if (contentInput) contentInput.value = '';
            }
            
            modal.classList.remove('hidden');
            
            // Focus on name input
            if (nameInput) {
                nameInput.focus();
            }
            
            // Generate initial preview
            this.generatePreview();
            this.validateTemplateForm();
            
            // Set up event delegation for placeholders
            this.setupPlaceholdersEventDelegation();
        }
    }

    /**
     * Close template editor modal
     */
    closeTemplateEditor() {
        const modal = document.getElementById('template-editor-modal');
        if (modal) {
            modal.classList.add('hidden');
            this.currentTemplate = null;
        }
    }

    /**
     * Load templates from API
     */
    async loadTemplates() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        
        try {
            console.log('Loading templates...');
            const response = await api.getTemplates();
            this.templates = response.data || response || [];
            console.log(`Loaded ${this.templates.length} templates`);
            
            this.renderTemplates();
            
        } catch (error) {
            console.error('Failed to load templates:', error);
            showError(`Failed to load templates: ${error.message}`);
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Render templates in the modal
     */
    renderTemplates(filteredTemplates = null) {
        const container = document.querySelector('#template-list-container');
        if (!container) return;
        
        const templatesToRender = filteredTemplates || this.templates;
        
        if (templatesToRender.length === 0) {
            container.innerHTML = `
                <div class="template-empty">
                    <p>No templates found</p>
                    <button class="btn btn-primary add-template-btn">Create First Template</button>
                </div>
            `;
            
            // Re-attach event listener for the button
            const addBtn = container.querySelector('.add-template-btn');
            if (addBtn) {
                addBtn.addEventListener('click', () => this.openTemplateEditor());
            }
            
            return;
        }
        
        container.innerHTML = templatesToRender.map(template => `
            <div class="template-item" data-template-id="${template.id}">
                <div class="template-info">
                    <h4 class="template-name">${escapeHtml(template.name)}</h4>
                    <p class="template-description">${escapeHtml(template.description || 'No description')}</p>
                    <div class="template-meta">
                        <span class="template-date">Created: ${formatDate(template.created_at)}</span>
                        <span class="template-usage">Used: ${template.usage_count || 0} times</span>
                    </div>
                </div>
                <div class="template-actions">
                    <button class="btn btn-sm btn-secondary edit-btn" data-template-id="${template.id}">Edit</button>
                    <button class="btn btn-sm btn-danger delete-btn" data-template-id="${template.id}">Delete</button>
                </div>
            </div>
        `).join('');
    }

    /**
     * Search templates
     */
    searchTemplates(query) {
        if (!query.trim()) {
            this.renderTemplates();
            return;
        }
        
        const filteredTemplates = this.templates.filter(template => 
            template.name.toLowerCase().includes(query.toLowerCase()) ||
            (template.description && template.description.toLowerCase().includes(query.toLowerCase()))
        );
        
        this.renderTemplates(filteredTemplates);
    }

    /**
     * Validate template form
     */
    validateTemplateForm() {
        const modal = document.getElementById('template-editor-modal');
        if (!modal) return false;
        
        const nameInput = modal.querySelector('#template-name-input');
        const contentInput = modal.querySelector('#template-content-input');
        const saveBtn = modal.querySelector('#template-save');
        
        const name = nameInput?.value?.trim() || '';
        const content = contentInput?.value?.trim() || '';
        
        const isValid = name.length > 0 && content.length > 0;
        
        console.log('Validation check:', { name, content, isValid });
        
        if (saveBtn) {
            saveBtn.disabled = !isValid;
        }
        
        return isValid;
    }

    /**
     * Generate template preview
     */
    generatePreview() {
        const modal = document.getElementById('template-editor-modal');
        if (!modal) return;
        
        const contentInput = modal.querySelector('#template-content-input');
        const previewContainer = modal.querySelector('.template-preview');
        
        if (!contentInput || !previewContainer) return;
        
        const content = contentInput.value.trim();
        
        if (!content) {
            previewContainer.innerHTML = '<p class="preview-placeholder">Enter template content to see preview</p>';
            return;
        }
        
        // Sample product data for preview
        const sampleProduct = {
            name: 'Sample Product Name',
            sku: 'SKU12345',
            price: '99.99',
            sell_price: '129.99',
            currency: 'USD',
            availability: 'In Stock',
            color: 'Blue',
            composition: 'Cotton 100%',
            item: 'Shirt',
            store: 'Victoria\'s Secret',
            comment: 'Sample comment',
            product_url: 'https://example.com/product',
            size: 'S, M, L, XL',
            sizes: 'S, M, L, XL'
        };
        
        // Replace placeholders with sample data
        let preview = content;
        Object.keys(sampleProduct).forEach(key => {
            const placeholder = `{${key}}`;
            preview = preview.replace(new RegExp(placeholder, 'g'), sampleProduct[key]);
        });
        
        // Convert line breaks to HTML
        preview = preview.replace(/\n/g, '<br>');
        
        previewContainer.innerHTML = `<div class="preview-content">${preview}</div>`;
    }

    /**
     * Save template
     */
    async saveTemplate() {
        if (!this.validateTemplateForm()) {
            showError('Please fill in all required fields');
            return;
        }
        
        const modal = document.getElementById('template-editor-modal');
        if (!modal) return;
        
        const nameInput = modal.querySelector('#template-name-input');
        const descriptionInput = modal.querySelector('#template-description-input');
        const contentInput = modal.querySelector('#template-content-input');
        const saveBtn = modal.querySelector('#template-save');
        
        const templateData = {
            name: nameInput.value.trim(),
            description: descriptionInput.value.trim(),
            template_content: contentInput.value.trim(),
            is_active: true
        };
        
        console.log('Sending template data:', templateData);
        
        // Disable save button during save
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.textContent = 'Saving...';
        }
        
        try {
            let savedTemplate;
            
            if (this.currentTemplate) {
                // Update existing template
                console.log('Updating template:', this.currentTemplate.id);
                const response = await api.updateTemplate(this.currentTemplate.id, templateData);
                savedTemplate = response.data || response;
                
                // Update in local array
                const index = this.templates.findIndex(t => t.id === this.currentTemplate.id);
                if (index !== -1) {
                    this.templates[index] = savedTemplate;
                }
                
                showSuccess('Template updated successfully');
            } else {
                // Create new template
                console.log('Creating new template');
                const response = await api.createTemplate(templateData);
                savedTemplate = response.data || response;
                
                console.log('Created template response:', savedTemplate);
                
                // Add to local array
                this.templates.unshift(savedTemplate);
                
                showSuccess('Template created successfully');
            }
            
            // Reload templates from server to ensure fresh data
            await this.loadTemplates();
            
            // Close editor
            this.closeTemplateEditor();
            
        } catch (error) {
            console.error('Failed to save template:', error);
            showError(`Failed to save template: ${error.message}`);
        } finally {
            // Re-enable save button with correct text
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = this.currentTemplate ? 'Save Changes' : 'Create Template';
            }
        }
    }

    /**
     * Delete template
     */
    async deleteTemplate(templateId) {
        const template = this.templates.find(t => t.id === templateId);
        if (!template) return;
        
        const confirmed = confirm(`Are you sure you want to delete the template "${template.name}"?`);
        if (!confirmed) return;
        
        try {
            console.log('Deleting template:', templateId);
            await api.deleteTemplate(templateId);
            
            // Remove from local array
            this.templates = this.templates.filter(t => t.id !== templateId);
            
            // Reload templates from server to ensure fresh data
            await this.loadTemplates();
            
            showSuccess('Template deleted successfully');
            
        } catch (error) {
            console.error('Failed to delete template:', error);
            showError(`Failed to delete template: ${error.message}`);
        }
    }

    /**
     * Get template by ID
     */
    getTemplate(templateId) {
        return this.templates.find(t => t.id === templateId);
    }

    /**
     * Get all templates
     */
    getTemplates() {
        return this.templates;
    }

    /**
     * Toggle placeholder help visibility
     */
    togglePlaceholders() {
        const helpSection = document.getElementById('template-placeholders-help');
        const btn = document.getElementById('show-template-placeholders');
        
        if (helpSection && btn) {
            const isHidden = helpSection.classList.contains('hidden');
            
            if (isHidden) {
                helpSection.classList.remove('hidden');
                btn.textContent = '📋 Hide Placeholders';
                this.loadPlaceholders();
            } else {
                helpSection.classList.add('hidden');
                btn.textContent = '📋 Show Placeholders';
            }
        }
    }

    /**
     * Load available placeholders
     */
    async loadPlaceholders() {
        const container = document.getElementById('template-placeholders-list');
        if (!container) return;
        
        try {
            // Fetch placeholders from backend
            const response = await fetch('/api/v1/templates/placeholders/available');
            const data = await response.json();
            
            if (data && data.data && data.data.placeholders) {
                // Convert object to array and sort
                this.availablePlaceholders = Object.entries(data.data.placeholders).map(([key, description]) => ({
                    key: key.replace(/[{}]/g, ''), // Remove braces for display
                    description
                })).sort((a, b) => a.key.localeCompare(b.key));
            } else {
                throw new Error('Invalid response format');
            }
        } catch (error) {
            console.error('Failed to load placeholders:', error);
            
            // Fallback to basic placeholders
            this.availablePlaceholders = [
                { key: 'name', description: 'Product name' },
                { key: 'sku', description: 'Product SKU' },
                { key: 'price', description: 'Product price' },
                { key: 'sell_price', description: 'Product sell price (calculated)' },
                { key: 'currency', description: 'Price currency' },
                { key: 'availability', description: 'Product availability' },
                { key: 'color', description: 'Product color' },
                { key: 'composition', description: 'Product composition' },
                { key: 'item', description: 'Product item type' },
                { key: 'store', description: 'Store or brand name' },
                { key: 'comment', description: 'Product comment' },
                { key: 'size', description: 'Size information (formatted for display)' },
                { key: 'sizes', description: 'Available sizes (comma-separated)' },
                { key: 'product_url', description: 'Product URL' },
                { key: 'created_at', description: 'Creation date' }
            ];
        }
        
        // Render placeholders
        this.renderPlaceholders();
    }

    /**
     * Render placeholders in the container
     */
    renderPlaceholders(filteredPlaceholders = null) {
        const container = document.getElementById('template-placeholders-list');
        if (!container) return;
        
        const placeholdersToRender = filteredPlaceholders || this.availablePlaceholders || [];
        
        if (placeholdersToRender.length === 0) {
            container.innerHTML = '<div class="placeholders-empty">No placeholders found</div>';
            return;
        }
        
        container.innerHTML = placeholdersToRender.map(placeholder => `
            <div class="placeholder-item" data-placeholder="{${placeholder.key}}">
                <code>{${placeholder.key}}</code>
                <span>${placeholder.description}</span>
            </div>
        `).join('');
    }

    /**
     * Set up event delegation for placeholder items to prevent memory leaks
     */
    setupPlaceholdersEventDelegation() {
        const container = document.getElementById('template-placeholders-list');
        if (!container) return;
        
        // Remove existing event listener if any
        container.removeEventListener('click', this.handlePlaceholderClick);
        
        // Add single delegated event listener
        this.handlePlaceholderClick = (e) => {
            const item = e.target.closest('.placeholder-item');
            if (item) {
                const placeholder = item.dataset.placeholder;
                this.insertPlaceholderAtCursor(placeholder);
                
                // Visual feedback
                item.classList.add('clicked');
                setTimeout(() => {
                    item.classList.remove('clicked');
                }, 500);
            }
        };
        
        container.addEventListener('click', this.handlePlaceholderClick);
    }

    /**
     * Set up event delegation for template action buttons to prevent memory leaks
     */
    setupTemplateActionsEventDelegation() {
        const container = document.getElementById('template-list-container');
        if (!container) return;
        
        // Remove existing event listener if any
        container.removeEventListener('click', this.handleTemplateActionClick);
        
        // Add single delegated event listener
        this.handleTemplateActionClick = (e) => {
            const editBtn = e.target.closest('.edit-btn');
            const deleteBtn = e.target.closest('.delete-btn');
            
            if (editBtn) {
                const templateId = parseInt(editBtn.dataset.templateId);
                const template = this.templates.find(t => t.id === templateId);
                if (template) {
                    this.openTemplateEditor(template);
                }
            } else if (deleteBtn) {
                const templateId = parseInt(deleteBtn.dataset.templateId);
                this.deleteTemplate(templateId);
            }
        };
        
        container.addEventListener('click', this.handleTemplateActionClick);
    }

    /**
     * Filter placeholders based on search query
     */
    filterPlaceholders(query) {
        if (!this.availablePlaceholders) return;
        
        if (!query.trim()) {
            this.renderPlaceholders();
            return;
        }
        
        const filteredPlaceholders = this.availablePlaceholders.filter(placeholder => 
            placeholder.key.toLowerCase().includes(query.toLowerCase()) ||
            placeholder.description.toLowerCase().includes(query.toLowerCase())
        );
        
        this.renderPlaceholders(filteredPlaceholders);
    }

    /**
     * Insert placeholder at cursor position in template content textarea
     */
    insertPlaceholderAtCursor(placeholder) {
        const contentInput = document.getElementById('template-content-input');
        if (!contentInput) return;
        
        const startPos = contentInput.selectionStart;
        const endPos = contentInput.selectionEnd;
        const textBefore = contentInput.value.substring(0, startPos);
        const textAfter = contentInput.value.substring(endPos);
        
        // Insert placeholder
        contentInput.value = textBefore + placeholder + textAfter;
        
        // Set cursor position after the inserted placeholder
        const newCursorPos = startPos + placeholder.length;
        contentInput.setSelectionRange(newCursorPos, newCursorPos);
        
        // Focus back on the textarea
        contentInput.focus();
        
        // Trigger validation and preview update
        this.validateTemplateForm();
        this.generatePreview();
        
        console.log('Inserted placeholder:', placeholder, 'at position:', startPos);
    }

    /**
     * Show keyboard shortcuts help
     */
    showKeyboardShortcuts() {
        const shortcuts = [
            'Ctrl+S (Cmd+S) - Save template',
            'Ctrl+/ (Cmd+/) - Toggle placeholders',
            'Ctrl+Enter (Cmd+Enter) - Show preview',
            'Escape - Clear search or close modal',
            'Click placeholders to insert at cursor'
        ];
        
        alert('Keyboard Shortcuts:\n\n' + shortcuts.join('\n'));
    }

    /**
     * Show template preview in a larger view
     */
    showPreview() {
        const contentInput = document.querySelector('#template-content-input');
        if (!contentInput) return;
        
        const content = contentInput.value.trim();
        if (!content) {
            alert('Please enter some template content first.');
            return;
        }
        
        // Sample product data for preview
        const sampleProduct = {
            name: 'Sample Product Name',
            sku: 'SKU12345',
            price: '99.99',
            sell_price: '129.99',
            currency: 'USD',
            availability: 'In Stock',
            color: 'Blue',
            composition: 'Cotton 100%',
            item: 'Shirt',
            store: 'Victoria\'s Secret',
            comment: 'Sample comment',
            product_url: 'https://example.com/product',
            created_at: new Date().toISOString(),
            size: 'S, M, L, XL',
            sizes: 'S, M, L, XL'
        };
        
        // Replace placeholders with sample data
        let preview = content;
        Object.keys(sampleProduct).forEach(key => {
            const placeholder = `{${key}}`;
            preview = preview.replace(new RegExp(placeholder, 'g'), sampleProduct[key]);
        });
        
        // Show in alert for now (could be enhanced with a modal)
        alert('Template Preview:\n\n' + preview);
    }

    /**
     * Validate template content
     */
    async validateTemplate() {
        console.log('Validate button clicked!');
        const nameInput = document.querySelector('#template-name-input');
        const contentInput = document.querySelector('#template-content-input');
        
        console.log('Found elements:', { nameInput, contentInput });
        
        if (!nameInput || !contentInput) {
            console.log('Could not find required elements');
            alert('Error: Could not find form elements');
            return;
        }
        
        const name = nameInput.value.trim();
        const content = contentInput.value.trim();
        
        const errors = [];
        
        if (!name) {
            errors.push('Template name is required');
        }
        
        if (!content) {
            errors.push('Template content is required');
        }
        
        try {
            // Use backend validation
            const response = await fetch(`/api/v1/templates/validate?template_content=${encodeURIComponent(content)}`, {
                method: 'POST'
            });
            
            const data = await response.json();
            const validationData = data.data || data;
            
            if (validationData.is_valid) {
                if (errors.length === 0) {
                    alert('✅ Template validation passed!\n\nNo errors found.');
                } else {
                    alert('❌ Template validation failed:\n\n' + errors.join('\n'));
                }
            } else {
                // Add placeholder validation errors
                if (validationData.invalid_placeholders && validationData.invalid_placeholders.length > 0) {
                    validationData.invalid_placeholders.forEach(placeholder => {
                        errors.push(`Invalid placeholder: ${placeholder}`);
                    });
                }
                
                alert('❌ Template validation failed:\n\n' + errors.join('\n'));
            }
        } catch (error) {
            console.error('Validation request failed:', error);
            
            // Fallback to basic validation
            const placeholderPattern = /\{([^}]+)\}/g;
            const validPlaceholders = ['name', 'sku', 'price', 'sell_price', 'currency', 'availability', 'color', 'composition', 'item', 'store', 'comment', 'size', 'sizes', 'product_url', 'created_at'];
            const matches = content.matchAll(placeholderPattern);
            
            for (const match of matches) {
                const placeholder = match[1];
                if (!validPlaceholders.includes(placeholder)) {
                    errors.push(`Invalid placeholder: {${placeholder}}`);
                }
            }
            
            if (errors.length === 0) {
                alert('✅ Template validation passed!\n\nNo errors found.');
            } else {
                alert('❌ Template validation failed:\n\n' + errors.join('\n'));
            }
        }
    }
}

// Helper functions
function formatDate(dateString) {
    if (!dateString) return 'Unknown';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (error) {
        return 'Invalid date';
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Create global template manager instance
window.templateManager = new TemplateManager();

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (window.templateManager) {
        window.templateManager.init();
    }
});