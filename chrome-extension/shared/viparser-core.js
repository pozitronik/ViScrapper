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
}

// Export for use in other modules
if (typeof window !== 'undefined') {
  window.VIParserCore = VIParserCore;
}