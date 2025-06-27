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

        // Refresh buttons
        const refreshChannels = document.getElementById('refresh-channels');
        const refreshTemplates = document.getElementById('refresh-templates');
        const refreshPreview = document.getElementById('refresh-preview');

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
            </div>
        `).join('');

        // Bind channel selection events
        container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => this.onChannelSelectionChange());
        });

        container.querySelectorAll('.channel-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.type !== 'checkbox') {
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
            this.hidePreview();
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