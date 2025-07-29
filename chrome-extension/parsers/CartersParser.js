/**
 * Парсер для Carter's
 * Содержит всю логику извлечения данных, специфичную для Carter's
 */
class CartersParser extends BaseParser {
  constructor() {
    super({
      siteName: "Carter's",
      domain: 'carters.com',
      selectors: {
        // JSON-LD script tag
        jsonLdScript: 'script[type="application/ld+json"]',
        
        // Product info selectors (fallback if JSON-LD fails)
        productTitle: 'h1, [data-testid*="title"], .product-title',
        productPrice: '[data-testid*="price"], .price, .product-price',
        
        // Size selectors (may need refinement)
        sizeContainer: '[data-testid*="size"], [aria-label*="size"], .size-selector, .size-options',
        sizeButtons: 'button[aria-label*="size"], button[data-value], [role="radio"]',
        
        // Image selectors - only inside image gallery
        imageGallery: '[data-testid="image-gallery"]',
        productImages: 'img', // Will be used within imageGallery context
        imageContainer: '.product-images, [data-testid*="image"]',
        
        // Additional info
        productDescription: '[data-testid*="description"], .product-description',
        availability: '[data-testid*="stock"], .availability',
        
        // Color/Style info
        productStyle: '[data-testid="pdp-product-style"]',
        
        // Composition info (in accordion)
        fabricCareButton: '[data-testid="fabric-care-btn"]',
        fabricCarePanel: '[aria-labelledby*="fabric-care"]',
        compositionList: 'ul li:first-child'
      }
    });
  }

  /**
   * Проверка, что мы на странице товара Carter's
   */
  isValidProductPage() {
    const url = window.location.href;
    console.log('Checking Carter\'s page validity, URL:', url);
    
    if (!url.includes(this.config.domain)) {
      console.log('Not a Carter\'s page');
      return false;
    }
    
    // Проверяем наличие JSON-LD или основных элементов продукта
    const hasJsonLd = document.querySelector(this.config.selectors.jsonLdScript);
    const hasProductTitle = document.querySelector(this.config.selectors.productTitle);
    
    console.log('JSON-LD found:', !!hasJsonLd);
    console.log('Product title found:', !!hasProductTitle);
    
    // Carter's URL pattern: ends with /V_XXXXXX format
    const urlPattern = /\/V_[A-Z0-9]+$/i;
    const hasValidUrlPattern = urlPattern.test(url);
    
    console.log('Valid URL pattern:', hasValidUrlPattern);
    
    const isValid = (hasJsonLd || hasProductTitle) && hasValidUrlPattern;
    console.log('Page is valid Carter\'s product page:', isValid);
    
    return isValid;
  }

  /**
   * Извлечение названия продукта
   */
  extractName() {
    // Приоритет 1: Из DOM элементов (всегда актуальны)
    const titleElement = document.querySelector(this.config.selectors.productTitle);
    if (titleElement) {
      const name = titleElement.textContent?.trim();
      console.log('Carter\'s name from DOM:', name);
      return name;
    }
    
    // Приоритет 2: Из JSON-LD (может устареть при SPA навигации)
    const jsonData = this.getJsonLdData();
    if (jsonData && jsonData.name) {
      console.log('Carter\'s name from JSON-LD:', jsonData.name);
      return jsonData.name;
    }
    
    console.log('Carter\'s name not found');
    return null;
  }

  /**
   * Извлечение SKU
   */
  extractSku(jsonData = null) {
    console.log('Carter\'s extractSku called');
    
    // Приоритет 1: Из URL (всегда актуален при переключении стилей)
    const url = window.location.href;
    const urlMatch = url.match(/\/V_([A-Z0-9]+)$/i);
    if (urlMatch) {
      const skuFromUrl = urlMatch[0].substring(1); // Remove leading slash
      console.log('Carter\'s SKU from URL:', skuFromUrl);
      return skuFromUrl;
    }
    
    // Приоритет 2: Из JSON-LD (может устареть при динамических изменениях)
    if (!jsonData) {
      jsonData = this.getJsonLdData();
    }
    
    if (jsonData && jsonData.sku) {
      console.log('Carter\'s SKU from JSON-LD:', jsonData.sku);
      return jsonData.sku;
    }
    
    if (jsonData && jsonData.mpn) {
      console.log('Carter\'s SKU from JSON-LD mpn:', jsonData.mpn);
      return jsonData.mpn;
    }
    
    console.log('Carter\'s SKU not found');
    return null;
  }

  /**
   * Извлечение цены
   */
  extractPrice(jsonData = null) {
    console.log('Carter\'s extractPrice called');
    
    // Приоритет 1: Из DOM элементов (всегда актуальны)
    const priceElement = document.querySelector(this.config.selectors.productPrice);
    if (priceElement) {
      const priceText = priceElement.textContent.trim();
      const priceMatch = priceText.match(/[\d,]+\.?\d*/);
      if (priceMatch) {
        const price = parseFloat(priceMatch[0].replace(',', ''));
        console.log('Carter\'s price from DOM:', price);
        return price;
      }
    }
    
    // Приоритет 2: Из JSON-LD (может устареть при SPA навигации)
    if (!jsonData) {
      jsonData = this.getJsonLdData();
    }
    
    if (jsonData && jsonData.offers) {
      const price = parseFloat(jsonData.offers.price);
      if (!isNaN(price)) {
        console.log('Carter\'s price from JSON-LD:', price);
        return price;
      }
    }
    
    console.log('Carter\'s price not found');
    return null;
  }

  /**
   * Извлечение валюты
   */
  extractCurrency(jsonData = null) {
    // Carter's всегда использует USD
    return 'USD';
  }

  /**
   * Извлечение доступности
   */
  extractAvailability(jsonData = null) {
    // Приоритет 1: Из DOM элементов (всегда актуальны)
    const availabilityElement = document.querySelector(this.config.selectors.availability);
    if (availabilityElement) {
      const availabilityText = availabilityElement.textContent.trim().toLowerCase();
      if (availabilityText.includes('in stock') || availabilityText.includes('available')) {
        return 'InStock';
      } else if (availabilityText.includes('out of stock') || availabilityText.includes('unavailable')) {
        return 'OutOfStock';
      }
    }
    
    // Приоритет 2: Из JSON-LD (может устареть при SPA навигации)
    if (!jsonData) {
      jsonData = this.getJsonLdData();
    }
    
    if (jsonData && jsonData.offers && jsonData.offers.availability) {
      const availability = jsonData.offers.availability;
      if (availability.includes('schema.org/')) {
        return availability.split('schema.org/').pop();
      }
      return availability;
    }
    
    // Default to InStock for Carter's
    return 'InStock';
  }

  /**
   * Извлечение изображений
   */
  extractImages() {
    console.log('Carter\'s extractImages called');
    
    // Приоритет 1: Из DOM элементов внутри image gallery (всегда актуальны)
    const imageGallery = document.querySelector(this.config.selectors.imageGallery);
    const imageUrls = [];
    
    if (imageGallery) {
      console.log('Found Carter\'s image gallery:', imageGallery);
      
      // Ищем все изображения только внутри галереи
      const imageElements = imageGallery.querySelectorAll(this.config.selectors.productImages);
      console.log(`Found ${imageElements.length} images in gallery`);
      
      imageElements.forEach(img => {
        if (img.src && img.src.startsWith('http')) {
          const enhancedUrl = this.enhanceImageQuality(img.src);
          if (!imageUrls.includes(enhancedUrl)) {
            imageUrls.push(enhancedUrl);
            console.log('Added image:', enhancedUrl);
          }
        }
      });
    } else {
      console.log('Carter\'s image gallery not found');
    }
    
    if (imageUrls.length > 0) {
      console.log('Carter\'s images from DOM gallery:', imageUrls);
      return imageUrls;
    }
    
    // Приоритет 2: Из JSON-LD (может устареть при SPA навигации)
    const jsonData = this.getJsonLdData();
    if (jsonData && jsonData.image && Array.isArray(jsonData.image)) {
      const images = jsonData.image.map(img => {
        const imageUrl = typeof img === 'string' ? img : img.url || img;
        return this.enhanceImageQuality(imageUrl);
      }).filter(url => url && url.startsWith('http'));
      
      if (images.length > 0) {
        console.log('Carter\'s images from JSON-LD fallback:', images);
        return images;
      }
    }
    
    console.log('Carter\'s images not found in gallery or JSON-LD');
    return [];
  }

  /**
   * Извлечение размеров
   */
  async extractSizes() {
    try {
      console.log('Starting Carter\'s size extraction...');
      
      // Поиск контейнера с размерами
      const sizeContainer = document.querySelector(this.config.selectors.sizeContainer);
      
      if (!sizeContainer) {
        console.log('No size container found on Carter\'s page');
        return [];
      }
      
      console.log('Found size container:', sizeContainer);
      
      // Поиск кнопок размеров
      const sizeButtons = sizeContainer.querySelectorAll(this.config.selectors.sizeButtons);
      
      if (sizeButtons.length === 0) {
        console.log('No size buttons found in Carter\'s size container');
        return [];
      }
      
      console.log(`Found ${sizeButtons.length} size buttons`);
      
      // Извлечение размеров из кнопок
      const sizes = [];
      sizeButtons.forEach(button => {
        // Проверяем, что кнопка не отключена
        if (button.disabled || button.getAttribute('aria-disabled') === 'true') {
          return;
        }
        
        // Пытаемся получить размер из разных атрибутов
        let size = button.getAttribute('data-value') || 
                  button.getAttribute('aria-label') || 
                  button.textContent?.trim();
        
        if (size && !sizes.includes(size)) {
          sizes.push(size);
        }
      });
      
      console.log('Carter\'s sizes extracted:', sizes);
      return sizes;
      
    } catch (error) {
      console.error('Error in Carter\'s extractSizes:', error);
      return [];
    }
  }

  /**
   * Получение JSON-LD данных
   */
  getJsonLdData() {
    try {
      const jsonLdScripts = document.querySelectorAll(this.config.selectors.jsonLdScript);
      
      for (const script of jsonLdScripts) {
        const jsonText = script.textContent?.trim();
        if (!jsonText) continue;
        
        try {
          const jsonData = JSON.parse(jsonText);
          
          // Проверяем, что это данные о продукте
          if (jsonData['@type'] === 'Product' || 
              (jsonData.name && jsonData.sku) ||
              (jsonData.name && jsonData.mpn)) {
            console.log('Found Carter\'s product JSON-LD data:', jsonData);
            return jsonData;
          }
        } catch (parseError) {
          console.log('Failed to parse JSON-LD script:', parseError);
          continue;
        }
      }
      
      console.log('No valid product JSON-LD found for Carter\'s');
      return null;
      
    } catch (error) {
      console.error('Error getting Carter\'s JSON-LD data:', error);
      return null;
    }
  }

  /**
   * Ожидание JSON-LD (переопределение базового метода)
   */
  async waitForJsonLd(timeout = 10000) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const jsonLdData = this.getJsonLdData();
      if (jsonLdData) {
        return jsonLdData;
      }
      
      await this.wait(100);
    }
    
    return null;
  }

  /**
   * Извлечение описания продукта
   */
  extractDescription() {
    // Приоритет 1: Из DOM элементов (всегда актуальны)
    const descriptionElement = document.querySelector(this.config.selectors.productDescription);
    if (descriptionElement) {
      return descriptionElement.textContent?.trim();
    }
    
    // Приоритет 2: Из JSON-LD (может устареть при SPA навигации)
    const jsonData = this.getJsonLdData();
    if (jsonData && jsonData.description) {
      return jsonData.description;
    }
    
    return null;
  }

  /**
   * Извлечение цвета/стиля (переопределение базового метода) с увеличенным ожиданием
   */
  async extractColor() {
    console.log('Carter\'s extractColor called');
    
    // Используем более продвинутое ожидание с увеличенным временем
    return await this.waitForColorElement();
  }

  /**
   * Ожидание появления элемента с цветом
   */
  async waitForColorElement(timeout = 10000) {
    console.log('Waiting for Carter\'s color element to appear...');
    
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      try {
        // Ищем элемент с data-testid="pdp-product-style"
        const styleElement = document.querySelector(this.config.selectors.productStyle);
        
        if (styleElement) {
          // Ищем родительский контейнер с aria-label="Style: ..."
          const parentContainer = styleElement.closest('[aria-label*="Style:"]');
          
          if (parentContainer) {
            const ariaLabel = parentContainer.getAttribute('aria-label');
            // Извлекаем все после "Style: "
            const styleMatch = ariaLabel.match(/Style:\s*(.+)/i);
            if (styleMatch && styleMatch[1]) {
              const style = styleMatch[1].trim();
              console.log('Carter\'s color/style from aria-label:', style);
              return style;
            }
          }
          
          // Альтернативный способ: ищем следующий элемент p после "Style:"
          const styleContainer = styleElement.parentElement;
          if (styleContainer) {
            const pElement = styleContainer.querySelector('p');
            if (pElement && pElement.textContent?.trim()) {
              const style = pElement.textContent.trim();
              console.log('Carter\'s color/style from p element:', style);
              return style;
            }
          }
        }
        
        // Ждем 200мс перед следующей попыткой
        await new Promise(resolve => setTimeout(resolve, 200));
        
      } catch (error) {
        console.error('Error while waiting for Carter\'s color element:', error);
        await new Promise(resolve => setTimeout(resolve, 200));
      }
    }
    
    console.log('Carter\'s color element not found within timeout');
    return null;
  }

  /**
   * Настройка наблюдателя для цвета (для обновления popup в реальном времени)
   */
  setupColorObserver(callback) {
    console.log('Setting up Carter\'s color observer...');
    
    // Создаем MutationObserver для отслеживания изменений
    const observer = new MutationObserver(async (mutations) => {
      let shouldCheck = false;
      
      for (const mutation of mutations) {
        // Проверяем, добавились ли новые элементы с нужными селекторами
        if (mutation.type === 'childList') {
          const addedNodes = Array.from(mutation.addedNodes);
          const hasRelevantElements = addedNodes.some(node => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              return node.matches && (
                node.matches('[data-testid="pdp-product-style"]') ||
                node.querySelector && node.querySelector('[data-testid="pdp-product-style"]') ||
                node.matches('[aria-label*="Style:"]') ||
                node.querySelector && node.querySelector('[aria-label*="Style:"]')
              );
            }
            return false;
          });
          
          if (hasRelevantElements) {
            shouldCheck = true;
            break;
          }
        }
        
        // Также проверяем изменения атрибутов
        if (mutation.type === 'attributes' && 
            (mutation.attributeName === 'aria-label' || mutation.attributeName === 'data-testid')) {
          shouldCheck = true;
          break;
        }
      }
      
      if (shouldCheck) {
        console.log('Color-relevant DOM changes detected, checking for color...');
        const color = await this.waitForColorElement(2000); // Короткий таймаут для повторной проверки
        if (color && callback) {
          console.log('Color found after DOM change, notifying callback:', color);
          callback(color);
        }
      }
    });
    
    // Наблюдаем за изменениями в document.body
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['aria-label', 'data-testid']
    });
    
    console.log('Carter\'s color observer set up');
    return observer;
  }

  /**
   * Извлечение состава (переопределение базового метода)
   */
  async extractComposition() {
    console.log('Carter\'s extractComposition called');
    
    try {
      // Ищем кнопку "Fabric & Care"
      const fabricCareButton = document.querySelector(this.config.selectors.fabricCareButton);
      
      if (!fabricCareButton) {
        console.log('Fabric & Care button not found');
        return null;
      }
      
      // Проверяем, раскрыт ли аккордеон
      const isExpanded = fabricCareButton.getAttribute('aria-expanded') === 'true';
      
      if (!isExpanded) {
        console.log('Fabric & Care accordion is collapsed, trying to expand...');
        // Пытаемся раскрыть аккордеон
        fabricCareButton.click();
        
        // Даем время на раскрытие
        await new Promise(resolve => setTimeout(resolve, 300));
      } else {
        console.log('Fabric & Care accordion is already expanded');
      }
      
      return this.extractCompositionFromPanel();
      
    } catch (error) {
      console.error('Error extracting Carter\'s composition:', error);
      return null;
    }
  }

  /**
   * Извлечение состава из раскрытой панели
   */
  extractCompositionFromPanel() {
    try {
      // Ищем все видимые панели аккордеона
      const allPanels = document.querySelectorAll('[id*="accordion-panel"]:not([style*="display: none"])');
      
      if (allPanels.length === 0) {
        console.log('No visible accordion panels found');
        return null;
      }
      
      // Ищем панель с Fabric & Care (по кнопке-триггеру)
      const fabricCareButton = document.querySelector(this.config.selectors.fabricCareButton);
      let fabricCarePanel = null;
      
      if (fabricCareButton) {
        const panelId = fabricCareButton.getAttribute('aria-controls');
        if (panelId) {
          fabricCarePanel = document.getElementById(panelId);
        }
      }
      
      // Если не нашли по aria-controls, пробуем другие способы
      if (!fabricCarePanel) {
        // Ищем панель, содержащую состав (с процентами)
        for (const panel of allPanels) {
          const compositionItems = panel.querySelectorAll('ul li');
          for (const item of compositionItems) {
            const text = item.textContent?.trim();
            if (text && text.match(/\d+%/)) {
              fabricCarePanel = panel;
              console.log('Found Fabric & Care panel by composition match');
              break;
            }
          }
          if (fabricCarePanel) break;
        }
      }
      
      if (!fabricCarePanel) {
        console.log('Fabric & Care panel not found');
        return null;
      }
      
      // Ищем первый элемент с составом (с процентами)
      const compositionItems = fabricCarePanel.querySelectorAll('ul li');
      for (const item of compositionItems) {
        const text = item.textContent?.trim();
        // Ищем строку с процентами (например, "60% cotton, 40% polyester")
        if (text && text.match(/\d+%/)) {
          console.log('Carter\'s composition found:', text);
          return text;
        }
      }
      
      // Если не нашли с процентами, берем первый элемент списка
      const firstListItem = fabricCarePanel.querySelector('ul li:first-child');
      if (firstListItem) {
        const composition = firstListItem.textContent?.trim();
        console.log('Carter\'s composition from first li:', composition);
        return composition;
      }
      
      console.log('Carter\'s composition not found in panel');
      return null;
      
    } catch (error) {
      console.error('Error extracting composition from panel:', error);
      return null;
    }
  }

  /**
   * Извлечение артикула (переопределение базового метода - используем SKU как fallback)
   */
  extractItem() {
    console.log('Carter\'s extractItem called');
    
    // Для Carter's используем SKU как артикул
    const sku = this.extractSku();
    if (sku) {
      console.log('Carter\'s item using SKU as fallback:', sku);
      return sku;
    }
    
    console.log('Carter\'s item not found');
    return null;
  }

  /**
   * Извлечение бренда
   */
  extractBrand() {
    // Carter's всегда имеет бренд Carter's
    return "Carter's";
  }

  /**
   * Парсинг JSON-LD с предупреждениями вместо ошибок (переопределение базового метода)
   */
  parseJsonLd(jsonLdText) {
    try {
      return JSON.parse(jsonLdText);
    } catch (error) {
      // Для Carter's используем предупреждение вместо ошибки, 
      // так как JSON-LD может устаревать при SPA навигации
      console.warn('Carter\'s JSON-LD parsing failed (expected with SPA navigation):', error.message);
      return null;
    }
  }
}

// Экспортируем для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CartersParser;
}