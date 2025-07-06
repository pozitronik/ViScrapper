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
        this.quickPostConfig = {
            channels: [],
            template_id: null,
            send_photos: true,
            disable_notification: false
        };
        
        this.init();
    }

    init() {
        this.modal = document.getElementById('telegram-modal');
        if (!this.modal) return;

        this.bindEvents();
        this.loadInitialData();
    }

    bindEvents() {
        // Channel management button
        const channelsBtn = document.getElementById('manage-channels');
        if (channelsBtn) {
            channelsBtn.addEventListener('click', () => this.openChannelManagement());
        }

        // Quick post button in selection bar
        const quickPostBtn = document.getElementById('telegram-quick-post');
        
        if (quickPostBtn) {
            quickPostBtn.addEventListener('click', () => this.quickPost());
        }

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

        // Channel management modal
        const channelManagementModal = document.getElementById('channel-management-modal');
        if (channelManagementModal) {
            const closeBtn = channelManagementModal.querySelector('#channel-management-close');
            const cancelBtn = channelManagementModal.querySelector('#channel-management-cancel');
            const addNewChannelBtn = channelManagementModal.querySelector('#add-new-channel');
            const refreshChannelListBtn = channelManagementModal.querySelector('#refresh-channel-list');
            const createFirstChannelBtn = channelManagementModal.querySelector('#create-first-channel');

            [closeBtn, cancelBtn].forEach(btn => {
                if (btn) btn.addEventListener('click', () => this.closeChannelManagement());
            });

            if (addNewChannelBtn) {
                addNewChannelBtn.addEventListener('click', () => this.openChannelModal());
            }

            if (createFirstChannelBtn) {
                createFirstChannelBtn.addEventListener('click', () => this.openChannelModal());
            }

            if (refreshChannelListBtn) {
                refreshChannelListBtn.addEventListener('click', () => this.loadChannelsForManagement());
            }

            // Quick post configuration
            const configureQuickPostBtn = channelManagementModal.querySelector('#configure-quick-post');
            const saveQuickPostConfigBtn = channelManagementModal.querySelector('#save-quick-post-config');
            const cancelQuickPostConfigBtn = channelManagementModal.querySelector('#cancel-quick-post-config');

            if (configureQuickPostBtn) {
                configureQuickPostBtn.addEventListener('click', () => this.openQuickPostConfig());
            }

            if (saveQuickPostConfigBtn) {
                saveQuickPostConfigBtn.addEventListener('click', () => this.saveQuickPostConfig());
            }

            if (cancelQuickPostConfigBtn) {
                cancelQuickPostConfigBtn.addEventListener('click', () => this.closeQuickPostConfig());
            }

            // Click outside to close
            channelManagementModal.addEventListener('click', (e) => {
                if (e.target === channelManagementModal || e.target.classList.contains('modal-backdrop')) {
                    this.closeChannelManagement();
                }
            });
        }

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
            this.loadPlaceholders(),
            this.loadQuickPostConfig()
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
            if (window.app && window.app.showNotification) {
                window.app.showNotification('Please select products and channels', 'warning');
            }
            return;
        }

        const sendBtn = document.getElementById('telegram-send');
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.textContent = '📤 Sending...';
        }

        try {
            // Get template configuration
            const templateType = document.querySelector('input[name="template-type"]:checked')?.value;
            const sendPhotos = document.getElementById('send-photos')?.checked;
            const disableNotification = document.getElementById('disable-notification')?.checked;
            
            let templateId = null;
            let templateContent = null;
            
            // Add template information
            if (templateType === 'template-select') {
                const selectedTemplateId = document.getElementById('template-select')?.value;
                if (selectedTemplateId) {
                    templateId = parseInt(selectedTemplateId);
                }
            } else if (templateType === 'custom') {
                const customContent = document.getElementById('custom-template')?.value;
                if (customContent) {
                    templateContent = customContent;
                }
            }

            let totalSuccess = 0;
            let totalFailed = 0;
            const failedProducts = [];

            // Process each selected product
            for (const productId of this.selectedProducts) {
                try {
                    let requestData = {
                        product_id: productId,
                        channel_ids: this.selectedChannels,
                        send_photos: sendPhotos,
                        disable_notification: disableNotification
                    };

                    if (templateId) {
                        requestData.template_id = templateId;
                    }
                    if (templateContent) {
                        requestData.template_content = templateContent;
                    }

                    const response = await fetch('/api/v1/telegram/posts/send', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(requestData)
                    });

                    const data = await response.json();

                    if (response.ok) {
                        totalSuccess += data.success_count || 0;
                        totalFailed += data.failed_count || 0;
                        
                        // Update button appearance for successful posts
                        if (data.success_count > 0) {
                            this.updateQuickPostButtonAppearance(productId);
                        }
                        
                        if (data.failed_count > 0) {
                            failedProducts.push(productId);
                        }
                    } else {
                        failedProducts.push(productId);
                        totalFailed += this.selectedChannels.length;
                        console.warn(`Failed to post product ${productId}:`, data);
                    }
                } catch (productError) {
                    console.error(`Error posting product ${productId}:`, productError);
                    failedProducts.push(productId);
                    totalFailed += this.selectedChannels.length;
                }
            }

            // Show summary notification as toast
            if (totalFailed > 0) {
                if (totalSuccess > 0) {
                    if (window.app && window.app.showNotification) {
                        window.app.showNotification(`${totalFailed} of ${totalSuccess + totalFailed} posts failed`, 'warning');
                    }
                } else {
                    if (window.app && window.app.showNotification) {
                        window.app.showNotification(`All posts failed`, 'error');
                    }
                }
            } else {
                // Show success message for multiple products as toast
                if (window.app && window.app.showNotification) {
                    window.app.showNotification(`Successfully posted ${this.selectedProducts.length} products to ${this.selectedChannels.length} channels`, 'success');
                }
            }
            
            // Refresh the table if available
            if (totalSuccess > 0 && window.app && window.app.refreshProducts) {
                window.app.refreshProducts();
            }
            
            // Always close modal after sending (whether successful or not)
            this.closeModal();
        } catch (error) {
            console.error('Send error:', error);
            if (window.app && window.app.showNotification) {
                window.app.showNotification(error.message || 'Failed to send posts', 'error');
            }
        } finally {
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.textContent = '📤 Send Posts';
            }
        }
    }

    openChannelManagement() {
        // Open the channel management interface
        const modal = document.getElementById('channel-management-modal');
        if (modal) {
            this.showElement(modal);
            this.loadChannelsForManagement();
        }
    }

    closeChannelManagement() {
        const modal = document.getElementById('channel-management-modal');
        if (modal) {
            this.hideElement(modal);
        }
    }

    async loadChannelsForManagement() {
        const loading = document.getElementById('channel-management-loading');
        const container = document.getElementById('channel-management-list');
        const noChannels = document.getElementById('no-channels-management');
        const countDisplay = document.getElementById('channel-management-count');

        this.showElement(loading);
        this.hideElement(container);
        this.hideElement(noChannels);

        try {
            const response = await fetch('/api/v1/telegram/channels?include_deleted=false');
            const data = await response.json();

            if (data.success && data.data.length > 0) {
                this.renderChannelsForManagement(data.data);
                this.showElement(container);
                if (countDisplay) {
                    countDisplay.textContent = `${data.data.length} channel${data.data.length !== 1 ? 's' : ''}`;
                }
            } else {
                this.showElement(noChannels);
                if (countDisplay) {
                    countDisplay.textContent = '0 channels';
                }
            }
            
            // Update quick post summary
            this.updateQuickPostSummary();
        } catch (error) {
            console.error('Failed to load channels for management:', error);
            this.showElement(noChannels);
            this.showNotification('Failed to load Telegram channels', 'error');
            if (countDisplay) {
                countDisplay.textContent = '0 channels';
            }
        } finally {
            this.hideElement(loading);
        }
    }

    renderChannelsForManagement(channels) {
        const container = document.getElementById('channel-management-list');
        if (!container) return;

        container.innerHTML = channels.map(channel => `
            <div class="channel-item" data-channel-id="${channel.id}">
                <div class="channel-content">
                    <div class="channel-name">${this.escapeHtml(channel.name)}</div>
                    <div class="channel-info">
                        <span class="channel-chat-id">${this.escapeHtml(channel.chat_id)}</span>
                        <div class="channel-badges">
                            <span class="channel-badge ${channel.is_active ? 'active' : 'inactive'}">
                                ${channel.is_active ? 'Active' : 'Inactive'}
                            </span>
                            <span class="channel-badge ${channel.auto_post ? 'auto-post' : 'manual'}">
                                ${channel.auto_post ? '🤖 Auto' : '👤 Manual'}
                            </span>
                        </div>
                    </div>
                    ${channel.description ? `<div class="channel-description">${this.escapeHtml(channel.description)}</div>` : ''}
                    <div class="channel-settings">
                        ${channel.send_photos ? '📷 Photos' : '📝 Text only'} • 
                        ${channel.disable_notification ? '🔕 Silent' : '🔔 With notifications'} • 
                        ${channel.disable_web_page_preview ? '🔗 No previews' : '🔗 With previews'}
                    </div>
                </div>
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

        // Bind action button events
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
                // Also refresh management list if it's open
                const managementModal = document.getElementById('channel-management-modal');
                if (managementModal && !managementModal.classList.contains('hidden')) {
                    this.loadChannelsForManagement();
                }
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
                // Also refresh management list if it's open
                const managementModal = document.getElementById('channel-management-modal');
                if (managementModal && !managementModal.classList.contains('hidden')) {
                    this.loadChannelsForManagement();
                }
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

    // Quick Post Methods
    async quickPost(productId = null) {
        // Get products to post - either specific product or selected products
        let productsToPost = [];
        if (productId) {
            productsToPost = [productId];
        } else {
            productsToPost = this.getSelectedProductIds();
        }
        
        if (!productsToPost.length) {
            if (window.app && window.app.showNotification) {
                window.app.showNotification('Please select products to post', 'warning');
            }
            return;
        }

        // Check if quick post is configured
        if (!this.quickPostConfig.channels.length) {
            if (window.app && window.app.showNotification) {
                window.app.showNotification('Quick post not configured. Use "📢 Channels" to set it up.', 'warning');
            }
            return;
        }

        // Send all selected products
        try {
            let totalSuccess = 0;
            let totalFailed = 0;
            const failedProducts = [];

            // Process each product individually
            for (const productId of productsToPost) {
                try {
                    const requestData = {
                        product_id: productId,
                        channel_ids: this.quickPostConfig.channels,
                        template_id: this.quickPostConfig.template_id,
                        send_photos: this.quickPostConfig.send_photos,
                        disable_notification: this.quickPostConfig.disable_notification
                    };

                    const response = await fetch('/api/v1/telegram/posts/send', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(requestData)
                    });

                    const data = await response.json();

                    if (response.ok) {
                        totalSuccess += data.success_count || 0;
                        totalFailed += data.failed_count || 0;
                        
                        // Update button appearance for successful posts
                        if (data.success_count > 0) {
                            this.updateQuickPostButtonAppearance(productId);
                        }
                        
                        if (data.failed_count > 0) {
                            failedProducts.push(productId);
                        }
                    } else {
                        failedProducts.push(productId);
                        totalFailed += this.quickPostConfig.channels.length;
                    }
                } catch (productError) {
                    console.error(`Error posting product ${productId}:`, productError);
                    failedProducts.push(productId);
                    totalFailed += this.quickPostConfig.channels.length;
                }
            }

            // Show summary notification as toast
            if (totalFailed > 0) {
                if (totalSuccess > 0) {
                    if (window.app && window.app.showNotification) {
                        window.app.showNotification(`${totalFailed} of ${totalSuccess + totalFailed} posts failed`, 'warning');
                    }
                } else {
                    if (window.app && window.app.showNotification) {
                        window.app.showNotification(`All posts failed`, 'error');
                    }
                }
            } else if (productsToPost.length > 1) {
                // Only show success message for multiple products as toast
                if (window.app && window.app.showNotification) {
                    window.app.showNotification(`Successfully posted ${productsToPost.length} products`, 'success');
                }
            }
            
            // Refresh the table if available
            if (totalSuccess > 0 && window.app && window.app.refreshProducts) {
                window.app.refreshProducts();
            }
        } catch (error) {
            console.error('Quick post error:', error);
            if (window.app && window.app.showNotification) {
                window.app.showNotification(error.message || 'Failed to send quick post', 'error');
            }
        }
    }

    updateQuickPostButtonAppearance(productId) {
        // Find the Quick post button for the specific product
        const quickPostBtn = document.querySelector(`[data-product-id="${productId}"][data-action="quick-post"]`);
        if (!quickPostBtn) return;

        // Update button appearance to "posted" state
        quickPostBtn.className = 'btn btn-sm btn-outline-success posted';
        quickPostBtn.innerHTML = '✅';
        
        // Update tooltip with current timestamp
        const now = new Date();
        quickPostBtn.title = `Posted to Telegram on ${now.toLocaleString()}. Click to post again.`;
    }

    async openQuickPostConfig() {
        const configSection = document.getElementById('quick-post-config');
        this.showElement(configSection);
        
        // Load data for configuration
        await this.loadQuickPostChannels();
        await this.loadQuickPostTemplates();
        this.populateQuickPostForm();
    }

    closeQuickPostConfig() {
        const configSection = document.getElementById('quick-post-config');
        this.hideElement(configSection);
        this.updateQuickPostSummary();
    }

    async loadQuickPostChannels() {
        const container = document.getElementById('quick-post-channels');
        if (!container) return;

        const channels = this.channels.filter(channel => channel.is_active);
        
        container.innerHTML = channels.map(channel => `
            <label class="checkbox-option">
                <input type="checkbox" value="${channel.id}" data-channel-id="${channel.id}">
                <span class="checkbox-label">${this.escapeHtml(channel.name)}</span>
            </label>
        `).join('');
    }

    async loadQuickPostTemplates() {
        const select = document.getElementById('quick-post-template');
        if (!select) return;

        select.innerHTML = `
            <option value="">Use channel's default template</option>
            ${this.templates.map(template => 
                `<option value="${template.id}">${this.escapeHtml(template.name)}</option>`
            ).join('')}
        `;
    }

    populateQuickPostForm() {
        // Set selected channels
        const channelCheckboxes = document.querySelectorAll('#quick-post-channels input[type="checkbox"]');
        channelCheckboxes.forEach(checkbox => {
            checkbox.checked = this.quickPostConfig.channels.includes(parseInt(checkbox.value));
        });

        // Set selected template
        const templateSelect = document.getElementById('quick-post-template');
        if (templateSelect) {
            templateSelect.value = this.quickPostConfig.template_id || '';
        }

        // Set options
        const photosCheckbox = document.getElementById('quick-post-photos');
        const silentCheckbox = document.getElementById('quick-post-silent');
        
        if (photosCheckbox) {
            photosCheckbox.checked = this.quickPostConfig.send_photos;
        }
        
        if (silentCheckbox) {
            silentCheckbox.checked = this.quickPostConfig.disable_notification;
        }
    }

    async saveQuickPostConfig() {
        // Get selected channels
        const selectedChannels = [];
        const channelCheckboxes = document.querySelectorAll('#quick-post-channels input[type="checkbox"]:checked');
        channelCheckboxes.forEach(checkbox => {
            selectedChannels.push(parseInt(checkbox.value));
        });

        if (!selectedChannels.length) {
            this.showNotification('Please select at least one channel', 'warning');
            return;
        }

        // Get other settings
        const templateSelect = document.getElementById('quick-post-template');
        const photosCheckbox = document.getElementById('quick-post-photos');
        const silentCheckbox = document.getElementById('quick-post-silent');

        this.quickPostConfig = {
            channels: selectedChannels,
            template_id: templateSelect?.value ? parseInt(templateSelect.value) : null,
            send_photos: photosCheckbox?.checked || true,
            disable_notification: silentCheckbox?.checked || false
        };

        // Save to localStorage
        localStorage.setItem('telegram_quick_post_config', JSON.stringify(this.quickPostConfig));
        
        this.showNotification('Quick post configuration saved', 'success');
        this.closeQuickPostConfig();
    }

    async loadQuickPostConfig() {
        try {
            const savedConfig = localStorage.getItem('telegram_quick_post_config');
            if (savedConfig) {
                this.quickPostConfig = { ...this.quickPostConfig, ...JSON.parse(savedConfig) };
            }
        } catch (error) {
            console.error('Error loading quick post config:', error);
        }
    }

    updateQuickPostSummary() {
        const summaryElement = document.getElementById('quick-post-summary');
        if (!summaryElement) return;

        if (this.quickPostConfig.channels.length > 0) {
            const channelNames = this.quickPostConfig.channels
                .map(id => {
                    const channel = this.channels.find(c => c.id === id);
                    return channel ? channel.name : `Channel ${id}`;
                })
                .join(', ');

            summaryElement.innerHTML = `
                <div class="quick-post-status configured">
                    <div class="status-header">
                        <span class="status-indicator">✅</span>
                        <strong>Quick Post Configured</strong>
                    </div>
                    <div class="status-details">
                        <div><strong>Channels:</strong> ${channelNames}</div>
                        <div><strong>Photos:</strong> ${this.quickPostConfig.send_photos ? 'Enabled' : 'Disabled'}</div>
                        <div><strong>Notifications:</strong> ${this.quickPostConfig.disable_notification ? 'Silent' : 'Enabled'}</div>
                    </div>
                </div>
            `;
        } else {
            summaryElement.innerHTML = `
                <div class="quick-post-status not-configured">
                    <div class="status-header">
                        <span class="status-indicator">⚠️</span>
                        <strong>Quick Post Not Configured</strong>
                    </div>
                    <p class="text-muted">Configure default settings for one-click posting with the ⚡ Quick Post button.</p>
                </div>
            `;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.telegramModal = new TelegramModal();
});