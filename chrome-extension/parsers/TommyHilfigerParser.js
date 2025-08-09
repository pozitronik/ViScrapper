/**
 * Парсер для Tommy Hilfiger
 * Содержит всю логику извлечения данных, специфичную для TH
 */
class TommyHilfigerParser extends BaseParser {
  constructor() {
    super({
      siteName: 'Tommy Hilfiger',
      domain: 'usa.tommy.com',
      selectors: {
        buyBox: '.buy-box[data-comp="BuyBox"]',
        productName: '.product-name, h1.product-name',
        priceValue: '.sales .value[content]',
        priceContainer: '.buy-box__prices.product-detail__prices',
        colorsList: '#colorscolorCode',
        sizesList: '#sizessize',
        jsonLdScript: 'script[type="application/ld+json"]'
      }
    });
  }

  /**
   * Проверка, что мы на странице товара Tommy Hilfiger
   */
  isValidProductPage() {
    const url = window.location.href;
    console.log('Checking TH page validity, URL:', url);
    
    if (!url.includes(this.config.domain)) {
      console.log('Not a Tommy Hilfiger page');
      return false;
    }
    
    // Проверяем наличие основных элементов продукта
    const productName = document.querySelector(this.config.selectors.productName);
    const buyBox = document.querySelector(this.config.selectors.buyBox);
    
    console.log('ProductName element:', productName);
    console.log('BuyBox element:', buyBox);
    
    // Проверяем URL паттерн для продукта (более надежно чем JSON-LD на начальной стадии)
    const hasProductUrl = /\/[A-Z0-9]+-[A-Z0-9]+\.html$/i.test(url);
    console.log('Has product URL pattern:', hasProductUrl);
    
    // Не требуем JSON-LD для первичной валидации, так как он может загружаться асинхронно
    const isValid = !!(productName && buyBox && hasProductUrl);
    console.log('Page is valid TH product page:', isValid);
    
    return isValid;
  }

  /**
   * Извлечение названия продукта
   */
  extractName() {
    const element = document.querySelector(this.config.selectors.productName);
    return element?.textContent?.trim() || null;
  }

  /**
   * Извлечение SKU из JSON-LD
   */
  extractSku(jsonData) {
    if (jsonData && jsonData.sku) {
      return jsonData.sku;
    }
    
    // Fallback: try to extract from URL pattern
    const urlMatch = window.location.pathname.match(/\/([A-Z0-9]+-[A-Z0-9]+)\.html$/i);
    if (urlMatch) {
      return urlMatch[1];
    }
    
    return null;
  }

  /**
   * Извлечение цены
   */
  extractPrice(jsonData) {
    // Приоритет 1: Проверяем актуальную цену в DOM (текущая продажная цена)
    const salesPriceElement = document.querySelector(this.config.selectors.priceValue);
    if (salesPriceElement) {
      const salesContent = salesPriceElement.getAttribute('content');
      if (salesContent) {
        return parseFloat(salesContent);
      }
    }
    
    // Приоритет 2: JSON-LD цена
    if (jsonData && jsonData.offers && jsonData.offers.price) {
      return parseFloat(jsonData.offers.price);
    }
    
    return null;
  }

  /**
   * Извлечение изображений из JSON-LD
   */
  async extractImages() {
    const jsonData = this.getJsonLdData();
    const imageUrls = [];
    
    // Tommy Hilfiger использует JSON-LD с массивом изображений
    if (jsonData && jsonData.image && Array.isArray(jsonData.image)) {
      jsonData.image.forEach((url) => {
        if (url && typeof url === 'string') {
          const enhancedUrl = this.enhanceImageQuality(url);
          imageUrls.push(enhancedUrl);
        }
      });
    }
    
    return imageUrls;
  }

  /**
   * Извлечение цвета из выбранного элемента
   */
  extractColor() {
    const colorsList = document.querySelector(this.config.selectors.colorsList);
    if (!colorsList) {
      return null;
    }
    
    // Ищем выбранный (checked) цвет
    const selectedColor = colorsList.querySelector('input[type="radio"]:checked');
    if (!selectedColor) {
      // Попробуем найти по aria-checked="true"
      const ariaCheckedColor = colorsList.querySelector('input[type="radio"][aria-checked="true"]');
      if (ariaCheckedColor) {
        return this.extractColorNameFromInput(ariaCheckedColor);
      }
      return null;
    }
    
    return this.extractColorNameFromInput(selectedColor);
  }

  /**
   * Извлечение названия цвета из input элемента
   */
  extractColorNameFromInput(input) {
    const inputId = input.getAttribute('id');
    
    // Находим соответствующий label
    const label = document.querySelector(`label[for="${inputId}"]`);
    if (label) {
      // Ищем span с aria-label (содержит название цвета)
      const colorSpan = label.querySelector('span[aria-label]');
      if (colorSpan) {
        return colorSpan.getAttribute('aria-label');
      }
      
      // Альтернативно ищем скрытый span с текстом
      const hiddenSpan = label.querySelector('span.d-none');
      if (hiddenSpan) {
        return hiddenSpan.textContent.trim();
      }
    }
    
    // Fallback на data-attr-value
    return input.getAttribute('data-attr-value');
  }

  /**
   * Извлечение размеров для текущего выбранного цвета
   */
  async extractSizes() {
    try {
      const sizesList = document.querySelector(this.config.selectors.sizesList);
      if (!sizesList) {
        return [];
      }
      
      // Tommy Hilfiger имеет простую структуру размеров
      const sizeInputs = sizesList.querySelectorAll('input[type="radio"]');
      const availableSizes = [];
      
      sizeInputs.forEach(input => {
        const inputId = input.getAttribute('id');
        const label = document.querySelector(`label[for="${inputId}"]`);
        const sizeLabel = label?.textContent?.trim();
        const dataValue = input.getAttribute('data-attr-value');
        
        const sizeValue = sizeLabel || dataValue;
        if (sizeValue) {
          availableSizes.push(sizeValue);
        }
      });
      
      return availableSizes;
      
    } catch (error) {
      console.error('Error in TH extractSizes:', error);
      return [];
    }
  }

  /**
   * Извлечение всех доступных цветов
   */
  extractAllColors() {
    const colors = [];
    const colorsList = document.querySelector(this.config.selectors.colorsList);
    
    if (!colorsList) {
      return colors;
    }
    
    const colorInputs = colorsList.querySelectorAll('input[type="radio"]');
    colorInputs.forEach(input => {
      const colorCode = input.getAttribute('data-attr-value');
      const colorName = this.extractColorNameFromInput(input);
      
      if (colorCode || colorName) {
        colors.push({
          code: colorCode,
          name: colorName || colorCode,
          isSelected: input.checked || input.getAttribute('aria-checked') === 'true'
        });
      }
    });
    
    return colors;
  }

  /**
   * Извлечение состава продукта из модального окна
   */
  extractComposition() {
    try {
      // Ищем модальное окно с деталями продукта
      const productModal = document.querySelector('[data-modal-id="productDetailsModal"]');
      if (!productModal) {
        return null;
      }
      
      // Ищем таблицу контента
      const contentTable = productModal.querySelector('.content-table');
      if (!contentTable) {
        return null;
      }
      
      // Ищем строку с составом
      const contentRows = contentTable.querySelectorAll('.content-row');
      for (const row of contentRows) {
        const columns = row.querySelectorAll('.content-column');
        if (columns.length >= 2) {
          const headerText = columns[0].textContent.trim().toLowerCase();
          if (headerText === 'composition') {
            return columns[1].textContent.trim();
          }
        }
      }
      
      return null;
    } catch (error) {
      console.error('Error extracting composition:', error);
      return null;
    }
  }

  /**
   * Ожидание появления JSON-LD скрипта
   */
  async waitForJsonLd(timeout = 10000) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const jsonLdScripts = document.querySelectorAll(this.config.selectors.jsonLdScript);
      
      for (let script of jsonLdScripts) {
        if (script.textContent.trim() && script.textContent.includes('@type')) {
          const jsonData = this.parseJsonLd(script.textContent);
          if (jsonData && jsonData['@type'] === 'Product') {
            return script;
          }
        }
      }
      
      await this.wait(100);
    }
    
    return null;
  }

  /**
   * Извлечение валюты
   */
  extractCurrency(jsonData) {
    // Приоритет 1: JSON-LD валюта
    if (jsonData && jsonData.offers && jsonData.offers.priceCurrency) {
      return jsonData.offers.priceCurrency;
    }
    
    // Приоритет 2: Поиск в DOM
    const currencyElement = document.querySelector('.currency, .price-currency, [data-currency]');
    if (currencyElement) {
      return currencyElement.textContent.trim() || currencyElement.getAttribute('data-currency');
    }
    
    // Fallback: USD для Tommy Hilfiger US
    return 'USD';
  }
  
  /**
   * Извлечение доступности товара
   */
  extractAvailability(jsonData) {
    // Проверяем явные признаки недоступности
    
    // 1. Проверка кнопки "Add to Cart" на отключенность
    const addToCartButton = document.querySelector('.buy-box__add-to-cart button, .add-to-cart-btn, [data-testid="add-to-cart"]');
    if (addToCartButton) {
      const isDisabled = addToCartButton.disabled || addToCartButton.classList.contains('disabled');
      const buttonText = addToCartButton.textContent.toLowerCase();
      
      if (isDisabled || buttonText.includes('out of stock') || buttonText.includes('sold out') || buttonText.includes('unavailable')) {
        return BaseParser.AVAILABILITY.OUT_OF_STOCK;
      }
    }
    
    // 2. Проверка явных сообщений о недоступности
    const outOfStockMessage = document.querySelector('.out-of-stock, .sold-out, .unavailable, [data-out-of-stock="true"]');
    if (outOfStockMessage) {
      return BaseParser.AVAILABILITY.OUT_OF_STOCK;
    }
    
    // 3. Проверка JSON-LD только для явной недоступности
    if (jsonData && jsonData.offers && jsonData.offers.availability) {
      const availability = jsonData.offers.availability.toLowerCase();
      if (availability.includes('outofstock') || availability.includes('soldout') || availability.includes('discontinued')) {
        return BaseParser.AVAILABILITY.OUT_OF_STOCK;
      }
    }
    
    // По умолчанию считаем товар доступным, если он есть на странице
    // Даже если есть предупреждения типа "Only 3 left in Stock"
    return BaseParser.AVAILABILITY.IN_STOCK;
  }

  /**
   * Получение JSON-LD данных продукта
   */
  getJsonLdData() {
    try {
      const jsonLdScripts = document.querySelectorAll(this.config.selectors.jsonLdScript);
      
      for (let script of jsonLdScripts) {
        if (script.textContent.trim() && script.textContent.includes('@type')) {
          const jsonData = this.parseJsonLd(script.textContent);
          if (jsonData && jsonData['@type'] === 'Product') {
            return jsonData;
          }
        }
      }
      return null;
    } catch (error) {
      console.error('TH getJsonLdData: Error getting JSON-LD data:', error);
      return null;
    }
  }

  /**
   * Извлечение всех вариантов (цвет + размеры) для создания отдельных продуктов
   */
  async extractAllVariants() {
    try {
      console.log('Starting TH variant extraction...');
      
      const baseJsonData = this.getJsonLdData();
      const baseSku = this.extractSku(baseJsonData);
      const baseName = this.extractName();
      const basePrice = this.extractPrice(baseJsonData);
      const baseCurrency = this.extractCurrency(baseJsonData);
      const baseAvailability = this.extractAvailability(baseJsonData);
      const baseImages = await this.extractImages();
      
      if (!baseSku) {
        console.error('TH extractAllVariants: No base SKU found, cannot create variants');
        return [];
      }
      
      const colors = this.extractAllColors();
      const variants = [];
      
      if (colors.length === 0) {
        console.log('TH extractAllVariants: No colors found, creating single variant with current state');
        const sizes = await this.extractSizes();
        const currentColor = this.extractColor();
        
        // Создаем варианты для каждого размера
        sizes.forEach(size => {
          const variantSku = `${baseSku}-${size}`;
          
          variants.push({
            sku: variantSku,
            name: baseName,
            price: basePrice,
            currency: baseCurrency,
            availability: baseAvailability,
            color: currentColor,
            size: size,
            all_image_urls: baseImages,
            product_url: this.sanitizeUrl(window.location.href)
          });
        });
      } else {
        // Для каждого цвета извлекаем размеры и создаем варианты
        for (const color of colors) {
          console.log(`TH extractAllVariants: Processing color: ${color.name} (${color.code})`);
          
          // Кликаем на цвет если он не выбран
          if (!color.isSelected) {
            const colorInput = document.querySelector(`${this.config.selectors.colorsList} input[data-attr-value="${color.code}"]`);
            if (colorInput) {
              colorInput.click();
              await this.wait(500); // Ждем обновления размеров и изображений
            }
          }
          
          const sizes = await this.extractSizes();
          const colorImages = await this.extractImages();
          
          // Создаем варианты для каждого размера этого цвета
          sizes.forEach(size => {
            // Создаем SKU в формате: базовыйSKU-размер (цвет уже в базовом SKU)
            const variantSku = `${baseSku}-${size}`;
            
            variants.push({
              sku: variantSku,
              name: baseName,
              price: basePrice,
              currency: baseCurrency,
              availability: baseAvailability,
              color: color.name,
              size: size,
              all_image_urls: colorImages,
              product_url: this.sanitizeUrl(window.location.href)
            });
          });
        }
      }
      
      console.log(`TH extractAllVariants: Created ${variants.length} variants total`);
      return variants;
      
    } catch (error) {
      console.error('Error extracting TH variants:', error);
      return [];
    }
  }


  /**
   * Основной метод парсинга
   */
  async parseProduct() {
    try {
      console.log('Starting TH product parsing...');
      
      // Сначала проверяем базовую валидацию еще раз
      if (!this.isValidProductPage()) {
        console.error('TH parseProduct: Page validation failed');
        return [];
      }
      
      // Ждем загрузки JSON-LD (с повторными попытками)
      const jsonLdScript = await this.waitForJsonLd();
      if (!jsonLdScript) {
        console.warn('TH parseProduct: No JSON-LD found after waiting, continuing without it');
      }
      
      const variants = await this.extractAllVariants();
      
      if (variants.length === 0) {
        console.error('TH parseProduct: No variants extracted - this could indicate selector issues');
        
        // Дополнительная диагностика
        const jsonData = this.getJsonLdData();
        const productName = this.extractName();
        const sku = this.extractSku(jsonData);
        
        console.log('TH Diagnostic Info:');
        console.log('- JSON-LD available:', !!jsonData);
        console.log('- Product name:', productName);
        console.log('- SKU:', sku);
        console.log('- Colors found:', this.extractAllColors().length);
        console.log('- URL:', window.location.href);
        
        return [];
      }
      
      // Валидируем каждый вариант
      const validVariants = variants.filter(variant => {
        const validation = this.validateProductData(variant);
        if (!validation.isValid) {
          console.warn(`TH parseProduct: Invalid variant for ${variant.sku}:`, validation.warnings);
          return false;
        }
        if (validation.warnings.length > 0) {
          console.warn(`TH parseProduct: Warnings for variant ${variant.sku}:`, validation.warnings);
        }
        return true;
      });
      
      console.log(`TH parseProduct: Returning ${validVariants.length} valid variants out of ${variants.length} total`);
      return validVariants;
      
    } catch (error) {
      console.error('Error in TH parseProduct:', error);
      console.error('Stack trace:', error.stack);
      return [];
    }
  }
}

// Экспортируем для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TommyHilfigerParser;
}