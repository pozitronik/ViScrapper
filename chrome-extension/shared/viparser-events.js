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
        
        // Handle the color/image update
        this.core.handleColorUpdate(update);
        
        // Note: Full panel refresh for Tommy Hilfiger is handled by separate spaPanelRefresh message
        // This is different from Carter's URL-based autoRefreshPanel mechanism
      } else if (request.action === 'autoRefreshPanel') {
        this.handleAutoRefresh(request.url);
      } else if (request.action === 'spaPanelRefresh') {
        this.handleSpaRefresh(request.source, request.reason);
      }
    });
  }

  /**
   * Обработка автоматического обновления при смене URL (для side panel)
   */
  handleAutoRefresh(newUrl) {
    console.log('Auto-refresh triggered for URL:', newUrl);
    console.log('Full refresh starting using proven Carter\'s mechanism...');
    
    // Show refresh indication
    this.ui.showRefreshIndication('Обновление данных...');
    
    // Reload data using the same mechanism as Carter's
    if (typeof refreshPanelData === 'function') {
      console.log('Calling refreshPanelData() for full sidepanel refresh');
      refreshPanelData();
    } else {
      console.log('refreshPanelData not available (popup context), triggering manual reload...');
      // For popup, do a lighter refresh by reloading product data
      this.loadProductData();
    }
  }

  /**
   * Обработка обновления для SPA сайтов (без смены URL)
   * Используется для Tommy Hilfiger когда контент меняется но URL остается тот же
   */
  handleSpaRefresh(source, reason) {
    console.log('SPA refresh triggered:', source, reason);
    console.log('Full refresh for SPA content change (no URL change)');
    
    // Show refresh indication
    this.ui.showRefreshIndication('Обновление после смены цвета...');
    
    // Direct refresh - same logic as handleAutoRefresh but for SPA
    if (typeof refreshPanelData === 'function') {
      console.log('Calling refreshPanelData() for SPA content refresh');
      refreshPanelData();
    } else {
      console.log('refreshPanelData not available (popup context), doing direct data reload...');
      // For popup, reload product data directly
      this.loadProductData();
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
    
    // Submit button and dropdown functionality
    if (submitBtn) {
      // Main submit button click (always normal submit)
      submitBtn.addEventListener('click', async () => {
        await this.handleSubmit(closeOnSubmit);
      });
      
      // Dropdown toggle button click
      const dropdownToggleBtn = document.getElementById('dropdownToggleBtn');
      if (dropdownToggleBtn) {
        dropdownToggleBtn.addEventListener('click', async (event) => {
          event.preventDefault();
          await this.toggleDropdown();
        });
      }
      
      // All colors button click
      const submitAllColorsBtn = document.getElementById('submitAllColorsBtn');
      if (submitAllColorsBtn) {
        submitAllColorsBtn.addEventListener('click', async () => {
          await this.handleSubmitAllColors(closeOnSubmit);
        });
      }
      
      // Close dropdown when clicking outside
      document.addEventListener('click', (event) => {
        const dropdownContainer = document.getElementById('dropdownContainer');
        const dropdownContent = document.getElementById('dropdownContent');
        
        if (dropdownContainer && dropdownContent && 
            !dropdownContainer.contains(event.target)) {
          dropdownContent.style.display = 'none';
        }
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
      if (!tab.url.includes('carters.com') && !tab.url.includes('usa.tommy.com') && !tab.url.includes('calvinklein.us')) {
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
      } else if (tab.url.includes('calvinklein.us')) {
        // Calvin Klein: Always start observer to track panel refresh on color switch
        console.log('Calvin Klein: Starting color observer to track data refresh...');
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
      
      // Debug: Log the response to understand what's happening
      console.log('VIParserEvents.loadProductData: Response received:', {
        hasError: !!response.error,
        hasData: !!response.data,
        dataKeys: response.data ? Object.keys(response.data) : null,
        error: response.error
      });
      
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
      console.log('VIParserEvents.loadProductData: Updating data preview with:', {
        sku: response.data?.sku,
        color: response.data?.color,
        name: response.data?.name,
        price: response.data?.price,
        imageCount: response.data?.all_image_urls?.length
      });
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

  // Note: refreshPreviewAfterColorChange() method removed
  // Tommy Hilfiger now uses the same autoRefreshPanel mechanism as Carter's

  /**
   * Переключение состояния dropdown меню
   */
  async toggleDropdown() {
    const dropdownContent = document.getElementById('dropdownContent');
    const submitBtn = document.getElementById('submitBtn');
    
    if (!dropdownContent || !submitBtn) return;
    
    // If dropdown is visible, hide it; if hidden, show it
    if (dropdownContent.style.display === 'none' || !dropdownContent.style.display) {
      dropdownContent.style.display = 'block';
    } else {
      dropdownContent.style.display = 'none';
    }
  }

  /**
   * Обработка отправки всех цветов (универсальная версия)
   */
  async handleSubmitAllColors(closeOnSubmit = false) {
    const submitBtn = document.getElementById('submitBtn');
    const submitAllColorsBtn = document.getElementById('submitAllColorsBtn');
    const dropdownContent = document.getElementById('dropdownContent');
    const statusCard = document.getElementById('productStatus');
    
    if (!submitBtn || !this.core.appState.availableColors) return;
    
    // Close dropdown
    if (dropdownContent) dropdownContent.style.display = 'none';
    
    // Disable buttons during processing
    submitBtn.disabled = true;
    if (submitAllColorsBtn) submitAllColorsBtn.disabled = true;
    
    const colors = this.core.appState.availableColors;
    let successCount = 0;
    let failureCount = 0;
    const failedColors = [];

    // Get selected images before starting bulk scraping
    const selectedImages = this.core.getSelectedImages();
    console.log(`[Bulk Scraping] Using ${selectedImages.length} selected images for all colors`);

    try {
      // Show initial progress
      if (statusCard) {
        statusCard.className = 'status-card warning';
        statusCard.innerHTML = `<div class="status-text">Отправка цветов: 0/${colors.length}</div>`;
      }
      submitBtn.textContent = `Отправка цветов: 0/${colors.length}`;

      // Process each color sequentially (one at a time)
      for (let i = 0; i < colors.length; i++) {
        const color = colors[i];
        
        try {
          console.log(`Processing color ${i + 1}/${colors.length}: ${color.name} (${color.code})`);
          
          // Update progress display
          if (statusCard) {
            statusCard.innerHTML = `<div class="status-text">Отправка цвета: ${color.name} (${i + 1}/${colors.length})</div>`;
          }
          submitBtn.textContent = `Отправка: ${color.name} (${i + 1}/${colors.length})`;
          
          // Send scrape request for this color and wait for completion
          const result = await this.scrapeColorVariant(color, selectedImages);
          
          if (result.success) {
            successCount++;
            console.log(`Successfully scraped color: ${color.name}`);
            
            // Update progress with success
            if (statusCard) {
              statusCard.className = 'status-card existing';
              statusCard.innerHTML = `<div class="status-text">✓ ${color.name} отправлен (${successCount}/${colors.length})</div>`;
            }
            submitBtn.textContent = `✓ ${color.name} отправлен (${successCount}/${colors.length})`;
            
            // Short delay to show success before moving to next color
            await new Promise(resolve => setTimeout(resolve, 500));
          } else {
            failureCount++;
            failedColors.push(`${color.name}: ${result.error}`);
            console.error(`Failed to scrape color ${color.name}:`, result.error);
            
            // Update progress with failure
            if (statusCard) {
              statusCard.className = 'status-card warning';
              statusCard.innerHTML = `<div class="status-text">✗ ${color.name} ошибка (${failureCount} неудач)</div>`;
            }
            submitBtn.textContent = `✗ ${color.name} ошибка (${failureCount} неудач)`;
            
            // Short delay before continuing to next color
            await new Promise(resolve => setTimeout(resolve, 800));
          }
          
        } catch (error) {
          failureCount++;
          failedColors.push(`${color.name}: ${error.message}`);
          console.error(`Error processing color ${color.name}:`, error);
          
          // Update progress with error
          if (statusCard) {
            statusCard.className = 'status-card unavailable';
            statusCard.innerHTML = `<div class="status-text">✗ ${color.name} критическая ошибка</div>`;
          }
          submitBtn.textContent = `✗ ${color.name} критическая ошибка`;
          
          // Longer delay for critical errors
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }

      // Show final results
      const message = `Отправлено: ${successCount}/${colors.length} цветов`;
      
      if (statusCard) {
        const statusClass = failureCount === 0 ? 'existing' : 'warning';
        statusCard.className = `status-card ${statusClass}`;
        statusCard.innerHTML = `<div class="status-text">${message}</div>`;
      }
      
      submitBtn.textContent = failureCount === 0 ? 'Все цвета отправлены!' : message;
      
      // Show failed colors if any
      if (failedColors.length > 0) {
        console.warn('Failed colors:', failedColors);
        // Could show a more detailed error message in the future
      }

    } catch (error) {
      console.error('Error in handleSubmitAllColors:', error);
      submitBtn.textContent = 'Ошибка отправки - попробуйте снова';
      if (statusCard) {
        statusCard.className = 'status-card unavailable';
        statusCard.innerHTML = `<div class="status-text">Ошибка отправки цветов</div>`;
      }
    } finally {
      // Re-enable buttons after delay
      setTimeout(() => {
        if (closeOnSubmit && failureCount === 0) {
          window.close();
        } else {
          this.core.updateButtonsState();
          if (submitAllColorsBtn) submitAllColorsBtn.disabled = false;
        }
      }, closeOnSubmit && failureCount === 0 ? 2000 : 3000);
    }
  }

  /**
   * Скрапинг конкретного цветового варианта с повышенным таймаутом
   */
  async scrapeColorVariant(color, selectedImages = null) {
    try {
      console.log(`[ColorScraper] Starting scrape for ${color.name} (${color.code}) with ${selectedImages?.length || 'all'} images`);
      
      const response = await new Promise((resolve, reject) => {
        // Set a timeout for the scraping operation
        const timeout = setTimeout(() => {
          reject(new Error(`Timeout scraping color ${color.name} after 45 seconds`));
        }, 45000); // Increased timeout
        
        chrome.runtime.sendMessage(
          { 
            action: 'scrapeColorVariant',
            color: color,
            selectedImages: selectedImages
          },
          (response) => {
            clearTimeout(timeout);
            
            if (chrome.runtime.lastError) {
              console.error(`[ColorScraper] Chrome runtime error for ${color.name}:`, chrome.runtime.lastError);
              reject(new Error(chrome.runtime.lastError.message));
            } else if (!response) {
              console.error(`[ColorScraper] Empty response for ${color.name}`);
              reject(new Error(`Empty response received for ${color.name}`));
            } else {
              console.log(`[ColorScraper] Received response for ${color.name}:`, response.success ? 'SUCCESS' : response.error);
              resolve(response);
            }
          }
        );
      });
      
      console.log(`[ColorScraper] Completed scrape for ${color.name}:`, response.success ? 'SUCCESS' : 'FAILED');
      return response;
    } catch (error) {
      console.error(`[ColorScraper] Error scraping color variant ${color.name}:`, error);
      return { success: false, error: error.message };
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