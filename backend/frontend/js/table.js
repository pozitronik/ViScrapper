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
        
        if (this.onDataChange) {
            this.onDataChange(products, totalCount);
        }
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
        row.appendChild(this.createAvailabilityCell(product));
        row.appendChild(this.createColorCell(product));
        row.appendChild(this.createCompositionCell(product));
        row.appendChild(this.createItemCell(product));
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
        return createElement('td', { className: 'select-column' }, `
            <input type="checkbox" class="row-checkbox" data-product-id="${product.id}" title="Select product">
        `);
    }

    /**
     * Create ID cell with control buttons
     */
    createIdCell(product) {
        const cell = createElement('td', { className: 'id-cell' });
        
        cell.innerHTML = `
            <div class="id-content">
                <span class="cell-id">${product.id}</span>
                <div class="control-buttons">
                    <button class="btn btn-sm btn-telegram" data-product-id="${product.id}" title="Send to Telegram">
                        📤
                    </button>
                </div>
            </div>
        `;
        
        // Add event listener for telegram button
        const telegramBtn = cell.querySelector('.btn-telegram');
        if (telegramBtn) {
            telegramBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleSendToTelegram(product.id);
            });
        }
        
        return cell;
    }

    /**
     * Create images cell with thumbnails
     */
    createImagesCell(product) {
        const cell = createElement('td');
        
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
        const cell = createElement('td', {}, `
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
        const cell = createElement('td', {}, `
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
        const cell = createElement('td');
        
        if (product.price !== null && product.price !== undefined) {
            const formattedPrice = formatCurrency(product.price, product.currency);
            let priceDisplay = formattedPrice;
            
            // Add sell price if available
            if (product.sell_price !== null && product.sell_price !== undefined) {
                const formattedSellPrice = formatCurrency(product.sell_price, product.currency);
                priceDisplay = `${formattedPrice} / ${formattedSellPrice}`;
            }
            
            cell.innerHTML = `<span class="cell-price" title="Original Price / Sell Price">${priceDisplay}</span>`;
        } else {
            cell.innerHTML = '<span class="text-muted">-</span>';
        }
        
        // Make editable
        this.inlineEditor.makeEditable(cell, product.id, 'price', product.price);
        
        return cell;
    }

    /**
     * Create availability cell
     */
    createAvailabilityCell(product) {
        const availability = product.availability || 'Unknown';
        const availabilityClass = getAvailabilityClass(availability);
        
        const cell = createElement('td', {}, `
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
        const cell = createElement('td', {}, `
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
        const cell = createElement('td');
        
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
        const cell = createElement('td', {}, `
            <span class="cell-item" title="${escapeHtml(item)}">${escapeHtml(item)}</span>
        `);
        
        // Make editable
        this.inlineEditor.makeEditable(cell, product.id, 'item', product.item);
        
        return cell;
    }

    /**
     * Create sizes cell
     */
    createSizesCell(product) {
        const cell = createElement('td');
        
        if (!product.sizes || product.sizes.length === 0) {
            cell.innerHTML = '<span class="text-muted">No sizes</span>';
            return cell;
        }

        const container = createElement('div', { className: 'size-tags' });
        
        // Show all sizes
        product.sizes.forEach(size => {
            const tag = createElement('span', {
                className: 'size-tag'
            }, escapeHtml(size.name));
            container.appendChild(tag);
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
        
        const cell = createElement('td', {}, `
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
        
        return createElement('td', {}, `
            <span class="cell-date" title="${fullDate}">${date}</span>
        `);
    }

    /**
     * Create URL cell
     */
    createUrlCell(product) {
        return createElement('td', { className: 'cell-url' }, `
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
     * Clear table data
     */
    clear() {
        this.tbody.innerHTML = '';
        this.updateTotalCount(0);
    }
}

// Export for use in other modules
window.ProductTable = ProductTable;