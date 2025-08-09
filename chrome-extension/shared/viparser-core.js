/**
 * VIParser Core - Shared functionality for popup and side panel
 * Contains common logic used by both interfaces
 */

class VIParserCore {
  constructor() {
    this.appState = {
      backendStatus: 'checking',
      productData: null,
      productStatus: null,
      isDataValid: false
    };
  }

  // Note: Availability constants are defined in BaseParser and referenced here

  /**
   * Определение текущего сайта и получение информации о брендинге
   */
  async detectSite() {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      
      if (!tab || !tab.url) {
        console.log('No tab URL available');
        return { id: 'unsupported', name: 'VIParser', supported: false };
      }
      
      console.log('Detecting site for URL:', tab.url);
      
      if (tab.url.includes('victoriassecret.com')) {
        return { id: 'victoriassecret', name: "Victoria's Secret", supported: true };
      } else if (tab.url.includes('calvinklein.us')) {
        return { id: 'calvinklein', name: 'Calvin Klein', supported: true };
      } else if (tab.url.includes('carters.com')) {
        return { id: 'carters', name: "Carter's", supported: true };
      } else if (tab.url.includes('usa.tommy.com')) {
        return { id: 'tommy', name: 'Tommy Hilfiger', supported: true };
      } else {
        console.log('Unsupported site detected:', tab.url);
        return { id: 'unsupported', name: 'VIParser', supported: false };
      }
    } catch (error) {
      console.error('Error detecting site:', error);
      return { id: 'unsupported', name: 'VIParser', supported: false };
    }
  }

  /**
   * Проверка статуса бэкенда
   */
  async checkBackendStatus() {
    try {
      const response = await new Promise((resolve) => {
        chrome.runtime.sendMessage(
          { action: 'checkBackendStatus' },
          resolve
        );
      });
      
      this.appState.backendStatus = response.status;
      return response;
    } catch (error) {
      console.error('Error checking backend status:', error);
      this.appState.backendStatus = 'unavailable';
      return { status: 'unavailable', message: 'Ошибка' };
    }
  }

  /**
   * Загрузка данных продукта
   */
  async loadProductData() {
    try {
      const response = await new Promise((resolve) => {
        chrome.runtime.sendMessage(
          { action: 'getTabData' },
          resolve
        );
      });
      
      if (response.error) {
        return { error: response.error, needsRefresh: response.needsRefresh };
      }
      
      this.appState.productData = response.data;
      this.appState.isDataValid = response.isValid;
      
      return {
        data: response.data,
        isValid: response.isValid,
        warnings: response.warnings,
        siteName: response.siteName
      };
    } catch (error) {
      console.error('Error loading product data:', error);
      return { error: 'Ошибка при загрузке данных продукта' };
    }
  }

  /**
   * Проверка статуса продукта на бэкенде
   */
  async checkProductStatus(data) {
    try {
      const response = await new Promise((resolve) => {
        chrome.runtime.sendMessage(
          { action: 'checkProductStatus', data: data },
          resolve
        );
      });
      
      this.appState.productStatus = response.status;
      return response;
    } catch (error) {
      console.error('Error checking product status:', error);
      return { status: 'error', message: 'Не удалось проверить статус' };
    }
  }

  /**
   * Отправка данных на бэкенд
   */
  async submitData(dataToSend) {
    try {
      const response = await new Promise((resolve) => {
        chrome.runtime.sendMessage(
          { action: 'sendToBackend', data: dataToSend },
          resolve
        );
      });
      
      return response;
    } catch (error) {
      console.error('Error submitting data:', error);
      return { error: 'Ошибка отправки данных' };
    }
  }

  /**
   * Запуск наблюдателя за цветом
   */
  async startColorObserver() {
    try {
      const response = await new Promise((resolve) => {
        chrome.runtime.sendMessage(
          { action: 'startColorObserver' },
          resolve
        );
      });
      
      return response;
    } catch (error) {
      console.error('Error starting color observer:', error);
      return { error: 'Не удалось запустить наблюдатель за цветом' };
    }
  }

  /**
   * Остановка наблюдателя за цветом
   */
  async stopColorObserver() {
    try {
      const response = await new Promise((resolve) => {
        chrome.runtime.sendMessage(
          { action: 'stopColorObserver' },
          resolve
        );
      });
      
      return response;
    } catch (error) {
      console.error('Error stopping color observer:', error);
      return { error: 'Не удалось остановить наблюдатель за цветом' };
    }
  }

  /**
   * Форматирование доступности для отображения
   */
  formatAvailability(value) {
    // Constants defined in BaseParser - using string literals to avoid circular dependency
    const availabilityMap = {
      'InStock': '✅ В наличии',
      'OutOfStock': '❌ Нет в наличии',
      'SoldOut': '❌ Распродано',
      'PreOrder': '⏰ Предзаказ',
      'PreSale': '⏰ Предпродажа',
      'BackOrder': '📦 Под заказ',
      'MadeToOrder': '🔨 Изготовление на заказ',
      'Discontinued': '🚫 Снят с производства',
      'InStoreOnly': '🏪 Только в магазине',
      'OnlineOnly': '💻 Только онлайн',
      'LimitedAvailability': '⚠️ Ограниченная доступность',
      'Reserved': '🔒 Зарезервировано'
    };
    
    return availabilityMap[value] || `❓ ${value}`;
  }

  /**
   * Получение выбранных изображений
   */
  getSelectedImages() {
    const checkboxes = document.querySelectorAll('.image-checkbox:checked');
    const selectedImages = [];
    
    checkboxes.forEach(checkbox => {
      const index = parseInt(checkbox.dataset.index);
      if (this.appState.productData && this.appState.productData.all_image_urls && this.appState.productData.all_image_urls[index]) {
        selectedImages.push(this.appState.productData.all_image_urls[index]);
      }
    });
    
    return selectedImages;
  }

  /**
   * Проверка возможности отправки данных
   */
  canSubmitData() {
    return this.appState.backendStatus === 'available' && 
           this.appState.productData && 
           this.appState.isDataValid;
  }

  /**
   * Получение текста кнопки отправки
   */
  getSubmitButtonText() {
    if (this.appState.backendStatus !== 'available') {
      return 'Бэкенд недоступен';
    } else if (!this.appState.productData) {
      return 'Нет данных';
    } else if (!this.appState.isDataValid) {
      return 'Данные некорректны';
    } else if (this.appState.productStatus === 'existing') {
      return 'Повторно отправить';
    } else {
      return 'Отправить данные';
    }
  }

  /**
   * Настройка обработчиков для селекции изображений
   */
  setupImageSelection() {
    const checkboxes = document.querySelectorAll('.image-checkbox');
    const selectAllBtn = document.getElementById('selectAllBtn');
    const deselectAllBtn = document.getElementById('deselectAllBtn');
    const imageSelectors = document.querySelectorAll('.image-selector');
    
    if (checkboxes.length === 0) {
      return;
    }
    
    // Обработчики для чекбоксов
    checkboxes.forEach(checkbox => {
      checkbox.addEventListener('change', () => this.handleImageSelectionChange());
    });
    
    // Обработчики для кликов по изображениям
    imageSelectors.forEach(selector => {
      selector.addEventListener('click', (e) => {
        if (e.target.type !== 'checkbox') {
          const checkbox = selector.querySelector('.image-checkbox');
          checkbox.checked = !checkbox.checked;
          this.handleImageSelectionChange();
        }
      });
    });
    
    // Обработчики для кнопок
    if (selectAllBtn) {
      selectAllBtn.addEventListener('click', () => this.selectAllImages());
    }
    
    if (deselectAllBtn) {
      deselectAllBtn.addEventListener('click', () => this.deselectAllImages());
    }
    
    // Обновляем начальное состояние
    this.updateImageSelectionUI();
  }

  /**
   * Обработка изменения выбора изображения
   */
  handleImageSelectionChange() {
    this.updateImageSelectionUI();
  }

  /**
   * Обновление интерфейса селекции изображений
   */
  updateImageSelectionUI() {
    const checkboxes = document.querySelectorAll('.image-checkbox');
    const selectedCountSpan = document.getElementById('selectedCount');
    const imageSelectors = document.querySelectorAll('.image-selector');
    
    let selectedCount = 0;
    
    checkboxes.forEach((checkbox, index) => {
      const selector = imageSelectors[index];
      if (checkbox.checked) {
        selectedCount++;
        selector?.classList.add('selected');
      } else {
        selector?.classList.remove('selected');
      }
    });
    
    if (selectedCountSpan) {
      selectedCountSpan.textContent = selectedCount;
    }
  }

  /**
   * Выбрать все изображения
   */
  selectAllImages() {
    const checkboxes = document.querySelectorAll('.image-checkbox');
    checkboxes.forEach(checkbox => {
      checkbox.checked = true;
    });
    this.updateImageSelectionUI();
  }

  /**
   * Снять выбор со всех изображений
   */
  deselectAllImages() {
    const checkboxes = document.querySelectorAll('.image-checkbox');
    checkboxes.forEach(checkbox => {
      checkbox.checked = false;
    });
    this.updateImageSelectionUI();
  }

  /**
   * Обновление статуса продукта в UI
   */
  updateProductStatusUI(statusResponse) {
    const statusCard = document.getElementById('productStatus');
    if (!statusCard) return;
    
    // Удаляем старые классы
    statusCard.classList.remove('new', 'existing', 'unavailable', 'warning');
    
    if (!statusResponse) {
      statusCard.innerHTML = '<div class="status-text">Проверяется...</div>';
      statusCard.classList.add('warning');
      return;
    }
    
    const { statusText, statusClass } = this.formatStatusResponse(statusResponse);
    statusCard.innerHTML = `<div class="status-text">${statusText}</div>`;
    statusCard.classList.add(statusClass);
    
    // Специальная обработка для случая изменения продукта
    if (statusResponse && statusResponse.status === 'changed') {
      const refreshBtn = document.getElementById('refreshBtn');
      const submitBtn = document.getElementById('submitBtn');
      
      if (refreshBtn) refreshBtn.style.display = 'block';
      if (submitBtn) submitBtn.style.display = 'none';
    }
  }

  /**
   * Форматирование ответа статуса для отображения
   */
  formatStatusResponse(statusResponse) {
    let statusText = '';
    let statusClass = '';
    
    switch (statusResponse.status) {
      case 'new':
        statusText = statusResponse.message || '🆕 Новый продукт';
        statusClass = 'new';
        break;
      case 'existing':
        statusClass = 'existing';
        
        if (statusResponse.productUrl) {
          statusText = `<a href="${statusResponse.productUrl}" target="_blank" style="color: #4ade80; text-decoration: underline;">${statusResponse.message || '✅ Продукт уже существует'}</a>`;
        } else {
          statusText = statusResponse.message || '✅ Уже существует';
        }
        break;
      case 'unavailable':
        statusText = statusResponse.message || '❌ Бэкенд недоступен';
        statusClass = 'unavailable';
        break;
      case 'error':
        statusText = statusResponse.message || '⚠️ Не удалось проверить';
        statusClass = 'warning';
        break;
      case 'changed':
        statusText = statusResponse.message || '🔄 Нужно обновить страницу';
        statusClass = 'warning';
        break;
      default:
        statusText = statusResponse.message || '❓ Неизвестно';
        statusClass = 'warning';
    }
    
    return { statusText, statusClass };
  }

  /**
   * Обработка обновления цвета и изображений в реальном времени
   */
  handleColorUpdate(update) {
    console.log('Received color/image update:', update);
    
    // Поддерживаем обратную совместимость: строка = только цвет (Carter's)
    let color, images;
    if (typeof update === 'string') {
      color = update;
    } else if (typeof update === 'object' && update !== null) {
      color = update.color;
      images = update.images;
    } else {
      console.warn('Invalid update format:', update);
      return;
    }
    
    // Обновляем данные в состоянии приложения
    if (this.appState.productData) {
      this.appState.productData.color = color;
      
      // Обновляем изображения если они предоставлены (Tommy Hilfiger)
      if (images && Array.isArray(images) && images.length > 0) {
        this.appState.productData.all_image_urls = images;
        console.log(`Updated ${images.length} images in product data`);
      }
    }
    
    // Находим элемент цвета в превью и обновляем его
    const colorValueElement = document.querySelector('[data-field="color"] .data-value');
    if (colorValueElement) {
      colorValueElement.textContent = color;
      colorValueElement.classList.remove('missing');
      console.log('Updated color in preview:', color);
    }
    
    // Если обновились изображения, обновляем превью изображений
    if (images && Array.isArray(images) && images.length > 0) {
      this.updateImagePreview(images);
    }
  }

  /**
   * Обновление превью изображений (для Tommy Hilfiger)
   */
  updateImagePreview(images) {
    try {
      console.log('Updating image preview with', images.length, 'images');
      
      // Находим контейнер с изображениями
      const imageContainer = document.querySelector('.image-selection');
      if (!imageContainer) {
        console.log('Image container not found, skipping image preview update');
        return;
      }
      
      // Очищаем старые изображения
      const oldImageSelectors = imageContainer.querySelectorAll('.image-selector');
      oldImageSelectors.forEach(selector => selector.remove());
      
      // Создаем новые элементы изображений
      images.forEach((imageUrl, index) => {
        const imageSelector = document.createElement('div');
        imageSelector.className = 'image-selector';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'image-checkbox';
        checkbox.dataset.index = index;
        checkbox.checked = true; // По умолчанию выбираем все новые изображения
        
        const img = document.createElement('img');
        img.src = imageUrl;
        img.alt = `Product image ${index + 1}`;
        img.style.maxWidth = '100px';
        img.style.maxHeight = '100px';
        img.style.objectFit = 'cover';
        
        imageSelector.appendChild(checkbox);
        imageSelector.appendChild(img);
        imageContainer.appendChild(imageSelector);
      });
      
      // Повторно настраиваем обработчики выбора изображений
      this.setupImageSelection();
      
      console.log('Image preview updated successfully');
      
    } catch (error) {
      console.error('Error updating image preview:', error);
    }
  }

  /**
   * Обработка уведомления о смене продукта
   */
  handleProductChangedNotification(reason) {
    console.log('Product changed notification received:', reason);
    
    // Показываем статус в блоке статуса
    this.updateProductStatusUI({ 
      status: 'changed', 
      message: 'Нужно обновить страницу' 
    });
    
    // Показываем кнопку обновления, скрываем кнопку отправки
    const refreshBtn = document.getElementById('refreshBtn');
    const submitBtn = document.getElementById('submitBtn');
    
    if (refreshBtn) refreshBtn.style.display = 'block';
    if (submitBtn) submitBtn.style.display = 'none';
    
    // Скрываем превью данных
    const previewContainer = document.getElementById('dataPreview');
    if (previewContainer) previewContainer.style.display = 'none';
    
    // Скрываем поле комментария
    const commentContainer = document.querySelector('.comment-container');
    if (commentContainer) commentContainer.style.display = 'none';
  }

  /**
   * Обновление состояния кнопок
   */
  updateButtonsState() {
    const submitBtn = document.getElementById('submitBtn');
    const refreshBtn = document.getElementById('refreshBtn');
    
    if (!submitBtn) return;
    
    // Если показывается кнопка обновления, не трогаем состояние
    if (refreshBtn && refreshBtn.style.display !== 'none') {
      return;
    }
    
    // Показываем кнопку отправки, скрываем кнопку обновления
    submitBtn.style.display = 'block';
    if (refreshBtn) refreshBtn.style.display = 'none';
    
    const canSubmit = this.canSubmitData();
    submitBtn.disabled = !canSubmit;
    submitBtn.textContent = this.getSubmitButtonText();
  }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
  window.VIParserCore = VIParserCore;
}