/**
 * Telegram Modal and Posting Functionality
 * Handles the telegram posting interface with preview capabilities
 */

class TelegramModal {
    constructor() {
        this.modal = null;
        this.selectedProducts = [];
        this.selectedChannels = [];
        this.channels = [];
        this.templates = [];
        this.placeholders = [];
        this.isLoading = false;
        
        this.init();
    }

    init() {
        this.modal = document.getElementById('telegram-modal');
        if (!this.modal) return;

        this.bindEvents();
        this.loadInitialData();
    }

    bindEvents() {
        // Modal open/close
        const telegramBtn = document.getElementById('telegram-selected');
        const closeBtn = document.getElementById('telegram-modal-close');
        const cancelBtn = document.getElementById('telegram-cancel');
        const modalBackdrop = this.modal.querySelector('.modal-backdrop');

        if (telegramBtn) {
            telegramBtn.addEventListener('click', () => this.openModal());
        }

        [closeBtn, cancelBtn, modalBackdrop].forEach(el => {
            if (el) {
                el.addEventListener('click', () => this.closeModal());
            }
        });

        // Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !this.modal.classList.contains('hidden')) {
                this.closeModal();
            }
        });

        // Channel management buttons
        const addChannelBtn = document.getElementById('add-channel');
        const refreshChannels = document.getElementById('refresh-channels');
        const refreshTemplates = document.getElementById('refresh-templates');
        const refreshPreview = document.getElementById('refresh-preview');

        if (addChannelBtn) {
            addChannelBtn.addEventListener('click', () => this.openChannelModal());
        }
        if (refreshChannels) {
            refreshChannels.addEventListener('click', () => this.loadChannels());
        }
        if (refreshTemplates) {
            refreshTemplates.addEventListener('click', () => this.loadTemplates());
        }
        if (refreshPreview) {
            refreshPreview.addEventListener('click', () => this.updatePreview());
        }

        // Template type selection
        const templateTypeRadios = document.querySelectorAll('input[name="template-type"]');
        templateTypeRadios.forEach(radio => {
            radio.addEventListener('change', () => this.onTemplateTypeChange());
        });

        // Template selection
        const templateSelect = document.getElementById('template-select');
        if (templateSelect) {
            templateSelect.addEventListener('change', () => this.updatePreview());
        }

        // Custom template
        const customTemplate = document.getElementById('custom-template');
        if (customTemplate) {
            customTemplate.addEventListener('input', () => this.debouncePreviewUpdate());
        }

        // Placeholders help
        const showPlaceholders = document.getElementById('show-placeholders');
        if (showPlaceholders) {
            showPlaceholders.addEventListener('click', () => this.togglePlaceholders());
        }

        // Post options
        const sendPhotos = document.getElementById('send-photos');
        const disableNotification = document.getElementById('disable-notification');

        [sendPhotos, disableNotification].forEach(el => {
            if (el) {
                el.addEventListener('change', () => this.updatePreview());
            }
        });

        // Send button
        const sendBtn = document.getElementById('telegram-send');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendPosts());
        }
    }

    async loadInitialData() {
        await Promise.all([
            this.loadChannels(),
            this.loadTemplates(),
            this.loadPlaceholders()
        ]);
    }

    async loadChannels() {
        const container = document.getElementById('channels-list');
        const loading = document.getElementById('channels-loading');
        const noChannels = document.getElementById('no-channels');

        this.showElement(loading);
        this.hideElement(container);
        this.hideElement(noChannels);

        try {
            const response = await fetch('/api/v1/telegram/channels?active_only=true');
            const data = await response.json();

            if (data.success && data.data.length > 0) {
                this.channels = data.data;
                this.renderChannels();
                this.showElement(container);
            } else {
                this.showElement(noChannels);
            }
        } catch (error) {
            console.error('Failed to load channels:', error);
            this.showElement(noChannels);
            this.showNotification('Failed to load Telegram channels', 'error');
        } finally {
            this.hideElement(loading);
        }
    }

    renderChannels() {
        const container = document.getElementById('channels-list');
        if (!container) return;

        container.innerHTML = this.channels.map(channel => `
            <div class="channel-item" data-channel-id="${channel.id}">
                <input type="checkbox" id="channel-${channel.id}" value="${channel.id}">
                <label for="channel-${channel.id}" class="channel-content">
                    <div class="channel-name">${this.escapeHtml(channel.name)}</div>
                    <div class="channel-info">
                        <span class="channel-chat-id">${this.escapeHtml(channel.chat_id)}</span>
                        <span class="channel-badge ${channel.auto_post ? 'auto-post' : 'manual'}">
                            ${channel.auto_post ? '🤖 Auto' : '👤 Manual'}
                        </span>
                    </div>
                </label>
                <div class="channel-actions">
                    <button class="channel-action-btn edit" data-channel-id="${channel.id}" title="Edit channel">
                        ✏️
                    </button>
                    <button class="channel-action-btn delete" data-channel-id="${channel.id}" title="Delete channel">
                        🗑️
                    </button>
                </div>
            </div>
        `).join('');

        // Bind channel selection events
        container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => this.onChannelSelectionChange());
        });

        // Bind channel action buttons
        container.querySelectorAll('.channel-action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const channelId = parseInt(btn.dataset.channelId);
                const action = btn.classList.contains('edit') ? 'edit' : 'delete';
                
                if (action === 'edit') {
                    this.editChannel(channelId);
                } else {
                    this.deleteChannel(channelId);
                }
            });
        });

        container.querySelectorAll('.channel-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.type !== 'checkbox' && !e.target.classList.contains('channel-action-btn')) {
                    const checkbox = item.querySelector('input[type="checkbox"]');
                    checkbox.checked = !checkbox.checked;
                    this.onChannelSelectionChange();
                }
            });
        });
    }

    async loadTemplates() {
        const select = document.getElementById('template-select');
        if (!select) return;

        try {
            const response = await fetch('/api/v1/templates?active_only=true');
            const data = await response.json();

            if (data.success) {
                this.templates = data.data;
                select.innerHTML = `
                    <option value="">Select a template...</option>
                    ${this.templates.map(template => 
                        `<option value="${template.id}">${this.escapeHtml(template.name)}</option>`
                    ).join('')}
                `;
            }
        } catch (error) {
            console.error('Failed to load templates:', error);
            select.innerHTML = '<option value="">Failed to load templates</option>';
        }
    }

    async loadPlaceholders() {
        try {
            const response = await fetch('/api/v1/templates/placeholders/available');
            const data = await response.json();

            if (data.success) {
                this.placeholders = data.data.placeholders;
            }
        } catch (error) {
            console.error('Failed to load placeholders:', error);
        }
    }

    onTemplateTypeChange() {
        const selectedType = document.querySelector('input[name="template-type"]:checked')?.value;
        const templateSelect = document.getElementById('template-select');
        const customSection = document.getElementById('custom-template-section');

        // Enable/disable template select
        if (templateSelect) {
            templateSelect.disabled = selectedType !== 'template-select';
        }

        // Show/hide custom template section
        if (customSection) {
            if (selectedType === 'custom') {
                this.showElement(customSection);
            } else {
                this.hideElement(customSection);
            }
        }

        this.updatePreview();
    }

    onChannelSelectionChange() {
        const selectedCheckboxes = document.querySelectorAll('#channels-list input[type="checkbox"]:checked');
        this.selectedChannels = Array.from(selectedCheckboxes).map(cb => parseInt(cb.value));

        // Update UI
        this.updateChannelVisualState();
        this.updateFooterInfo();
        this.updateSendButtonState();
        this.updatePreview();
    }

    updateChannelVisualState() {
        document.querySelectorAll('.channel-item').forEach(item => {
            const checkbox = item.querySelector('input[type="checkbox"]');
            if (checkbox?.checked) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }

    togglePlaceholders() {
        const help = document.getElementById('placeholders-help');
        const btn = document.getElementById('show-placeholders');

        if (help.classList.contains('hidden')) {
            this.renderPlaceholders();
            this.showElement(help);
            if (btn) btn.textContent = '📋 Hide Placeholders';
        } else {
            this.hideElement(help);
            if (btn) btn.textContent = '📋 Show Available Placeholders';
        }
    }

    renderPlaceholders() {
        const container = document.getElementById('placeholders-list');
        if (!container || !this.placeholders.length) return;

        container.innerHTML = this.placeholders.map(placeholder => `
            <div class="placeholder-item" data-placeholder="${placeholder}">
                <span class="placeholder-code">${placeholder}</span>
                <span class="placeholder-desc">Click to insert</span>
            </div>
        `).join('');

        // Bind click events to insert placeholders
        container.querySelectorAll('.placeholder-item').forEach(item => {
            item.addEventListener('click', () => {
                const placeholder = item.dataset.placeholder;
                this.insertPlaceholder(placeholder);
            });
        });
    }

    insertPlaceholder(placeholder) {
        const textarea = document.getElementById('custom-template');
        if (!textarea) return;

        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const text = textarea.value;

        textarea.value = text.substring(0, start) + placeholder + text.substring(end);
        textarea.selectionStart = textarea.selectionEnd = start + placeholder.length;
        textarea.focus();

        this.debouncePreviewUpdate();
    }

    debouncePreviewUpdate() {
        clearTimeout(this.previewTimeout);
        this.previewTimeout = setTimeout(() => this.updatePreview(), 500);
    }

    async updatePreview() {
        if (!this.selectedProducts.length || !this.selectedChannels.length) {
            this.showDefaultPreview();
            return;
        }

        const loading = document.getElementById('preview-loading');
        const container = document.getElementById('preview-container');
        const error = document.getElementById('preview-error');

        this.showElement(loading);
        this.hideElement(container);
        this.hideElement(error);

        try {
            // Get first selected channel for preview
            const channelId = this.selectedChannels[0];
            const productId = this.selectedProducts[0];

            const templateType = document.querySelector('input[name="template-type"]:checked')?.value;
            let requestData = {
                product_id: productId,
                channel_id: channelId
            };

            // Add template information based on selection
            if (templateType === 'template-select') {
                const selectedTemplateId = document.getElementById('template-select')?.value;
                if (selectedTemplateId) {
                    requestData.template_id = parseInt(selectedTemplateId);
                }
            } else if (templateType === 'custom') {
                const customContent = document.getElementById('custom-template')?.value;
                if (customContent) {
                    requestData.template_content = customContent;
                }
            }

            const response = await fetch('/api/v1/telegram/posts/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();

            if (response.ok) {
                this.renderPreview(data);
                this.showElement(container);
            } else {
                this.showPreviewError(data.detail || 'Failed to generate preview');
            }
        } catch (error) {
            console.error('Preview error:', error);
            this.showPreviewError('Network error while generating preview');
        } finally {
            this.hideElement(loading);
        }
    }

    renderPreview(previewData) {
        const channelName = document.querySelector('.preview-channel');
        const photosInfo = document.querySelector('.preview-photos');
        const messageContainer = document.getElementById('preview-message');

        if (channelName) {
            channelName.textContent = `📢 ${previewData.channel_name || 'Channel'}`;
        }

        if (photosInfo) {
            const photoText = previewData.will_send_photos && previewData.photo_count > 0
                ? `📷 ${previewData.photo_count} photo${previewData.photo_count !== 1 ? 's' : ''}`
                : '📝 Text only';
            photosInfo.textContent = photoText;
        }

        if (messageContainer) {
            messageContainer.textContent = previewData.rendered_content || 'No content';
        }

        // Update tabs if multiple products
        this.updatePreviewTabs();
    }

    updatePreviewTabs() {
        const tabs = document.querySelector('.preview-tabs');
        if (!tabs || this.selectedProducts.length <= 1) return;

        tabs.innerHTML = this.selectedProducts.map((productId, index) => `
            <button class="preview-tab ${index === 0 ? 'active' : ''}" data-product="${productId}">
                Product ${index + 1}
            </button>
        `).join('');
    }

    showPreviewError(message) {
        const error = document.getElementById('preview-error');
        const errorMessage = document.getElementById('preview-error-message');

        if (errorMessage) {
            errorMessage.textContent = message;
        }
        this.showElement(error);
    }

    showDefaultPreview() {
        const container = document.getElementById('preview-container');
        const error = document.getElementById('preview-error');
        const loading = document.getElementById('preview-loading');
        
        this.showElement(container);
        this.hideElement(error);
        this.hideElement(loading);
        
        // Set default preview content
        const channelName = document.querySelector('.preview-channel');
        const photosInfo = document.querySelector('.preview-photos');
        const messageContainer = document.getElementById('preview-message');
        
        if (channelName) {
            if (!this.selectedChannels.length) {
                channelName.textContent = '📢 Select a channel';
            } else if (!this.selectedProducts.length) {
                channelName.textContent = '📢 Select a product';
            }
        }
        
        if (photosInfo) {
            photosInfo.textContent = '📝 Preview will appear here';
        }
        
        if (messageContainer) {
            if (!this.selectedChannels.length && !this.selectedProducts.length) {
                messageContainer.textContent = 'Select a channel and ensure you have a product selected to see the preview.';
            } else if (!this.selectedChannels.length) {
                messageContainer.textContent = 'Please select at least one channel from step 1.';
            } else if (!this.selectedProducts.length) {
                messageContainer.textContent = 'Please select a product from the main table before opening this modal.';
            }
        }
    }

    hidePreview() {
        const container = document.getElementById('preview-container');
        const error = document.getElementById('preview-error');
        this.hideElement(container);
        this.hideElement(error);
    }

    async sendPosts() {
        if (!this.selectedProducts.length || !this.selectedChannels.length) {
            this.showNotification('Please select products and channels', 'warning');
            return;
        }

        const sendBtn = document.getElementById('telegram-send');
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.textContent = '📤 Sending...';
        }

        try {
            // Prepare request data
            const templateType = document.querySelector('input[name="template-type"]:checked')?.value;
            let requestData = {
                product_id: this.selectedProducts[0], // For now, send first selected product
                channel_ids: this.selectedChannels,
                send_photos: document.getElementById('send-photos')?.checked,
                disable_notification: document.getElementById('disable-notification')?.checked
            };

            // Add template information
            if (templateType === 'template-select') {
                const selectedTemplateId = document.getElementById('template-select')?.value;
                if (selectedTemplateId) {
                    requestData.template_id = parseInt(selectedTemplateId);
                }
            } else if (templateType === 'custom') {
                const customContent = document.getElementById('custom-template')?.value;
                if (customContent) {
                    requestData.template_content = customContent;
                }
            }

            const response = await fetch('/api/v1/telegram/posts/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();

            if (response.ok) {
                const successMsg = `Successfully sent to ${data.success_count} channel${data.success_count !== 1 ? 's' : ''}`;
                this.showNotification(successMsg, 'success');
                
                if (data.failed_count > 0) {
                    console.warn('Some posts failed:', data.errors);
                    this.showNotification(`${data.failed_count} posts failed`, 'warning');
                }

                this.closeModal();
            } else {
                throw new Error(data.detail || 'Failed to send posts');
            }
        } catch (error) {
            console.error('Send error:', error);
            this.showNotification(error.message || 'Failed to send posts', 'error');
        } finally {
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.textContent = '📤 Send Posts';
            }
        }
    }

    openModal() {
        // Get selected products from the main table
        this.selectedProducts = this.getSelectedProductIds();
        
        if (!this.selectedProducts.length) {
            this.showNotification('Please select products to post', 'warning');
            return;
        }

        this.showElement(this.modal);
        this.updateFooterInfo();
        this.updateSendButtonState();
        
        // Always show the preview container and update it
        this.showElement(document.getElementById('preview-container'));
        this.updatePreview();

        // Reset form state
        this.resetForm();
    }

    closeModal() {
        this.hideElement(this.modal);
        this.selectedChannels = [];
        this.resetForm();
    }

    resetForm() {
        // Reset template type to default
        const defaultRadio = document.querySelector('input[name="template-type"][value="channel-default"]');
        if (defaultRadio) {
            defaultRadio.checked = true;
        }

        // Reset template select
        const templateSelect = document.getElementById('template-select');
        if (templateSelect) {
            templateSelect.value = '';
            templateSelect.disabled = true;
        }

        // Hide custom template section
        const customSection = document.getElementById('custom-template-section');
        if (customSection) {
            this.hideElement(customSection);
        }

        // Clear custom template
        const customTemplate = document.getElementById('custom-template');
        if (customTemplate) {
            customTemplate.value = '';
        }

        // Reset post options
        const sendPhotos = document.getElementById('send-photos');
        const disableNotification = document.getElementById('disable-notification');
        
        if (sendPhotos) sendPhotos.checked = true;
        if (disableNotification) disableNotification.checked = false;

        // Clear channel selections
        document.querySelectorAll('#channels-list input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        this.updateChannelVisualState();

        // Hide placeholders help
        const placeholdersHelp = document.getElementById('placeholders-help');
        if (placeholdersHelp) {
            this.hideElement(placeholdersHelp);
        }

        this.hidePreview();
    }

    getSelectedProductIds() {
        // Get selected products from the global row selection system
        if (window.app && window.app.table && window.app.table.rowSelection) {
            return window.app.table.rowSelection.getSelectedIds();
        }
        
        // Fallback: try to find selected rows by CSS class
        const selectedRows = document.querySelectorAll('#products-tbody tr.selected');
        return Array.from(selectedRows).map(row => {
            const productId = parseInt(row.dataset.productId);
            return productId || null;
        }).filter(id => id !== null);
    }

    updateFooterInfo() {
        const productCount = document.getElementById('selected-products-count');
        const channelCount = document.getElementById('selected-channels-count');

        if (productCount) {
            const count = this.selectedProducts.length;
            productCount.textContent = `${count} product${count !== 1 ? 's' : ''} selected`;
        }

        if (channelCount) {
            const count = this.selectedChannels.length;
            channelCount.textContent = `${count} channel${count !== 1 ? 's' : ''} selected`;
        }
    }

    updateSendButtonState() {
        const sendBtn = document.getElementById('telegram-send');
        if (!sendBtn) return;

        const canSend = this.selectedProducts.length > 0 && this.selectedChannels.length > 0;
        sendBtn.disabled = !canSend;
    }

    // Channel Management Methods
    openChannelModal(channelData = null) {
        const modal = document.getElementById('channel-modal');
        const title = document.getElementById('channel-modal-title');
        const saveBtn = document.getElementById('channel-save');
        
        if (channelData) {
            title.textContent = '✏️ Edit Channel';
            saveBtn.textContent = '💾 Update Channel';
            this.populateChannelForm(channelData);
        } else {
            title.textContent = '➕ Add Channel';
            saveBtn.textContent = '➕ Create Channel';
            this.resetChannelForm();
        }
        
        this.currentEditingChannel = channelData;
        this.showElement(modal);
        this.loadTemplatesForChannel();
        this.initChannelFormEvents();
    }

    closeChannelModal() {
        const modal = document.getElementById('channel-modal');
        this.hideElement(modal);
        this.resetChannelForm();
        this.currentEditingChannel = null;
    }

    initChannelFormEvents() {
        if (this.channelFormBound) return;
        this.channelFormBound = true;

        const modal = document.getElementById('channel-modal');
        const closeBtn = document.getElementById('channel-modal-close');
        const cancelBtn = document.getElementById('channel-cancel');
        const saveBtn = document.getElementById('channel-save');
        const testBtn = document.getElementById('test-channel');
        const form = document.getElementById('channel-form');

        [closeBtn, cancelBtn].forEach(btn => {
            if (btn) btn.addEventListener('click', () => this.closeChannelModal());
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal || e.target.classList.contains('modal-backdrop')) {
                this.closeChannelModal();
            }
        });

        form.addEventListener('input', () => this.validateChannelForm());
        
        if (testBtn) testBtn.addEventListener('click', () => this.testChannelConnection());
        if (saveBtn) saveBtn.addEventListener('click', () => this.saveChannel());
    }

    resetChannelForm() {
        const form = document.getElementById('channel-form');
        if (form) {
            form.reset();
            document.getElementById('channel-active').checked = true;
            document.getElementById('channel-send-photos').checked = true;
            document.getElementById('channel-disable-preview').checked = true;
        }
        this.clearChannelFormValidation();
        this.updateChannelSaveButton();
        this.hideElement(document.getElementById('test-result'));
    }

    populateChannelForm(channel) {
        document.getElementById('channel-name').value = channel.name || '';
        document.getElementById('channel-chat-id').value = channel.chat_id || '';
        document.getElementById('channel-description').value = channel.description || '';
        document.getElementById('channel-template').value = channel.template_id || '';
        
        document.getElementById('channel-active').checked = channel.is_active !== false;
        document.getElementById('channel-auto-post').checked = channel.auto_post === true;
        document.getElementById('channel-send-photos').checked = channel.send_photos !== false;
        document.getElementById('channel-disable-notification').checked = channel.disable_notification === true;
        document.getElementById('channel-disable-preview').checked = channel.disable_web_page_preview !== false;
        
        this.validateChannelForm();
    }

    async loadTemplatesForChannel() {
        const select = document.getElementById('channel-template');
        if (!select) return;

        try {
            const response = await fetch('/api/v1/templates?active_only=true');
            const data = await response.json();

            if (data.success) {
                select.innerHTML = `
                    <option value="">No default template</option>
                    ${data.data.map(template => 
                        `<option value="${template.id}">${this.escapeHtml(template.name)}</option>`
                    ).join('')}
                `;
            }
        } catch (error) {
            console.error('Failed to load templates for channel:', error);
        }
    }

    validateChannelForm() {
        const name = document.getElementById('channel-name').value.trim();
        const chatId = document.getElementById('channel-chat-id').value.trim();
        
        let isValid = true;
        let errors = [];

        if (!name) {
            errors.push('Channel name is required');
            isValid = false;
        }

        if (!chatId) {
            errors.push('Chat ID is required');
            isValid = false;
        } else if (!this.isValidChatId(chatId)) {
            errors.push('Chat ID must be numeric or start with @');
            isValid = false;
        }

        this.updateChannelStatus(isValid, errors);
        this.updateChannelSaveButton(isValid);
        
        return isValid;
    }

    isValidChatId(chatId) {
        if (chatId.startsWith('@')) {
            return chatId.length > 1;
        } else {
            return !isNaN(parseInt(chatId));
        }
    }

    updateChannelStatus(isValid, errors = []) {
        const status = document.getElementById('channel-status');
        if (!status) return;

        if (isValid) {
            status.textContent = 'Ready to save';
            status.style.color = '#166534';
        } else {
            status.textContent = errors[0] || 'Please fix the errors';
            status.style.color = '#991b1b';
        }
    }

    updateChannelSaveButton(isValid = null) {
        const saveBtn = document.getElementById('channel-save');
        if (!saveBtn) return;

        if (isValid === null) {
            isValid = this.validateChannelForm();
        }
        
        saveBtn.disabled = !isValid;
    }

    clearChannelFormValidation() {
        const inputs = document.querySelectorAll('#channel-form .form-input, #channel-form .form-textarea');
        inputs.forEach(input => {
            input.classList.remove('invalid');
        });
        
        const errors = document.querySelectorAll('#channel-form .form-error');
        errors.forEach(error => error.remove());
    }

    async testChannelConnection() {
        const chatId = document.getElementById('channel-chat-id').value.trim();
        const testBtn = document.getElementById('test-channel');
        
        if (!chatId) {
            this.showTestResult('Please enter a chat ID first', 'error');
            return;
        }

        testBtn.disabled = true;
        testBtn.textContent = '🔄 Testing...';
        this.showTestResult('Testing connection...', 'testing');

        try {
            const response = await fetch('/api/v1/telegram/channels/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: chatId })
            });

            const data = await response.json();

            if (data.success) {
                const chatInfo = data.chat_info;
                this.showTestResult(
                    `✅ Connection successful!\nChat: ${chatInfo.title || chatInfo.username || 'Unknown'}\nType: ${chatInfo.type || 'Unknown'}`,
                    'success'
                );
            } else {
                this.showTestResult(`❌ Connection failed: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Test connection error:', error);
            this.showTestResult(`❌ Network error: ${error.message}`, 'error');
        } finally {
            testBtn.disabled = false;
            testBtn.textContent = '🔧 Test Connection';
        }
    }

    showTestResult(message, type) {
        const testResult = document.getElementById('test-result');
        if (!testResult) return;

        testResult.textContent = message;
        testResult.className = `test-result ${type}`;
        this.showElement(testResult);
    }

    async saveChannel() {
        if (!this.validateChannelForm()) return;

        const form = document.getElementById('channel-form');
        const formData = new FormData(form);
        const saveBtn = document.getElementById('channel-save');
        
        const channelData = {
            name: formData.get('name'),
            chat_id: formData.get('chat_id'),
            description: formData.get('description') || null,
            template_id: formData.get('template_id') ? parseInt(formData.get('template_id')) : null,
            is_active: formData.has('is_active'),
            auto_post: formData.has('auto_post'),
            send_photos: formData.has('send_photos'),
            disable_notification: formData.has('disable_notification'),
            disable_web_page_preview: formData.has('disable_web_page_preview')
        };

        const isEdit = this.currentEditingChannel !== null;
        const url = isEdit 
            ? `/api/v1/telegram/channels/${this.currentEditingChannel.id}`
            : '/api/v1/telegram/channels';
        const method = isEdit ? 'PUT' : 'POST';

        saveBtn.disabled = true;
        saveBtn.textContent = isEdit ? '💾 Updating...' : '➕ Creating...';

        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(channelData)
            });

            const data = await response.json();

            if (response.ok && data.success) {
                this.showNotification(
                    `Channel ${isEdit ? 'updated' : 'created'} successfully`, 
                    'success'
                );
                this.closeChannelModal();
                this.loadChannels();
            } else {
                throw new Error(data.detail || `Failed to ${isEdit ? 'update' : 'create'} channel`);
            }
        } catch (error) {
            console.error('Save channel error:', error);
            this.showNotification(error.message, 'error');
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = isEdit ? '💾 Update Channel' : '➕ Create Channel';
        }
    }

    editChannel(channelId) {
        const channel = this.channels.find(c => c.id === channelId);
        if (channel) {
            this.openChannelModal(channel);
        }
    }

    async deleteChannel(channelId) {
        const channel = this.channels.find(c => c.id === channelId);
        if (!channel) return;

        const confirmed = confirm(`Are you sure you want to delete the channel "${channel.name}"?\n\nThis action cannot be undone.`);
        if (!confirmed) return;

        try {
            const response = await fetch(`/api/v1/telegram/channels/${channelId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (response.ok && data.success) {
                this.showNotification('Channel deleted successfully', 'success');
                this.loadChannels();
            } else {
                throw new Error(data.detail || 'Failed to delete channel');
            }
        } catch (error) {
            console.error('Delete channel error:', error);
            this.showNotification(error.message, 'error');
        }
    }

    // Utility methods
    showElement(element) {
        if (element) element.classList.remove('hidden');
    }

    hideElement(element) {
        if (element) element.classList.add('hidden');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showNotification(message, type = 'info') {
        // Integrate with existing notification system
        if (window.NotificationService) {
            window.NotificationService.show(message, type);
        } else {
            // Fallback
            console.log(`${type.toUpperCase()}: ${message}`);
            alert(message);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.telegramModal = new TelegramModal();
});