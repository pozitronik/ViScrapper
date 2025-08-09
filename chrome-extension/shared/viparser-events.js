/**
 * VIParser Events - Shared event handling functionality for popup and side panel
 * Handles message listeners, submit logic, and event coordination
 */

class VIParserEvents {
  constructor(viParserCore, viParserUI) {
    this.core = viParserCore;
    this.ui = viParserUI;
  }

  /**
   * Настройка слушателя сообщений от content script и background script
   */
  setupMessageListener() {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      console.log('Received message:', request);
      
      if (request.action === 'productChanged') {
        this.core.handleProductChangedNotification(request.reason);
      } else if (request.action === 'updateColorInPopup') {
        // Legacy Carter's color update (only color)
        this.core.handleColorUpdate(request.color);
      } else if (request.action === 'colorUpdated') {
        // New format supporting both color and images (Tommy Hilfiger + Carter's)
        const update = {
          color: request.color
        };
        if (request.images && request.images.length > 0) {
          update.images = request.images;
          update.source = request.source;
        }
        this.core.handleColorUpdate(update);
      } else if (request.action === 'autoRefreshPanel') {
        this.handleAutoRefresh(request.url);
      }
    });
  }

  /**
   * Обработка автоматического обновления при смене URL (для side panel)
   */
  handleAutoRefresh(newUrl) {
    console.log('Auto-refresh triggered for URL:', newUrl);
    
    // Show refresh indication
    this.ui.showRefreshIndication('Обновление данных...');
    
    // Reload data
    if (typeof refreshPanelData === 'function') {
      refreshPanelData();
    }
  }

  /**
   * Настройка основных обработчиков событий
   */
  setupEventHandlers(options = {}) {
    const {
      submitBtnId = 'submitBtn',
      refreshBtnId = 'refreshBtn',
      manualRefreshBtnId = 'manualRefreshBtn',
      onRefresh = null,
      onManualRefresh = null,
      closeOnSubmit = false
    } = options;

    const submitBtn = document.getElementById(submitBtnId);
    const refreshBtn = document.getElementById(refreshBtnId);
    const manualRefreshBtn = document.getElementById(manualRefreshBtnId);
    
    // Submit button
    if (submitBtn) {
      submitBtn.addEventListener('click', async () => {
        await this.handleSubmit(closeOnSubmit);
      });
    }
    
    // Page refresh button (old)
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        if (onRefresh) {
          onRefresh();
        } else {
          chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            chrome.tabs.reload(tabs[0].id);
            if (closeOnSubmit) {
              window.close();
            }
          });
        }
      });
    }
    
    // Manual data refresh button (new)
    if (manualRefreshBtn) {
      manualRefreshBtn.addEventListener('click', () => {
        console.log('Manual refresh button clicked');
        
        // Show refresh indication
        this.ui.showRefreshIndication('Обновление данных...');
        
        // Execute refresh function
        if (onManualRefresh) {
          onManualRefresh();
        } else if (typeof refreshPanelData === 'function') {
          refreshPanelData();
        }
      });
    }
    
    // Update initial button state
    this.core.updateButtonsState();
  }

  /**
   * Обработка отправки данных (универсальная версия)
   */
  async handleSubmit(closeOnSubmit = false) {
    const submitBtn = document.getElementById('submitBtn');
    const commentInput = document.getElementById('commentInput');
    
    if (!submitBtn) return;
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Отправка...';
    
    try {
      // Get only selected images
      const selectedImages = this.core.getSelectedImages();
      
      const dataToSend = {
        ...this.core.appState.productData,
        comment: commentInput ? commentInput.value.trim() : '',
        // Replace all images with selected ones
        all_image_urls: selectedImages,
        main_image_url: selectedImages.length > 0 ? selectedImages[0] : null
      };
      
      const response = await this.core.submitData(dataToSend);
      
      if (response.error) {
        // Show error in button
        submitBtn.textContent = 'Ошибка отправки - попробуйте снова';
        setTimeout(() => {
          this.core.updateButtonsState();
        }, 3000);
      } else {
        // Show message with product link
        const statusCard = document.getElementById('productStatus');
        
        if (response.productUrl && response.message) {
          // Update status to green with link
          if (statusCard) {
            statusCard.classList.remove('new', 'existing', 'unavailable', 'warning');
            statusCard.classList.add('existing');
            statusCard.innerHTML = `<div class="status-text"><a href="${response.productUrl}" target="_blank" style="color: #4ade80; text-decoration: underline;">${response.message}</a></div>`;
          }
          
          submitBtn.textContent = 'Данные отправлены!';
        } else {
          submitBtn.textContent = 'Данные отправлены!';
        }
        
        // Reset form after delay
        setTimeout(() => {
          if (closeOnSubmit) {
            window.close();
          } else {
            this.core.updateButtonsState();
            if (commentInput) {
              commentInput.value = '';
              commentInput.dispatchEvent(new Event('input')); // Trigger char counter update
            }
          }
        }, closeOnSubmit ? 2000 : 2000);
      }
      
    } catch (error) {
      console.error('Error submitting data:', error);
      submitBtn.textContent = 'Ошибка отправки - попробуйте снова';
      setTimeout(() => {
        this.core.updateButtonsState();
      }, 3000);
    } finally {
      submitBtn.disabled = false;
    }
  }

  /**
   * Запуск наблюдателя за цветом если нужно (для Carter's и если цвет отсутствует)
   */
  async startColorObserverIfNeeded() {
    try {
      // Get information about current active tab
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      
      if (!tab || !tab.url) {
        return;
      }
      
      // Check if this is a site that supports color observer
      if (!tab.url.includes('carters.com') && !tab.url.includes('usa.tommy.com')) {
        console.log('Site does not support color observer, skipping');
        return;
      }
      
      // Determine if observer should start based on site
      let shouldStartObserver = false;
      
      if (tab.url.includes('carters.com')) {
        // Carter's: Start observer only if color is missing
        const colorValueElement = document.querySelector('[data-field="color"] .data-value');
        if (colorValueElement) {
          const colorText = colorValueElement.textContent.trim();
          if (colorText === 'Отсутствует' || colorText === '' || colorValueElement.classList.contains('missing')) {
            console.log('Carter\'s: Color is missing, starting observer...');
            shouldStartObserver = true;
          } else {
            console.log('Carter\'s: Color already available:', colorText);
          }
        }
      } else if (tab.url.includes('usa.tommy.com')) {
        // Tommy Hilfiger: Always start observer to track image changes on color switch
        console.log('Tommy Hilfiger: Starting color observer to track image changes...');
        shouldStartObserver = true;
      }
      
      if (shouldStartObserver) {
        const response = await this.core.startColorObserver();
        
        if (response.success) {
          console.log('Color observer started successfully');
        } else {
          console.log('Failed to start color observer:', response.error);
        }
      }
      
    } catch (error) {
      console.error('Error starting color observer:', error);
    }
  }

  /**
   * Остановка наблюдателя за цветом
   */
  async stopColorObserver() {
    try {
      const response = await this.core.stopColorObserver();
      
      if (response.success) {
        console.log('Color observer stopped successfully');
      }
      
    } catch (error) {
      console.error('Error stopping color observer:', error);
    }
  }

  /**
   * Инициализация полного приложения (универсальная версия)
   */
  async initializeApp(options = {}) {
    const {
      setupBranding = true,
      loadSettings = false,
      checkBackend = true,
      loadProductData = true,
      startColorObserver = false,
      closeOnSubmit = false,
      onManualRefresh = null
    } = options;

    console.log('VIParser app initialized');
    
    // Site branding setup
    if (setupBranding) {
      await this.setupSiteBranding();
    }
    
    // Settings loading
    if (loadSettings && typeof loadSettings === 'function') {
      await loadSettings();
    }
    
    // Initialize UI elements
    this.ui.initializeCommentCounter();
    
    // Setup message listener
    this.setupMessageListener();
    
    // Check backend status
    if (checkBackend) {
      await this.checkBackendStatus();
    }
    
    // Load product data
    if (loadProductData) {
      await this.loadProductData();
    }
    
    // Setup event handlers
    this.setupEventHandlers({
      closeOnSubmit,
      onManualRefresh
    });
    
    // Start color observer if needed
    if (startColorObserver) {
      await this.startColorObserverIfNeeded();
    }
  }

  /**
   * Setup site branding (delegated to core)
   */
  async setupSiteBranding() {
    try {
      const siteInfo = await this.core.detectSite();
      console.log('Detected site:', siteInfo);
      
      // Apply corresponding class to body
      document.body.className = `site-${siteInfo.id}`;
      
      // Update title
      const titleElement = document.getElementById('appTitle');
      if (titleElement) {
        if (siteInfo.supported) {
          titleElement.textContent = `VIParser: ${siteInfo.name}`;
        } else {
          titleElement.textContent = 'VIParser';
        }
      }
      
      console.log(`Applied branding for ${siteInfo.name} (supported: ${siteInfo.supported})`);
      
      return siteInfo;
      
    } catch (error) {
      console.error('Error setting up site branding:', error);
      return { id: 'unsupported', name: 'VIParser', supported: false };
    }
  }

  /**
   * Check backend status (delegated to core with UI updates)
   */
  async checkBackendStatus() {
    this.ui.updateBackendStatusUI('checking', 'Проверка...');
    
    try {
      const response = await this.core.checkBackendStatus();
      
      if (response.status === 'available') {
        this.ui.updateBackendStatusUI('available', 'Доступен');
      } else {
        this.ui.updateBackendStatusUI('unavailable', 'Недоступен');
      }
      
    } catch (error) {
      console.error('Error checking backend status:', error);
      this.ui.updateBackendStatusUI('unavailable', 'Ошибка');
    }
  }

  /**
   * Load product data (delegated to core with UI updates)
   */
  async loadProductData() {
    const previewContainer = document.getElementById('dataPreview');
    const productStatus = document.getElementById('productStatus');
    
    try {
      this.ui.showLoadingState('dataPreview', 'Загрузка данных...');
      if (productStatus) {
        productStatus.innerHTML = '<div class="loading">Проверка статуса...</div>';
      }
      
      // Request data through core
      const response = await this.core.loadProductData();
      
      if (response.error) {
        // Hide data preview on error
        if (previewContainer) {
          previewContainer.style.display = 'none';
        }
        
        // Show error in product status
        if (response.needsRefresh) {
          this.core.updateProductStatusUI({ 
            status: 'changed', 
            message: 'Нужно обновить страницу' 
          });
        } else {
          this.core.updateProductStatusUI({ 
            status: 'error', 
            message: 'Не удалось загрузить данные' 
          });
        }
        
        // Hide comment container
        const commentContainer = document.querySelector('.comment-container');
        if (commentContainer) {
          commentContainer.style.display = 'none';
        }
        
        return;
      }
      
      // Update interface
      this.ui.updateDataPreview(response.data);
      
      // Check product status on backend
      if (response.data && (response.data.sku || response.data.product_url)) {
        await this.checkProductStatus(response.data);
      } else {
        this.core.updateProductStatusUI({ status: 'unknown', message: 'Недостаточно данных для поиска' });
      }
      
    } catch (error) {
      console.error('Error loading product data:', error);
      
      // Hide data preview
      if (previewContainer) {
        previewContainer.style.display = 'none';
      }
      
      // Show error in status
      this.core.updateProductStatusUI({ 
        status: 'error', 
        message: 'Не удалось загрузить данные' 
      });
      
      // Hide comment container
      const commentContainer = document.querySelector('.comment-container');
      if (commentContainer) {
        commentContainer.style.display = 'none';
      }
    }
  }

  /**
   * Check product status (delegated to core with UI updates)
   */
  async checkProductStatus(data) {
    try {
      const response = await this.core.checkProductStatus(data);
      this.core.updateProductStatusUI(response);
      
    } catch (error) {
      console.error('Error checking product status:', error);
      this.core.updateProductStatusUI({ status: 'error', message: 'Не удалось проверить статус' });
    }
  }

  /**
   * Setup cleanup handlers
   */
  setupCleanupHandlers() {
    // Stop observer when window is closed
    window.addEventListener('beforeunload', () => {
      this.stopColorObserver();
    });
  }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
  window.VIParserEvents = VIParserEvents;
}