// Table rendering and management for products

class ProductTable {
    constructor(tableId, onDataChange, onUpdateProduct, onDeleteProducts, onExportProducts) {
        this.table = document.getElementById(tableId);
        this.tbody = document.getElementById('products-tbody');
        this.totalCountElement = document.getElementById('total-count');
        this.onDataChange = onDataChange;
        this.onUpdateProduct = onUpdateProduct;
        this.products = [];
        this.imageBaseUrl = '/images/'; // Base URL for serving images
        
        // Initialize inline editor
        this.inlineEditor = new InlineEditor(this.handleProductUpdate.bind(this));
        this.inlineEditor.initializeTable(this.table);
        
        // Initialize row selection
        this.rowSelection = new RowSelection(
            this.handleSelectionChange.bind(this),
            onDeleteProducts,
            onExportProducts
        );
    }

    /**
     * Update table with new product data
     */
    updateData(products, totalCount = null) {
        this.products = products;
        this.renderRows();
        
        if (totalCount !== null) {
            this.updateTotalCount(totalCount);
        }
        
        // Initialize row selection for new data
        this.rowSelection.initializeTable(this.table, products);
        
        // Apply column configuration after rendering
        if (window.columnConfig) {
            setTimeout(() => {
                window.columnConfig.applyConfiguration();
            }, 0);
        }
        
        if (this.onDataChange) {
            this.onDataChange(products, totalCount);
        }
    }

    /**
     * Update a single product row with new data
     */
    updateProductRow(updatedProduct) {
        // Update the product in internal data
        const productIndex = this.products.findIndex(p => p.id === updatedProduct.id);
        if (productIndex !== -1) {
            this.products[productIndex] = updatedProduct;
            
            // Find and replace the row
            const row = document.querySelector(`tr[data-product-id="${updatedProduct.id}"]`);
            if (row) {
                const newRow = this.createProductRow(updatedProduct);
                row.parentNode.replaceChild(newRow, row);
                
                // Re-apply column configuration
                if (window.columnConfig) {
                    setTimeout(() => {
                        window.columnConfig.applyConfiguration();
                    }, 0);
                }
                
                // Re-initialize inline editor for the new row
                this.inlineEditor.initializeTable(this.table);
                
                // Re-initialize row selection for the new row
                this.rowSelection.initializeTable(this.table, this.products);
                
                return true;
            }
        }
        return false;
    }

    /**
     * Update total count display
     */
    updateTotalCount(count) {
        const plural = count === 1 ? 'product' : 'products';
        this.totalCountElement.textContent = `${count.toLocaleString()} ${plural}`;
    }

    /**
     * Render all product rows
     */
    renderRows() {
        this.tbody.innerHTML = '';
        
        this.products.forEach(product => {
            const row = this.createProductRow(product);
            this.tbody.appendChild(row);
        });
    }

    /**
     * Create a single product row
     */
    createProductRow(product) {
        const row = createElement('tr', {
            dataset: { productId: product.id }
        });

        // Add all table cells
        row.appendChild(this.createSelectCell(product));
        row.appendChild(this.createIdCell(product));
        row.appendChild(this.createImagesCell(product));
        row.appendChild(this.createNameCell(product));
        row.appendChild(this.createSkuCell(product));
        row.appendChild(this.createPriceCell(product));
        row.appendChild(this.createSellingPriceCell(product));
        row.appendChild(this.createAvailabilityCell(product));
        row.appendChild(this.createColorCell(product));
        row.appendChild(this.createCompositionCell(product));
        row.appendChild(this.createItemCell(product));
        row.appendChild(this.createStoreCell(product));
        row.appendChild(this.createSizesCell(product));
        row.appendChild(this.createCommentCell(product));
        row.appendChild(this.createCreatedAtCell(product));
        row.appendChild(this.createUrlCell(product));

        return row;
    }

    /**
     * Create select cell
     */
    createSelectCell(product) {
        return createElement('td', { 
            className: 'select-column',
            dataset: { column: 'select' }
        }, `
            <input type="checkbox" class="row-checkbox" data-product-id="${product.id}" title="Select product">
        `);
    }

    /**
     * Create ID cell with control buttons
     */
    createIdCell(product) {
        const cell = createElement('td', { 
            className: 'id-cell',
            dataset: { column: 'id' }
        });
        
        // Check if product is soft-deleted
        const isDeleted = product.deleted_at !== null && product.deleted_at !== undefined;
        
        if (isDeleted) {
            // Show restore and permanent delete buttons for deleted products
            const deletedDate = new Date(product.deleted_at);
            cell.innerHTML = `
                <div class="id-content">
                    <span class="cell-id deleted">${product.id}</span>
                    <div class="control-buttons">
                        <a href="/product/${product.id}" class="btn btn-sm btn-primary" title="View product details">
                            👁️
                        </a>
                        <button class="btn btn-sm btn-success" data-product-id="${product.id}" data-action="restore" title="Restore product">
                            🔄 Restore
                        </button>
                        <button class="btn btn-sm btn-danger" data-product-id="${product.id}" data-action="permanent-delete" title="Permanently delete product">
                            🗑️ Delete
                        </button>
                    </div>
                    <div class="deleted-info">
                        <small>Deleted: ${deletedDate.toLocaleDateString()}</small>
                    </div>
                </div>
            `;
        } else {
            // Show normal buttons for active products
            const isPosted = product.telegram_posted_at;
            let quickPostClass, quickPostIcon, quickPostTitle;
            
            if (isPosted) {
                quickPostClass = 'btn btn-sm btn-outline-success posted';
                quickPostIcon = '✅';
                const postedDate = new Date(product.telegram_posted_at);
                quickPostTitle = `Posted to Telegram on ${postedDate.toLocaleString()}. Click to post again.`;
            } else {
                quickPostClass = 'btn btn-sm btn-success';
                quickPostIcon = '⚡';
                quickPostTitle = 'Quick post to Telegram';
            }
            
            cell.innerHTML = `
                <div class="id-content">
                    <span class="cell-id">${product.id}</span>
                    <div class="control-buttons">
                        <a href="/product/${product.id}" class="btn btn-sm btn-primary" title="View product details">
                            👁️
                        </a>
                        <button class="btn btn-sm btn-outline" data-product-id="${product.id}" data-action="telegram" title="Send to Telegram">
                            📤
                        </button>
                        <button class="${quickPostClass}" data-product-id="${product.id}" data-action="quick-post" title="${quickPostTitle}">
                            ${quickPostIcon}
                        </button>
                    </div>
                </div>
            `;
        }
        
        // Add event listener for telegram button
        const telegramBtn = cell.querySelector('[data-action="telegram"]');
        if (telegramBtn) {
            telegramBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleSendToTelegram(product.id);
            });
        }
        
        // Add event listener for quick post button
        const quickPostBtn = cell.querySelector('[data-action="quick-post"]');
        if (quickPostBtn) {
            quickPostBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleQuickPost(product.id);
            });
        }
        
        // Add event listener for restore button
        const restoreBtn = cell.querySelector('[data-action="restore"]');
        if (restoreBtn) {
            restoreBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleRestore(product.id);
            });
        }
        
        // Add event listener for permanent delete button
        const permanentDeleteBtn = cell.querySelector('[data-action="permanent-delete"]');
        if (permanentDeleteBtn) {
            permanentDeleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handlePermanentDelete(product.id);
            });
        }
        
        return cell;
    }

    /**
     * Create images cell with thumbnails
     */
    createImagesCell(product) {
        const cell = createElement('td', {
            dataset: { column: 'images' }
        });
        
        if (!product.images || product.images.length === 0) {
            cell.innerHTML = '<span class="text-muted">No images</span>';
            return cell;
        }

        const container = createElement('div', { className: 'image-thumbnails' });
        
        // Show all images as thumbnails
        product.images.forEach((image, index) => {
            const img = createElement('img', {
                className: 'image-thumbnail',
                src: this.getImageUrl(image.url),
                alt: `Product image ${index + 1}`,
                dataset: { 
                    imageIndex: index,
                    productId: product.id 
                }
            });
            
            // Add click handler for image preview
            img.addEventListener('click', () => {
                this.openImagePreview(product.images, index);
            });
            
            // Handle image load error
            img.addEventListener('error', () => {
                img.src = this.getPlaceholderImage();
            });
            
            container.appendChild(img);
        });

        cell.appendChild(container);
        return cell;
    }

    /**
     * Create name cell
     */
    createNameCell(product) {
        const name = product.name || 'Unnamed Product';
        const cell = createElement('td', {
            dataset: { column: 'name' }
        }, `
            <span class="cell-name" title="${escapeHtml(name)}">${escapeHtml(name)}</span>
        `);
        
        // Make editable
        this.inlineEditor.makeEditable(cell, product.id, 'name', product.name);
        
        return cell;
    }

    /**
     * Create SKU cell
     */
    createSkuCell(product) {
        const sku = product.sku || '-';
        const cell = createElement('td', {
            dataset: { column: 'sku' }
        }, `
            <span title="${escapeHtml(sku)}">${escapeHtml(sku)}</span>
        `);
        
        // Make editable
        this.inlineEditor.makeEditable(cell, product.id, 'sku', product.sku);
        
        return cell;
    }

    /**
     * Create price cell
     */
    createPriceCell(product) {
        const cell = createElement('td', {
            dataset: { column: 'price' }
        });
        
        if (product.price !== null && product.price !== undefined) {
            const formattedPrice = formatCurrency(product.price, product.currency);
            cell.innerHTML = `<span class="cell-price" title="Original price">${formattedPrice}</span>`;
        } else {
            cell.innerHTML = '<span class="text-muted">-</span>';
        }
        
        // Make editable
        this.inlineEditor.makeEditable(cell, product.id, 'price', product.price);
        
        return cell;
    }

    /**
     * Create selling price cell
     */
    createSellingPriceCell(product) {
        const cell = createElement('td', {
            dataset: { column: 'selling_price' }
        });
        
        // Check if selling_price is set manually
        if (product.selling_price !== null && product.selling_price !== undefined) {
            const formattedSellingPrice = formatCurrency(product.selling_price, product.currency);
            cell.innerHTML = `<span class="cell-selling-price manual" title="Manual selling price (click to edit or clear)">${formattedSellingPrice}</span>`;
        } else if (product.sell_price !== null && product.sell_price !== undefined) {
            // Show calculated sell_price with indication it's auto-calculated
            const formattedSellPrice = formatCurrency(product.sell_price, product.currency);
            cell.innerHTML = `<span class="cell-selling-price auto" title="Auto-calculated selling price (click to set manual override)">${formattedSellPrice}</span>`;
        } else {
            cell.innerHTML = '<span class="text-muted" title="Click to set manual selling price">-</span>';
        }
        
        // Make editable - this will allow setting the manual selling_price
        this.inlineEditor.makeEditable(cell, product.id, 'selling_price', product.selling_price);
        
        return cell;
    }

    /**
     * Create availability cell
     */
    createAvailabilityCell(product) {
        const availability = product.availability || 'Unknown';
        const availabilityClass = getAvailabilityClass(availability);
        
        const cell = createElement('td', {
            dataset: { column: 'availability' }
        }, `
            <span class="cell-availability ${availabilityClass}">${escapeHtml(availability)}</span>
        `);
        
        // Make editable
        this.inlineEditor.makeEditable(cell, product.id, 'availability', product.availability);
        
        return cell;
    }

    /**
     * Create color cell
     */
    createColorCell(product) {
        const color = product.color || '-';
        const cell = createElement('td', {
            dataset: { column: 'color' }
        }, `
            <span title="${escapeHtml(color)}">${escapeHtml(color)}</span>
        `);
        
        // Make editable
        this.inlineEditor.makeEditable(cell, product.id, 'color', product.color);
        
        return cell;
    }

    /**
     * Create composition cell
     */
    createCompositionCell(product) {
        const composition = product.composition || '-';
        const cell = createElement('td', {
            dataset: { column: 'composition' }
        });
        
        if (composition === '-') {
            cell.innerHTML = '<span class="cell-composition">-</span>';
        } else {
            // Preserve line breaks and show full text
            const compositionSpan = createElement('span', { 
                className: 'cell-composition cell-composition-full'
            });
            compositionSpan.textContent = composition;
            cell.appendChild(compositionSpan);
        }
        
        // Make editable
        this.inlineEditor.makeEditable(cell, product.id, 'composition', product.composition);
        
        return cell;
    }

    /**
     * Create item cell
     */
    createItemCell(product) {
        const item = product.item || '-';
        const cell = createElement('td', {
            dataset: { column: 'item' }
        }, `
            <span class="cell-item" title="${escapeHtml(item)}">${escapeHtml(item)}</span>
        `);
        
        // Make editable
        this.inlineEditor.makeEditable(cell, product.id, 'item', product.item);
        
        return cell;
    }

    /**
     * Create store cell
     */
    createStoreCell(product) {
        const store = product.store || 'Unknown Store';
        const cell = createElement('td', {
            dataset: { column: 'store' }
        }, `
            <span class="cell-store" title="${escapeHtml(store)}">${escapeHtml(store)}</span>
        `);
        
        // Make editable
        this.inlineEditor.makeEditable(cell, product.id, 'store', product.store);
        
        return cell;
    }

    /**
     * Create sizes cell
     */
    createSizesCell(product) {
        const cell = createElement('td', {
            dataset: { column: 'sizes' }
        });
        
        if (!product.sizes || product.sizes.length === 0) {
            cell.innerHTML = '<span class="text-muted">No sizes</span>';
            return cell;
        }

        const container = createElement('div', { className: 'size-tags' });
        
        // Show all sizes
        product.sizes.forEach(size => {
            if (size.size_type === 'combination' && size.combination_data) {
                // Special handling for size combinations - display as visual grid
                const gridContainer = createElement('div', {
                    className: 'size-combination-grid'
                });
                
                // First, collect all unique size2 options to create columns
                const allSize2Options = new Set();
                Object.values(size.combination_data).forEach(options => {
                    options.forEach(opt => allSize2Options.add(opt));
                });
                const size2Columns = Array.from(allSize2Options).sort();
                
                // Create grid rows
                Object.entries(size.combination_data).forEach(([size1, size2Options]) => {
                    const row = createElement('div', {
                        className: 'combination-row'
                    });
                    
                    // Size1 label
                    const label = createElement('span', {
                        className: 'size1-label'
                    }, `${escapeHtml(size1)}:`);
                    row.appendChild(label);
                    
                    // Size2 columns
                    size2Columns.forEach(columnOption => {
                        const cell = createElement('span', {
                            className: `size2-cell ${size2Options.includes(columnOption) ? 'available' : 'empty'}`
                        }, size2Options.includes(columnOption) ? escapeHtml(columnOption) : '');
                        row.appendChild(cell);
                    });
                    
                    gridContainer.appendChild(row);
                });
                
                container.appendChild(gridContainer);
            } else if (size.size_type === 'simple' && size.size_value) {
                // Regular size display for simple sizes
                const tag = createElement('span', {
                    className: 'size-tag'
                }, escapeHtml(size.size_value));
                container.appendChild(tag);
            }
        });

        cell.appendChild(container);
        return cell;
    }

    /**
     * Create comment cell
     */
    createCommentCell(product) {
        const comment = product.comment || '';
        const displayComment = comment || '-';
        
        const cell = createElement('td', {
            dataset: { column: 'comment' }
        }, `
            <span class="cell-comment" title="${escapeHtml(comment)}">${escapeHtml(displayComment)}</span>
        `);
        
        // Make editable
        this.inlineEditor.makeEditable(cell, product.id, 'comment', product.comment);
        
        return cell;
    }

    /**
     * Create created at cell
     */
    createCreatedAtCell(product) {
        const date = formatRelativeTime(product.created_at);
        const fullDate = formatDate(product.created_at);
        
        return createElement('td', {
            dataset: { column: 'created_at' }
        }, `
            <span class="cell-date" title="${fullDate}">${date}</span>
        `);
    }

    /**
     * Create URL cell
     */
    createUrlCell(product) {
        return createElement('td', { 
            className: 'cell-url',
            dataset: { column: 'product_url' }
        }, `
            <a href="${escapeHtml(product.product_url)}" target="_blank" rel="noopener noreferrer" title="${escapeHtml(product.product_url)}">
                View
            </a>
        `);
    }

    /**
     * Get full image URL from filename
     */
    getImageUrl(filename) {
        // If filename is already a full URL, return as-is
        if (filename.startsWith('http://') || filename.startsWith('https://')) {
            return filename;
        }
        // Otherwise, construct local URL
        return this.imageBaseUrl + filename;
    }

    /**
     * Get placeholder image for failed loads
     */
    getPlaceholderImage() {
        return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzIiIGhlaWdodD0iMzIiIHZpZXdCb3g9IjAgMCAzMiAzMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjMyIiBoZWlnaHQ9IjMyIiBmaWxsPSIjRjNGNEY2Ii8+CjxwYXRoIGQ9Ik0xNiAyMEMxMy43OSAxNCAxMy43OSAxMiAxNiAxMlMxOC4yMSAxNCAxNiAyMFoiIGZpbGw9IiM5MzkzOTMiLz4KPGNpcmNsZSBjeD0iMTYiIGN5PSIxNiIgcj0iNCIgc3Ryb2tlPSIjOTM5MzkzIiBzdHJva2Utd2lkdGg9IjIiLz4KPC9zdmc+';
    }

    /**
     * Open image preview modal
     */
    openImagePreview(images, startIndex = 0) {
        if (window.imageModal && images && images.length > 0) {
            window.imageModal.open(images, startIndex);
        } else {
            // Fallback: open first image in new tab
            if (images[startIndex]) {
                const imageUrl = this.getImageUrl(images[startIndex].url);
                window.open(imageUrl, '_blank');
            }
        }
    }

    /**
     * Handle product update from inline editor
     */
    async handleProductUpdate(productId, field, newValue) {
        if (this.onUpdateProduct) {
            await this.onUpdateProduct(productId, field, newValue);
        }
        
        // Update local product data
        const product = this.products.find(p => p.id === productId);
        if (product) {
            product[field] = newValue;
        }
    }

    /**
     * Handle selection change
     */
    handleSelectionChange(selectedIds, selectedProducts) {
        console.log(`Selected ${selectedIds.length} products:`, selectedIds);
    }

    /**
     * Handle send to telegram for individual product
     */
    handleSendToTelegram(productId) {
        // First select the product in the row selection system
        if (this.rowSelection) {
            this.rowSelection.clearSelection();
            this.rowSelection.selectProducts([productId]);
        }
        
        // Open the telegram modal
        if (window.telegramModal) {
            window.telegramModal.openModal();
        } else {
            console.warn('Telegram modal not available');
        }
    }

    /**
     * Handle quick post for individual product
     */
    handleQuickPost(productId) {
        // Trigger quick post with specific product ID (don't modify selection)
        if (window.telegramModal) {
            window.telegramModal.quickPost(productId);
        } else {
            console.warn('Telegram modal not available');
        }
    }

    /**
     * Handle restore for soft-deleted product
     */
    async handleRestore(productId) {
        try {
            if (!confirm('Are you sure you want to restore this product?')) {
                return;
            }

            console.log(`Restoring product ${productId}`);
            
            // Call API to restore product
            const response = await api.restoreProduct(productId);
            
            console.log(`Successfully restored product ${productId}`);
            
            // Reload the current page to reflect changes
            if (window.app) {
                await window.app.loadProducts(window.app.currentPage, false);
            }
            
            // Show success message
            if (window.app && window.app.showNotification) {
                window.app.showNotification(`Product restored successfully`, 'success');
            }
            
        } catch (error) {
            console.error(`Failed to restore product ${productId}:`, error);
            
            // Show error message
            if (window.app && window.app.showNotification) {
                window.app.showNotification(`Failed to restore product: ${error.message}`, 'error');
            }
        }
    }

    /**
     * Handle permanent delete for soft-deleted product
     */
    async handlePermanentDelete(productId) {
        try {
            if (!confirm('Are you sure you want to permanently delete this product? This action cannot be undone!')) {
                return;
            }

            console.log(`Permanently deleting product ${productId}`);
            
            // Call API to permanently delete product
            const response = await api.deleteProduct(productId, 'hard');
            
            console.log(`Successfully permanently deleted product ${productId}`);
            
            // Reload the current page to reflect changes
            if (window.app) {
                await window.app.loadProducts(window.app.currentPage, false);
            }
            
            // Show success message
            if (window.app && window.app.showNotification) {
                window.app.showNotification(`Product permanently deleted`, 'warning');
            }
            
        } catch (error) {
            console.error(`Failed to permanently delete product ${productId}:`, error);
            
            // Show error message
            if (window.app && window.app.showNotification) {
                window.app.showNotification(`Failed to permanently delete product: ${error.message}`, 'error');
            }
        }
    }

    /**
     * Clear table data
     */
    clear() {
        this.tbody.innerHTML = '';
        this.updateTotalCount(0);
    }
}

// Export for use in other modules
window.ProductTable = ProductTable;