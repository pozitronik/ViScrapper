/**
 * Базовый класс для парсеров сайтов
 * Определяет общий интерфейс и базовую функциональность
 */
class BaseParser {
  constructor(config) {
    this.config = config;
    this.siteName = config.siteName;
    this.domain = config.domain;
    this.selectors = config.selectors || {};
  }

  // Абстрактные методы - должны быть переопределены в наследниках
  isValidProductPage() { 
    throw new Error('Must implement isValidProductPage'); 
  }
  
  extractName() { 
    throw new Error('Must implement extractName'); 
  }
  
  extractSku(jsonData) { 
    throw new Error('Must implement extractSku'); 
  }
  
  extractPrice(jsonData) { 
    throw new Error('Must implement extractPrice'); 
  }
  
  extractImages() { 
    throw new Error('Must implement extractImages'); 
  }
  
  async extractSizes() { 
    throw new Error('Must implement extractSizes'); 
  }

  // Общие методы с базовой реализацией
  
  /**
   * Сантизация URL продукта - удаляет параметры, которые не влияют на идентификацию
   */
  sanitizeUrl(url) {
    try {
      const urlObj = new URL(url);
      const cleanUrl = `${urlObj.protocol}//${urlObj.host}${urlObj.pathname}`;
      console.log(`URL sanitized: ${url} -> ${cleanUrl}`);
      return cleanUrl;
    } catch (error) {
      console.error('Error sanitizing URL:', error);
      return url;
    }
  }

  /**
   * Функция ожидания
   */
  wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Валидация данных продукта
   */
  validateProductData(data) {
    const warnings = [];
    const requiredFields = ['sku'];
    
    let isValid = true;
    
    // Проверяем обязательные поля
    requiredFields.forEach(field => {
      if (!data[field]) {
        warnings.push(`Отсутствует обязательное поле: ${field}`);
        isValid = false;
      }
    });
    
    // Проверяем, что SKU не пустой
    if (data.sku && data.sku.trim() === '') {
      warnings.push('SKU не может быть пустым');
      isValid = false;
    }
    
    // Предупреждения для важных полей (не влияют на isValid)
    if (!data.name) {
      warnings.push('Название продукта не найдено');
    }
    
    if (!data.price) {
      warnings.push('Цена продукта не найдена');
    }
    
    if (!data.currency) {
      warnings.push('Валюта не найдена');
    }
    
    if (!data.all_image_urls || data.all_image_urls.length === 0) {
      warnings.push('Изображения не найдены');
    }
    
    if (!data.available_sizes && !data.size_combinations) {
      warnings.push('Размеры не извлечены');
    }
    
    return {
      isValid: isValid,
      warnings
    };
  }

  // Опциональные методы с базовой реализацией
  
  /**
   * Извлечение валюты (базовая реализация)
   */
  extractCurrency(jsonData) {
    if (jsonData && jsonData.offers && jsonData.offers.priceCurrency) {
      return jsonData.offers.priceCurrency;
    }
    return 'USD'; // По умолчанию
  }

  /**
   * Извлечение доступности (базовая реализация)
   */
  extractAvailability(jsonData) {
    if (jsonData && jsonData.offers && jsonData.offers.availability) {
      const availabilityUrl = jsonData.offers.availability;
      
      if (availabilityUrl.includes('schema.org/')) {
        const type = availabilityUrl.split('schema.org/').pop();
        console.log(`Extracted availability type: ${type} from ${availabilityUrl}`);
        return type;
      }
      
      return availabilityUrl;
    }
    
    return 'InStock';
  }

  /**
   * Извлечение цвета (базовая реализация - может быть переопределена)
   */
  extractColor() {
    return null;
  }

  /**
   * Извлечение состава (базовая реализация - может быть переопределена)
   */
  extractComposition() {
    return null;
  }

  /**
   * Извлечение артикула (базовая реализация - может быть переопределена)
   */
  extractItem() {
    return null;
  }

  /**
   * Ожидание JSON-LD (базовая реализация - может быть переопределена)
   */
  async waitForJsonLd(timeout = 10000) {
    return null; // Не все сайты используют JSON-LD
  }

  /**
   * Парсинг JSON-LD (базовая реализация - может быть переопределена)
   */
  parseJsonLd(jsonLdText) {
    try {
      return JSON.parse(jsonLdText);
    } catch (error) {
      console.error('Error parsing JSON-LD:', error);
      return null;
    }
  }
}

// Экспортируем для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
  module.exports = BaseParser;
}