// Keyboard shortcuts for VIParser frontend

class KeyboardShortcuts {
    constructor(app) {
        this.app = app;
        this.isEnabled = true;
        this.shortcuts = new Map();
        this.helpVisible = false;
        
        this.setupShortcuts();
        this.setupEventListeners();
        this.createHelpModal();
    }

    /**
     * Define all keyboard shortcuts
     */
    setupShortcuts() {
        // Navigation shortcuts
        this.addShortcut('ArrowLeft', { ctrl: true }, 'Previous page', () => {
            if (this.app.pagination) {
                this.app.pagination.prevPage();
            }
        });

        this.addShortcut('ArrowRight', { ctrl: true }, 'Next page', () => {
            if (this.app.pagination) {
                this.app.pagination.nextPage();
            }
        });

        this.addShortcut('Home', { ctrl: true }, 'First page', () => {
            if (this.app.pagination) {
                this.app.pagination.firstPage();
            }
        });

        this.addShortcut('End', { ctrl: true }, 'Last page', () => {
            if (this.app.pagination) {
                this.app.pagination.lastPage();
            }
        });

        // Data shortcuts
        this.addShortcut('F5', {}, 'Refresh data', (e) => {
            e.preventDefault();
            this.app.refresh();
        });

        this.addShortcut('r', { ctrl: true }, 'Refresh data', (e) => {
            e.preventDefault();
            this.app.refresh();
        });

        // Search shortcuts
        this.addShortcut('f', { ctrl: true }, 'Focus search', (e) => {
            e.preventDefault();
            this.focusSearch();
        });

        this.addShortcut('/', {}, 'Focus search', (e) => {
            e.preventDefault();
            this.focusSearch();
        });

        this.addShortcut('Escape', {}, 'Clear search', () => {
            this.clearSearch();
        });

        // Filter shortcuts
        this.addShortcut('f', { ctrl: true, shift: true }, 'Toggle filters', (e) => {
            e.preventDefault();
            this.toggleFilters();
        });

        this.addShortcut('c', { ctrl: true, shift: true }, 'Clear filters', (e) => {
            e.preventDefault();
            this.clearFilters();
        });

        // Selection shortcuts
        this.addShortcut('a', { ctrl: true }, 'Select all', (e) => {
            e.preventDefault();
            this.selectAll();
        });

        this.addShortcut('Delete', {}, 'Delete selected', (e) => {
            if (this.hasSelectedRows()) {
                e.preventDefault();
                this.deleteSelected();
            }
        });

        this.addShortcut('e', { ctrl: true }, 'Export selected', (e) => {
            if (this.hasSelectedRows()) {
                e.preventDefault();
                this.exportSelected();
            }
        });

        // Help shortcut
        this.addShortcut('?', {}, 'Show help', (e) => {
            if (!this.isInputFocused()) {
                e.preventDefault();
                this.toggleHelp();
            }
        });

        this.addShortcut('F1', {}, 'Show help', (e) => {
            e.preventDefault();
            this.toggleHelp();
        });

        // Quick actions
        this.addShortcut('n', { ctrl: true }, 'New product', (e) => {
            e.preventDefault();
            this.newProduct();
        });
    }

    /**
     * Add a keyboard shortcut
     */
    addShortcut(key, modifiers, description, handler) {
        const shortcut = {
            key: key.toLowerCase(),
            ctrl: modifiers.ctrl || false,
            alt: modifiers.alt || false,
            shift: modifiers.shift || false,
            meta: modifiers.meta || false,
            description,
            handler
        };

        const shortcutKey = this.getShortcutKey(key, modifiers);
        this.shortcuts.set(shortcutKey, shortcut);
    }

    /**
     * Generate unique key for shortcut
     */
    getShortcutKey(key, modifiers) {
        const parts = [];
        if (modifiers.ctrl) parts.push('ctrl');
        if (modifiers.alt) parts.push('alt');
        if (modifiers.shift) parts.push('shift');
        if (modifiers.meta) parts.push('meta');
        parts.push(key.toLowerCase());
        return parts.join('+');
    }

    /**
     * Set up event listeners
     */
    setupEventListeners() {
        document.addEventListener('keydown', (e) => {
            if (!this.isEnabled) return;

            const shortcutKey = this.getShortcutKey(e.key, {
                ctrl: e.ctrlKey,
                alt: e.altKey,
                shift: e.shiftKey,
                meta: e.metaKey
            });

            const shortcut = this.shortcuts.get(shortcutKey);
            if (shortcut) {
                // Check if we should ignore this shortcut based on focus
                if (this.shouldIgnoreShortcut(e, shortcut)) {
                    return;
                }

                shortcut.handler(e);
            }
        });
    }

    /**
     * Check if shortcut should be ignored
     */
    shouldIgnoreShortcut(e, shortcut) {
        // Always allow help shortcuts
        if (shortcut.key === '?' || shortcut.key === 'f1') {
            return false;
        }

        // Ignore most shortcuts when input is focused
        if (this.isInputFocused()) {
            // Allow escape to work in inputs
            return shortcut.key !== 'escape';
        }

        return false;
    }

    /**
     * Check if an input element is focused
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
     * Check if rows are selected
     */
    hasSelectedRows() {
        return this.app.table && 
               this.app.table.rowSelection && 
               this.app.table.rowSelection.getSelectedIds().length > 0;
    }

    // Shortcut action methods
    focusSearch() {
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }

    clearSearch() {
        if (this.app.clearSearch) {
            this.app.clearSearch();
        }
    }

    toggleFilters() {
        if (this.app.filters) {
            this.app.filters.toggleFilterPanel();
        }
    }

    clearFilters() {
        if (this.app.filters) {
            this.app.filters.clearAllFilters();
        }
    }

    selectAll() {
        if (this.app.table && this.app.table.rowSelection) {
            this.app.table.rowSelection.selectAll();
        }
    }

    deleteSelected() {
        if (this.app.table && this.app.table.rowSelection) {
            this.app.table.rowSelection.handleDeleteSelected();
        }
    }

    exportSelected() {
        if (this.app.table && this.app.table.rowSelection) {
            this.app.table.rowSelection.handleExportSelected();
        }
    }

    newProduct() {
        // Placeholder for new product functionality
        console.log('New product shortcut triggered');
        alert('New product functionality would be implemented here');
    }

    /**
     * Create help modal
     */
    createHelpModal() {
        const modal = createElement('div', {
            id: 'keyboard-help-modal',
            className: 'keyboard-help-modal hidden'
        });

        const backdrop = createElement('div', { className: 'modal-backdrop' });
        backdrop.addEventListener('click', () => this.hideHelp());

        const content = createElement('div', { className: 'keyboard-help-content' });
        
        const header = createElement('div', { className: 'keyboard-help-header' });
        header.innerHTML = `
            <h3>Keyboard Shortcuts</h3>
            <button class="modal-close-btn" title="Close (Esc)">×</button>
        `;

        const closeBtn = header.querySelector('.modal-close-btn');
        closeBtn.addEventListener('click', () => this.hideHelp());

        const body = createElement('div', { className: 'keyboard-help-body' });
        this.renderHelpContent(body);

        content.appendChild(header);
        content.appendChild(body);
        modal.appendChild(backdrop);
        modal.appendChild(content);

        document.body.appendChild(modal);
        this.helpModal = modal;
    }

    /**
     * Render help content
     */
    renderHelpContent(container) {
        const categories = {
            'Navigation': [
                { key: 'Ctrl + ←', desc: 'Previous page' },
                { key: 'Ctrl + →', desc: 'Next page' },
                { key: 'Ctrl + Home', desc: 'First page' },
                { key: 'Ctrl + End', desc: 'Last page' }
            ],
            'Data': [
                { key: 'F5 / Ctrl + R', desc: 'Refresh data' }
            ],
            'Search & Filter': [
                { key: 'Ctrl + F / /', desc: 'Focus search' },
                { key: 'Esc', desc: 'Clear search' },
                { key: 'Ctrl + Shift + F', desc: 'Toggle filters' },
                { key: 'Ctrl + Shift + C', desc: 'Clear all filters' }
            ],
            'Selection': [
                { key: 'Ctrl + A', desc: 'Select all' },
                { key: 'Delete', desc: 'Delete selected' },
                { key: 'Ctrl + E', desc: 'Export selected' }
            ],
            'General': [
                { key: '? / F1', desc: 'Show this help' },
                { key: 'Ctrl + N', desc: 'New product' }
            ]
        };

        Object.entries(categories).forEach(([category, shortcuts]) => {
            const section = createElement('div', { className: 'help-section' });
            
            const title = createElement('h4', { className: 'help-section-title' }, category);
            section.appendChild(title);

            const list = createElement('div', { className: 'help-shortcuts-list' });
            
            shortcuts.forEach(shortcut => {
                const item = createElement('div', { className: 'help-shortcut-item' });
                item.innerHTML = `
                    <span class="help-shortcut-key">${shortcut.key}</span>
                    <span class="help-shortcut-desc">${shortcut.desc}</span>
                `;
                list.appendChild(item);
            });

            section.appendChild(list);
            container.appendChild(section);
        });
    }

    /**
     * Toggle help modal
     */
    toggleHelp() {
        if (this.helpVisible) {
            this.hideHelp();
        } else {
            this.showHelp();
        }
    }

    /**
     * Show help modal
     */
    showHelp() {
        if (this.helpModal) {
            this.helpModal.classList.remove('hidden');
            this.helpVisible = true;
            document.body.style.overflow = 'hidden';
        }
    }

    /**
     * Hide help modal
     */
    hideHelp() {
        if (this.helpModal) {
            this.helpModal.classList.add('hidden');
            this.helpVisible = false;
            document.body.style.overflow = '';
        }
    }

    /**
     * Enable shortcuts
     */
    enable() {
        this.isEnabled = true;
    }

    /**
     * Disable shortcuts
     */
    disable() {
        this.isEnabled = false;
    }

    /**
     * Get all shortcuts for display
     */
    getAllShortcuts() {
        return Array.from(this.shortcuts.values());
    }
}

// Export for use in other modules
window.KeyboardShortcuts = KeyboardShortcuts;