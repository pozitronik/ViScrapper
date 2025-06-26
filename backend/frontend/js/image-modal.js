// Image preview modal functionality

class ImageModal {
    constructor() {
        this.modal = document.getElementById('image-modal');
        this.modalImage = document.getElementById('modal-image');
        this.modalCounter = document.querySelector('.image-modal-counter');
        this.modalThumbnails = document.getElementById('modal-thumbnails');
        this.closeBtn = document.querySelector('.image-modal-close');
        this.prevBtn = document.querySelector('.image-modal-prev');
        this.nextBtn = document.querySelector('.image-modal-next');
        this.backdrop = document.querySelector('.image-modal-backdrop');
        
        this.images = [];
        this.currentIndex = 0;
        this.imageBaseUrl = '/images/';
        
        this.setupEventListeners();
    }

    /**
     * Set up event listeners for modal controls
     */
    setupEventListeners() {
        // Close button
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.close());
        }

        // Backdrop click to close
        if (this.backdrop) {
            this.backdrop.addEventListener('click', () => this.close());
        }

        // Navigation buttons
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', () => this.previous());
        }

        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => this.next());
        }

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!this.isOpen()) return;

            switch (e.key) {
                case 'Escape':
                    this.close();
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    this.previous();
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.next();
                    break;
                case ' ':
                    e.preventDefault();
                    this.next();
                    break;
            }
        });

        // Prevent modal content clicks from closing modal
        const modalContent = document.querySelector('.image-modal-content');
        if (modalContent) {
            modalContent.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }
    }

    /**
     * Open modal with images
     */
    open(images, startIndex = 0) {
        if (!images || images.length === 0) return;

        this.images = images;
        this.currentIndex = Math.max(0, Math.min(startIndex, images.length - 1));

        this.updateDisplay();
        this.renderThumbnails();

        // Show modal
        if (this.modal) {
            this.modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden'; // Prevent body scroll
        }

        // Preload images for smoother navigation
        this.preloadImages();
    }

    /**
     * Close modal
     */
    close() {
        if (this.modal) {
            this.modal.classList.add('hidden');
            document.body.style.overflow = ''; // Restore body scroll
        }

        // Clear data
        this.images = [];
        this.currentIndex = 0;
    }

    /**
     * Go to previous image
     */
    previous() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this.updateDisplay();
        }
    }

    /**
     * Go to next image
     */
    next() {
        if (this.currentIndex < this.images.length - 1) {
            this.currentIndex++;
            this.updateDisplay();
        }
    }

    /**
     * Go to specific image index
     */
    goToIndex(index) {
        if (index >= 0 && index < this.images.length) {
            this.currentIndex = index;
            this.updateDisplay();
        }
    }

    /**
     * Check if modal is open
     */
    isOpen() {
        return this.modal && !this.modal.classList.contains('hidden');
    }

    /**
     * Update modal display with current image
     */
    updateDisplay() {
        if (!this.images[this.currentIndex]) return;

        const currentImage = this.images[this.currentIndex];

        // Update main image
        if (this.modalImage) {
            this.modalImage.src = this.getImageUrl(currentImage.url);
            this.modalImage.alt = `Product image ${this.currentIndex + 1}`;
        }

        // Update counter
        if (this.modalCounter) {
            this.modalCounter.textContent = `${this.currentIndex + 1} of ${this.images.length}`;
        }

        // Update navigation buttons
        this.updateNavigationButtons();

        // Update thumbnail active state
        this.updateThumbnailActive();
    }

    /**
     * Update navigation button states
     */
    updateNavigationButtons() {
        if (this.prevBtn) {
            this.prevBtn.disabled = this.currentIndex === 0;
        }

        if (this.nextBtn) {
            this.nextBtn.disabled = this.currentIndex === this.images.length - 1;
        }
    }

    /**
     * Render thumbnail strip
     */
    renderThumbnails() {
        if (!this.modalThumbnails) return;

        this.modalThumbnails.innerHTML = '';

        this.images.forEach((image, index) => {
            const thumbnail = createElement('img', {
                className: `modal-thumbnail ${index === this.currentIndex ? 'active' : ''}`,
                src: this.getImageUrl(image.url),
                alt: `Thumbnail ${index + 1}`,
                dataset: { index }
            });

            // Add click handler
            thumbnail.addEventListener('click', () => {
                this.goToIndex(index);
            });

            // Handle thumbnail load error
            thumbnail.addEventListener('error', () => {
                thumbnail.src = this.getPlaceholderImage();
            });

            this.modalThumbnails.appendChild(thumbnail);
        });
    }

    /**
     * Update active thumbnail
     */
    updateThumbnailActive() {
        if (!this.modalThumbnails) return;

        const thumbnails = this.modalThumbnails.querySelectorAll('.modal-thumbnail');
        thumbnails.forEach((thumbnail, index) => {
            if (index === this.currentIndex) {
                thumbnail.classList.add('active');
            } else {
                thumbnail.classList.remove('active');
            }
        });

        // Scroll active thumbnail into view
        const activeThumbnail = thumbnails[this.currentIndex];
        if (activeThumbnail) {
            activeThumbnail.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest',
                inline: 'center'
            });
        }
    }

    /**
     * Preload images for smoother navigation
     */
    preloadImages() {
        // Preload current, next, and previous images
        const indicesToPreload = [
            this.currentIndex - 1,
            this.currentIndex,
            this.currentIndex + 1
        ].filter(index => index >= 0 && index < this.images.length);

        indicesToPreload.forEach(index => {
            if (this.images[index]) {
                const img = new Image();
                img.src = this.getImageUrl(this.images[index].url);
            }
        });
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
}

// Create global instance
window.imageModal = new ImageModal();

// Export for use in other modules
window.ImageModal = ImageModal;