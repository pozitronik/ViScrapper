/**
 * Simplified Tommy Hilfiger Parser - NO OBSERVERS
 * Focus on core data extraction functionality
 * Observer logic removed to debug size extraction issues
 */
class TommyHilfigerParser extends BaseParser {
  constructor() {
    // Define capabilities for Tommy Hilfiger
    const capabilities = {
      ...window.DEFAULT_CAPABILITIES,
      [window.JSON_LD_MUTATION_OBSERVER]: false,  // Self-managed updates
      [window.JSON_LD_TRACKING]: true,
      [window.URL_CHANGE_TRACKING]: false,  // SPA with internal handling
      [window.URL_NAVIGATION_TYPE]: window.NAV_TYPE_SPA,
      [window.COLOR_OBSERVER_MODE]: window.COLOR_MODE_SELF_MANAGED,  // Has own observer
      [window.PRODUCT_CHANGE_DETECTION]: window.CHANGE_DETECTION_STANDARD,
      [window.SUPPORTS_MULTI_COLOR]: true,  // Supports multi-color bulk posting
      [window.SUPPORTS_MULTI_SIZE]: true,  // Supports multi-size combinations
      [window.NEEDS_IMAGE_LAZY_LOADING]: false,
      [window.SPA_REFRESH_DELAY]: 0  // Immediate refresh on color change
    };
    
    super({
      siteName: 'Tommy Hilfiger',
      domain: 'usa.tommy.com',
      capabilities: capabilities,
      selectors: {
        buyBox: '.buy-box[data-comp="BuyBox"]',
        productName: '.product-name, h1.product-name',
        priceValue: '.sales .value[content]',
        priceContainer: '.buy-box__prices.product-detail__prices',
        colorsList: '[data-display-id="colorCode"]',
        sizesList: '#sizessize',
        jsonLdScript: 'script[type="application/ld+json"]'
      }
    });
    
    // SELF-INITIALIZATION: Setup color observer immediately when parser is created
    this.initializeColorObserver();
  }
  
  /**
   * Self-initialization of color observer - called from constructor
   */
  initializeColorObserver() {
    // Try immediate setup
    const immediateResult = this.setupColorChangeObserver();
    
    if (!immediateResult.success || immediateResult.listeners === 0) {
      // Fallback: DOM might not be ready yet
      setTimeout(() => {
        const delayedResult = this.setupColorChangeObserver();
        if (!delayedResult.success) {
          console.warn('TH Parser: Color observer setup failed');
        }
      }, 1000);
    }
  }

  /**
   * Проверка, что мы на странице товара Tommy Hilfiger
   * Использует JSON-LD + DOM элементы, не полагается на URL паттерны
   */
  isValidProductPage() {
    const url = window.location.href;
    
    if (!url.includes(this.config.domain)) {
      return false;
    }
    
    // Приоритет 1: Проверяем JSON-LD на наличие Product
    const jsonData = this.getJsonLdData();
    if (jsonData && jsonData['@type'] === 'Product') {
      return true;
    }
    
    // Приоритет 2: Проверяем основные элементы продукта
    const productName = document.querySelector(this.config.selectors.productName);
    const buyBox = document.querySelector(this.config.selectors.buyBox);
    
    return productName && buyBox;
  }

  /**
   * Извлечение названия продукта
   */
  extractName() {
    const element = document.querySelector(this.config.selectors.productName);
    return element?.textContent?.trim() || null;
  }

  /**
   * Извлечение SKU - генерирует уникальный SKU на основе продукта и выбранного цвета
   * Формат: {baseProductCode}-{colorCode} (например: MW41326-HGF-DW5)
   */
  extractSku(jsonData) {
    // Извлекаем базовый код продукта из radio ID
    const baseProductCode = this.extractUniqueProductId();
    if (!baseProductCode) {
      // No base product code found, trying fallbacks
      
      // Fallback 1: JSON-LD SKU
      if (jsonData && jsonData.sku) {
        return jsonData.sku;
      }
      
      // Fallback 2: URL pattern
      const urlMatch = window.location.pathname.match(/\/([A-Z0-9]+-[A-Z0-9]+)\.html$/i);
      if (urlMatch) {
        return urlMatch[1];
      }
      
      return null;
    }
    
    // Определяем выбранный цвет
    const selectedColorCode = this.extractSelectedColorCode();
    
    // Генерируем уникальный SKU
    return this.generateColorSpecificSku(baseProductCode, selectedColorCode);
  }

  /**
   * Извлечение кода выбранного цвета
   * Поддерживает как обычную структуру, так и grouped-by-price структуру
   */
  extractSelectedColorCode() {
    // Ищем выбранный цвет в различных возможных контейнерах
    let selectedColor = null;
    
    // Вариант 1: Обычная структура с одним colorsList
    const colorsList = document.querySelector(this.config.selectors.colorsList);
    if (colorsList) {
      selectedColor = colorsList.querySelector('input[type="radio"]:checked, input[type="radio"][aria-checked="true"]');
      if (selectedColor) {
      }
    }
    
    // Вариант 2: Grouped-by-price структура - ищем во всех видимых colorGroup
    if (!selectedColor) {
      const colorGroups = document.querySelectorAll('.colors-variant-list:not(.d-none)');
      
      for (const group of colorGroups) {
        selectedColor = group.querySelector('input[type="radio"]:checked, input[type="radio"][aria-checked="true"]');
        if (selectedColor) {
          break;
        }
      }
    }
    
    // Вариант 3: Поиск по всему документу как fallback
    if (!selectedColor) {
      selectedColor = document.querySelector('input[type="radio"].variant-colorCode:checked, input[type="radio"].variant-colorCode[aria-checked="true"]');
      if (selectedColor) {
      }
    }
    
    if (!selectedColor) {
      
      // Fallback: берем первый доступный цвет
      let firstColor = null;
      
      if (colorsList) {
        firstColor = colorsList.querySelector('input[type="radio"]');
      }
      
      if (!firstColor) {
        const colorGroups = document.querySelectorAll('.colors-variant-list:not(.d-none)');
        for (const group of colorGroups) {
          firstColor = group.querySelector('input[type="radio"]');
          if (firstColor) break;
        }
      }
      
      if (!firstColor) {
        firstColor = document.querySelector('input[type="radio"].variant-colorCode');
      }
      
      if (firstColor) {
        return this.extractColorCodeFromId(firstColor.getAttribute('id'));
      }
      
      return null;
    }
    
    return this.extractColorCodeFromId(selectedColor.getAttribute('id'));
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
   * Извлечение изображений - приоритет DOM над JSON-LD для актуальных данных
   */
  async extractImages() {
    // Приоритет 1: Извлекаем из DOM (актуальные изображения для текущего цвета)
    const domImages = await this.extractImagesFromDOM();
    if (domImages.length > 0) {
      return domImages;
    }
    
    // Приоритет 2: Fallback к JSON-LD (может быть устаревшим)
    const jsonData = this.getJsonLdData();
    const imageUrls = [];
    
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
   * Извлечение изображений из DOM (актуальные данные)
   * Парсит структуру: [data-comp="ProductImage"] > .product-image.swiper-slide > img
   */
  async extractImagesFromDOM() {
    try {
      // Находим основной контейнер с изображениями
      const productImageContainer = document.querySelector('[data-comp="ProductImage"]');
      if (!productImageContainer) {
        return [];
      }
      
      // Находим все слайды с изображениями
      const imageSlides = productImageContainer.querySelectorAll('.product-image.swiper-slide');
      if (imageSlides.length === 0) {
        return [];
      }
      
      const imageUrls = [];
      
      imageSlides.forEach((slide, index) => {
        const img = slide.querySelector('img');
        if (!img) {
          return;
        }
        
        let imageUrl = null;
        
        // Приоритет 1: Загруженное изображение (src атрибут)
        const src = img.getAttribute('src');
        if (src && src.startsWith('http') && !src.includes('data:image')) {
          imageUrl = src;
        }
        
        // Приоритет 2: Lazy-loaded изображения (источники в picture > source)
        if (!imageUrl) {
          const picture = slide.querySelector('picture');
          if (picture) {
            const sources = picture.querySelectorAll('source');
            for (const source of sources) {
              // Проверяем srcset или data-srcset
              let srcset = source.getAttribute('srcset') || source.getAttribute('data-srcset');
              if (srcset) {
                // Извлекаем первый URL из srcset (до первого пробела)
                const firstUrl = srcset.split(' ')[0];
                if (firstUrl && firstUrl.startsWith('http')) {
                  imageUrl = firstUrl;
                  break;
                }
              }
            }
          }
        }
        
        if (imageUrl) {
          // Применяем улучшение качества (поддерживает Tommy Hilfiger CDN)
          const enhancedUrl = this.enhanceImageQuality(imageUrl);
          imageUrls.push(enhancedUrl);
        }
      });
      
      return imageUrls;
      
    } catch (error) {
      console.error('TH extractImagesFromDOM: Error extracting images from DOM:', error);
      return [];
    }
  }

  /**
   * Извлечение цвета из выбранного элемента
   * Поддерживает как обычную структуру, так и grouped-by-price структуру
   */
  extractColor() {
    // Ищем выбранный цвет в различных возможных контейнерах
    let selectedColor = null;
    
    // Вариант 1: Обычная структура с одним colorsList
    const colorsList = document.querySelector(this.config.selectors.colorsList);
    if (colorsList) {
      selectedColor = colorsList.querySelector('input[type="radio"]:checked, input[type="radio"][aria-checked="true"]');
      if (selectedColor) {
      }
    }
    
    // Вариант 2: Grouped-by-price структура - ищем во всех видимых colorGroup
    if (!selectedColor) {
      const colorGroups = document.querySelectorAll('.colors-variant-list:not(.d-none)');
      for (const group of colorGroups) {
        selectedColor = group.querySelector('input[type="radio"]:checked, input[type="radio"][aria-checked="true"]');
        if (selectedColor) {
          break;
        }
      }
    }
    
    // Вариант 3: Поиск по всему документу как fallback
    if (!selectedColor) {
      selectedColor = document.querySelector('input[type="radio"].variant-colorCode:checked, input[type="radio"].variant-colorCode[aria-checked="true"]');
      if (selectedColor) {
      }
    }
    
    if (!selectedColor) {
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
   * Поддерживает как обычные размеры (S, M, L), так и "ONE SIZE"
   */
  async extractSizes() {
    try {
      // Look for size containers using .variant-list approach
      const sizeContainers = document.querySelectorAll('.variant-list[data-display-value]:not([data-display-id="colorCode"])');
      
      if (sizeContainers.length >= 2) {
        // Two-dimensional size system (e.g., Waist × Length)
        return await this.extractSizeCombinations(sizeContainers[0], sizeContainers[1]);
      } else if (sizeContainers.length === 1) {
        // One-dimensional size system
        return await this.extractSimpleSizes(sizeContainers[0]);
      }
      
      // Fallback: try old method
      return await this.extractSimpleSizes();
      
    } catch (error) {
      console.error('Error in TH extractSizes:', error);
      return [];
    }
  }

  /**
   * Extract simple sizes (one-dimensional)
   */
  async extractSimpleSizes(sizeContainer = null) {
    try {
      const availableSizes = [];
      
      let targetContainer = sizeContainer;
      
      if (!targetContainer) {
        targetContainer = document.querySelector(this.config.selectors.sizesList);
        
        if (!targetContainer) {
          targetContainer = document.querySelector('.variant-list[data-display-value]:not([data-display-id="colorCode"])');
        }
      }
      
      if (targetContainer) {
        const sizeInputs = targetContainer.querySelectorAll('input[type="radio"]');
        
        sizeInputs.forEach(input => {
          const inputId = input.getAttribute('id');
          const label = document.querySelector(`label[for="${inputId}"]`);
          
          // Проверяем, что размер не отключен (не имеет класс size-disabled)
          if (label && label.classList.contains('size-disabled')) {
            return;
          }
          
          if (input.classList.contains('disabled') || input.classList.contains('oos-variant')) {
            return;
          }
          
          const sizeLabel = label?.textContent?.trim();
          const dataValue = input.getAttribute('data-attr-value');
          
          const sizeValue = sizeLabel || dataValue;
          if (sizeValue) {
            availableSizes.push(sizeValue);
          }
        });
        
        if (availableSizes.length > 0) {
          return availableSizes;
        }
      }
      
      // Fallback for ONE SIZE products
      const sizeHeaders = document.querySelectorAll('[id^="pdp-attr-"], .attribute-label');
      for (const sizeHeader of sizeHeaders) {
        const sizeValueSpan = sizeHeader.querySelector('.variation__attr--value');
        if (sizeValueSpan) {
          const sizeText = sizeValueSpan.textContent?.trim();
          if (sizeText && sizeText !== '' && sizeText !== 'Отсутствует') {
            availableSizes.push(sizeText);
            break;
          }
        }
      }
      
      if (availableSizes.length === 0) {
        const oneSize = document.querySelector('[data-testid="size-onesize"], .size-one-size');
        if (oneSize) {
          availableSizes.push('ONE SIZE');
        }
      }
      
      console.log(`TH extractSimpleSizes: Final result - ${availableSizes.length} sizes found:`, availableSizes);
      return availableSizes;
      
    } catch (error) {
      console.error('Error in TH extractSimpleSizes:', error);
      return [];
    }
  }

  /**
   * Extract size combinations for two-dimensional systems (e.g., Waist × Length)
   * SIMPLIFIED VERSION - No observer management, focus on accurate data collection
   */
  async extractSizeCombinations(dimension1Container, dimension2Container) {
    try {
      // Get dimension types
      const dimension1Type = this.getDimensionType(dimension1Container);
      const dimension2Type = this.getDimensionType(dimension2Container);
      
      const dimension1Options = Array.from(dimension1Container.querySelectorAll('input[type="radio"].variant-item'));
      const combinations = {};
      
      // Save original selections for restoration (simplified)
      const originalDim1 = dimension1Container.querySelector('input[type="radio"][aria-checked="true"]');
      const originalDim2 = dimension2Container.querySelector('input[type="radio"][aria-checked="true"]');
      
      // Test each dimension1 option
      for (let i = 0; i < dimension1Options.length; i++) {
        const dim1Option = dimension1Options[i];
        const dim1Value = dim1Option.getAttribute('data-attr-value');
        
        // Skip obviously disabled options
        if (dim1Option.classList.contains('disabled') || dim1Option.classList.contains('oos-variant')) {
          continue;
        }
        
        // Click dimension1 option (try clicking the label instead of the input for better results)
        const dim1Label = document.querySelector(`label[for="${dim1Option.id}"]`);
        if (dim1Label) {
          dim1Label.click();
        } else {
          dim1Option.click();
        }
        
        // Wait for DOM to update - using conservative timing
        await this.wait(2000); // Even longer wait to ensure DOM fully updates
        
        // Get available dimension2 options after dimension1 selection
        const dimension2Options = Array.from(dimension2Container.querySelectorAll('input[type="radio"].variant-item'));
        const availableDim2Values = [];
        
        // Tommy Hilfiger adds .size-disabled class to labels of unavailable options in the second radiogroup
        // We just need to observe which labels DON'T have this class
        
        for (let j = 0; j < dimension2Options.length; j++) {
          const dim2Option = dimension2Options[j];
          const dim2Value = dim2Option.getAttribute('data-attr-value');
          
          if (!dim2Value) {
            continue;
          }
          
          // Find the label for this radio input
          const dim2Label = document.querySelector(`label[for="${dim2Option.id}"]`);
          
          if (!dim2Label) {
            continue;
          }
          
          // Check multiple possible disabled indicators on the label
          const hasDisabledClass = dim2Label.classList.contains('disabled');
          const hasSizeDisabledClass = dim2Label.classList.contains('size-disabled');
          const hasOosClass = dim2Label.classList.contains('oos');
          const isLabelDisabled = hasDisabledClass || hasSizeDisabledClass || hasOosClass;
          
          if (!isLabelDisabled) {
            // Label is not disabled - option is available for this waist size
            availableDim2Values.push(dim2Value);
          }
        }
        
        if (availableDim2Values.length > 0) {
          combinations[dim1Value] = availableDim2Values;
        }
      }
      
      // Simple restoration - just restore original selections if they existed
      try {
        if (originalDim1 && !originalDim1.checked) {
          originalDim1.click();
          await this.wait(200);
        }
        if (originalDim2 && !originalDim2.checked) {
          originalDim2.click();
          await this.wait(200);
        }
      } catch (e) {
        // Restoration error (non-critical)
      }
      
      return {
        dimension1_type: dimension1Type,
        dimension2_type: dimension2Type,
        combinations: combinations
      };
      
    } catch (error) {
      console.error('Error extracting size combinations:', error);
      return [];
    }
  }

  /**
   * Извлечение всех доступных цветов
   * Извлекает цветовые коды из radio ID формата: MW41326-HGF_colorCodeitem-DW5
   * Поддерживает как обычную структуру, так и grouped-by-price структуру
   */
  getDimensionType(container) {
    try {
      const displayValue = container.getAttribute('data-display-value');
      if (displayValue) {
        return displayValue;
      }
      
      const displayId = container.getAttribute('data-display-id');
      if (displayId) {
        return displayId.charAt(0).toUpperCase() + displayId.slice(1);
      }
      
      const containerId = container.getAttribute('id');
      if (containerId) {
        const cleaned = containerId.replace(/^sizes/, '');
        return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
      }
      
      const parent = container.closest('.product-detail__attribute-item');
      if (parent) {
        const header = parent.querySelector('.attribute-label .variation__attr--name');
        if (header) {
          return header.textContent.trim();
        }
      }
      
      return 'Unknown';
      
    } catch (error) {
      return 'Unknown';
    }
  }

  /**
   * Извлечение уникального идентификатора продукта из radio ID
   * Парсит ID формата: MW41326-HGF_colorCodeitem-DW5 -> MW41326-HGF
   * Поддерживает как обычную структуру, так и grouped-by-price структуру
   */
  extractUniqueProductId() {
    // Ищем color inputs в различных возможных контейнерах
    let firstColorInput = null;
    
    // Вариант 1: Обычная структура с одним colorsList
    const colorsList = document.querySelector(this.config.selectors.colorsList);
    if (colorsList) {
      firstColorInput = colorsList.querySelector('input[type="radio"]');
    }
    
    // Вариант 2: Grouped-by-price структура - ищем во всех colorGroup
    if (!firstColorInput) {
      const colorGroups = document.querySelectorAll('.colors-variant-list:not(.d-none)');
      
      for (const group of colorGroups) {
        const input = group.querySelector('input[type="radio"]');
        if (input) {
          firstColorInput = input;
          break;
        }
      }
    }
    
    // Вариант 3: Поиск по всему документу как fallback
    if (!firstColorInput) {
      firstColorInput = document.querySelector('input[type="radio"].variant-colorCode');
    }
    
    if (!firstColorInput) {
      return null;
    }
    
    const inputId = firstColorInput.getAttribute('id');
    if (!inputId) {
      console.log('TH extractUniqueProductId: No ID found on color input');
      return null;
    }
    
    // Парсим ID формата: XM05531-DW6_colorCodeitem-DW6 -> XM05531
    // Новая логика: извлекаем только базовый код продукта (до первого дефиса после букв)
    let match = inputId.match(/^([A-Z]+\d+)(-[A-Z0-9]+)?_colorCodeitem-/);
    if (match) {
      const uniqueProductId = match[1]; // XM05531 (только базовый код)
      console.log(`TH extractUniqueProductId: Extracted base code "${uniqueProductId}" from "${inputId}"`);
      return uniqueProductId;
    }
    
    // Fallback logic - consistent with Calvin Klein approach
    match = inputId.match(/^([^_]+)_colorCodeitem-/);
    if (!match) {
      console.log('TH extractUniqueProductId: ID format does not match any expected pattern:', inputId);
      return null;
    }
    
    let fullPart = match[1]; // e.g., MW41326-HGF
    
    // CONSISTENT WITH CALVIN KLEIN: Always take only the first part before first dash
    // This ensures we never get double color codes
    const parts = fullPart.split('-');
    const uniqueProductId = parts[0]; // MW41326-HGF -> MW41326
    
    return uniqueProductId;
  }

  /**
   * Извлечение цветового кода из radio ID
   * Парсит ID формата: MW41326-HGF_colorCodeitem-DW5 -> DW5
   */
  extractColorCodeFromId(inputId) {
    if (!inputId) {
      return null;
    }
    
    // Парсим ID формата: MW41326-HGF_colorCodeitem-DW5
    const match = inputId.match(/_colorCodeitem-(.+)$/);
    if (!match) {
      return null;
    }
    
    const colorCode = match[1]; // DW5
    return colorCode;
  }

  /**
   * Генерация уникального SKU для конкретного цвета
   * Формат: {baseProductCode}-{colorCode} (например: MW41326-HGF-DW5)
   */
  generateColorSpecificSku(baseProductCode, colorCode) {
    if (!baseProductCode) {
      console.warn('TH generateColorSpecificSku: No base product code provided');
      return null;
    }

    if (!colorCode) {
      return baseProductCode;
    }

    const colorSpecificSku = `${baseProductCode}-${colorCode}`;
    return colorSpecificSku;
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
   * Извлечение артикула продукта (базовый код продукта)
   * Возвращает базовый код продукта как артикул (например: MW41326-HGF)
   */
  extractItem() {
    const baseProductCode = this.extractUniqueProductId();
    if (baseProductCode) {
      console.log('TH extractItem: Using base product code as item:', baseProductCode);
      return baseProductCode;
    }
    
    console.log('TH extractItem: No base product code found');
    return null;
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
   * Настройка наблюдателя за изменением цвета (только для Tommy Hilfiger)
   * Устанавливается сразу при загрузке страницы для отслеживания ранних изменений
   */
  setupColorChangeObserver() {
    try {
      // Очистка предыдущих слушателей если есть
      if (this.colorListeners && this.colorListeners.length > 0) {
        this.cleanup();
      }
      
      // Сохраняем текущий цвет для сравнения
      this.currentColorCode = this.extractSelectedColorCode();
      this.colorListeners = []; // Массив для очистки
      
      
      // Проверяем, есть ли нужные элементы на странице
      if (!document.querySelector(this.config.selectors.colorsList) && 
          !document.querySelector('.colors-variant-list:not(.d-none)') &&
          !document.querySelector('input[type="radio"].variant-colorCode')) {
        console.warn('TH setupColorChangeObserver: No color elements found on page yet');
        return { success: false, error: 'No color elements found', listeners: 0 };
      }
      
      // Находим все цветовые элементы
      const colorInputs = this.getAllColorInputs();
      const colorLabels = this.getAllColorLabels(colorInputs);
      
      
      if (colorInputs.length === 0) {
        console.warn('TH setupColorChangeObserver: No color inputs found, setup failed');
        return { success: false, error: 'No color inputs found', listeners: 0 };
      }
      
      // Устанавливаем слушатели на radio inputs
      colorInputs.forEach((input, index) => {
        const handler = this.handleColorChange.bind(this);
        input.addEventListener('change', handler);
        this.colorListeners.push({ element: input, type: 'change', handler });
      });
      
      // Устанавливаем слушатели на labels (иногда более надежно)
      colorLabels.forEach((label, index) => {
        const handler = this.handleColorLabelClick.bind(this);
        label.addEventListener('click', handler);
        this.colorListeners.push({ element: label, type: 'click', handler });
      });
      
      // Автоматическая очистка при уходе со страницы
      const cleanupHandler = this.cleanup.bind(this);
      window.addEventListener('beforeunload', cleanupHandler);
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) this.cleanup();
      });
      
      return { success: true, listeners: this.colorListeners.length };
      
    } catch (error) {
      console.error('Error setting up color observer:', error);
      return { success: false, error: error.message };
    }
  }
  
  /**
   * Находит все цветовые radio inputs в различных структурах TH
   */
  getAllColorInputs() {
    const colorInputs = [];
    
    // Структура 1: Основной colorsList
    const mainColorsList = document.querySelector(this.config.selectors.colorsList);
    if (mainColorsList) {
      const inputs = mainColorsList.querySelectorAll('input[type="radio"]');
      colorInputs.push(...inputs);
      console.log(`TH getAllColorInputs: Found ${inputs.length} inputs in main colorsList`);
    }
    
    // Структура 2: Grouped-by-price структура
    const colorGroups = document.querySelectorAll('.colors-variant-list:not(.d-none)');
    colorGroups.forEach((group, groupIndex) => {
      const inputs = group.querySelectorAll('input[type="radio"]');
      colorInputs.push(...inputs);
      console.log(`TH getAllColorInputs: Found ${inputs.length} inputs in color group ${groupIndex}`);
    });
    
    // Структура 3: Fallback - поиск по классу
    const fallbackInputs = document.querySelectorAll('input[type="radio"].variant-colorCode');
    // Добавляем только те, которых еще нет в массиве
    fallbackInputs.forEach(input => {
      if (!colorInputs.includes(input)) {
        colorInputs.push(input);
      }
    });
    
    console.log(`TH getAllColorInputs: Total unique color inputs found: ${colorInputs.length}`);
    return colorInputs;
  }
  
  /**
   * Находит все labels для цветовых inputs
   */
  getAllColorLabels(colorInputs) {
    const colorLabels = [];
    
    colorInputs.forEach(input => {
      const inputId = input.getAttribute('id');
      if (inputId) {
        const label = document.querySelector(`label[for="${inputId}"]`);
        if (label) {
          colorLabels.push(label);
        }
      }
    });
    
    console.log(`TH getAllColorLabels: Found ${colorLabels.length} labels for color inputs`);
    return colorLabels;
  }
  
  /**
   * Обработчик изменения цвета через radio input
   */
  async handleColorChange(event) {
    try {
      // Небольшая задержка для стабилизации DOM
      await this.wait(100);
      
      const newColorCode = this.extractSelectedColorCode();
      
      // Проверяем, действительно ли цвет изменился
      if (newColorCode && newColorCode !== this.currentColorCode) {
        this.currentColorCode = newColorCode;
        await this.sendColorUpdateMessage();
      }
      
    } catch (error) {
      console.error('TH handleColorChange: Error handling color change:', error);
    }
  }
  
  /**
   * Обработчик клика по label (альтернативный способ)
   */
  async handleColorLabelClick(event) {
    try {
      console.log('TH handleColorLabelClick: Color label click detected');
      
      // Store color BEFORE click to compare properly
      const colorBeforeClick = this.extractSelectedColorCode();
      console.log(`TH handleColorLabelClick: Color before click: ${colorBeforeClick}`);
      
      // Progressive timeout approach for slow connections
      let newColorCode = null;
      const timeouts = [800, 1500]; // Try 800ms, then 1500ms if needed
      
      for (let i = 0; i < timeouts.length; i++) {
        console.log(`TH handleColorLabelClick: Waiting ${timeouts[i]}ms for DOM update (attempt ${i + 1}/${timeouts.length})...`);
        await this.wait(timeouts[i]);
        
        newColorCode = this.extractSelectedColorCode();
        console.log(`TH handleColorLabelClick: Color after ${timeouts[i]}ms wait: ${newColorCode}`);
        
        // If color changed from before, we're good
        if (newColorCode !== colorBeforeClick) {
          console.log(`TH handleColorLabelClick: ✓ Color change detected after ${timeouts[i]}ms`);
          break;
        }
        
        // If this was the last attempt, we'll proceed anyway
        if (i === timeouts.length - 1) {
          console.warn('TH handleColorLabelClick: ⚠️ DOM update took longer than expected, proceeding anyway');
        }
      }
      
      console.log(`TH handleColorLabelClick: Final color code: ${newColorCode}`);
      console.log(`TH handleColorLabelClick: Current stored color code: ${this.currentColorCode}`);
      
      // Compare with BOTH stored color AND pre-click color
      const changedFromStored = newColorCode !== this.currentColorCode;
      const changedFromBefore = newColorCode !== colorBeforeClick;
      
      console.log(`TH handleColorLabelClick: Changed from stored? ${changedFromStored}`);
      console.log(`TH handleColorLabelClick: Changed from before click? ${changedFromBefore}`);
      
      // Trigger refresh if color changed from either reference
      if (newColorCode && (changedFromStored || changedFromBefore)) {
        console.log(`TH handleColorLabelClick: ✓ Color change detected: ${this.currentColorCode} → ${newColorCode}`);
        
        this.currentColorCode = newColorCode;
        await this.sendColorUpdateMessage();
      } else {
        console.log(`TH handleColorLabelClick: ✗ No color change detected (stored: ${this.currentColorCode}, before: ${colorBeforeClick}, after: ${newColorCode})`);
      }
      
    } catch (error) {
      console.error('TH handleColorLabelClick: Error handling label click:', error);
    }
  }
  
  /**
   * Отправка сообщения об изменении цвета
   * Sends color update message that will trigger SPA refresh based on parser capabilities
   */
  async sendColorUpdateMessage() {
    try {
      console.log('TH sendColorUpdateMessage: Color changed - sending update...');
      
      // Get current color and images
      const currentColor = this.extractColor();
      const currentImages = this.extractImages();
      
      // Send color update message
      // Content.js will handle SPA refresh based on SPA_REFRESH_DELAY capability
      chrome.runtime.sendMessage({
        action: 'colorUpdated',
        color: currentColor,
        images: currentImages,
        source: 'tommy-hilfiger'
      });
      
      console.log('TH sendColorUpdateMessage: Color update message sent');
      
    } catch (error) {
      console.error('TH sendColorUpdateMessage: Error sending color update message:', error);
    }
  }
  
  /**
   * Очистка слушателей событий
   */
  cleanup() {
    try {
      if (this.colorListeners && this.colorListeners.length > 0) {
        console.log(`TH cleanup: Removing ${this.colorListeners.length} color change listeners...`);
        
        this.colorListeners.forEach(({ element, type, handler }) => {
          element.removeEventListener(type, handler);
        });
        
        this.colorListeners = [];
        console.log('TH cleanup: All color listeners removed');
      }
    } catch (error) {
      console.error('TH cleanup: Error during cleanup:', error);
    }
  }

  /**
   * Извлечение всех доступных цветов
   * Извлекает цветовые коды из radio ID формата: MW41326-HGF_colorCodeitem-DW5
   * Поддерживает как обычную структуру, так и grouped-by-price структуру
   */
  extractAllColors() {
    const colors = [];
    let colorInputs = [];
    
    // Вариант 1: Обычная структура с одним colorsList
    const colorsList = document.querySelector(this.config.selectors.colorsList);
    if (colorsList) {
      const inputs = colorsList.querySelectorAll('input[type="radio"]');
      colorInputs = colorInputs.concat(Array.from(inputs));
    }
    
    // Вариант 2: Grouped-by-price структура - собираем из всех видимых colorGroup
    const colorGroups = document.querySelectorAll('.colors-variant-list:not(.d-none)');
    
    colorGroups.forEach((group, index) => {
      const inputs = group.querySelectorAll('input[type="radio"]');
      colorInputs = colorInputs.concat(Array.from(inputs));
    });
    
    // Вариант 3: Fallback - поиск по всему документу
    if (colorInputs.length === 0) {
      const fallbackInputs = document.querySelectorAll('input[type="radio"].variant-colorCode');
      colorInputs = colorInputs.concat(Array.from(fallbackInputs));
    }
    
    // Удаляем дубликаты по ID
    const uniqueInputs = [];
    const seenIds = new Set();
    
    colorInputs.forEach(input => {
      const inputId = input.getAttribute('id');
      if (inputId && !seenIds.has(inputId)) {
        uniqueInputs.push(input);
        seenIds.add(inputId);
      }
    });
    
    uniqueInputs.forEach(input => {
      const inputId = input.getAttribute('id');
      if (!inputId) {
        return;
      }
      
      // Извлекаем цветовой код из ID
      const colorCode = this.extractColorCodeFromId(inputId);
      if (!colorCode) {
        return;
      }
      
      // Извлекаем название цвета (для отображения)
      const colorName = this.extractColorNameFromInput(input);
      
      colors.push({
        code: colorCode,
        name: colorName || colorCode,
        isSelected: input.checked || input.getAttribute('aria-checked') === 'true',
        inputId: inputId  // Сохраняем ID для удобства отладки
      });
      
    });
    
    return colors;
  }

  /**
   * Переключение на конкретный цвет
   */
  async switchToColor(color) {
    try {
      // Найти input элемент для этого цвета
      let colorInput = null;
      
      // Способ 1: Прямой поиск по document.getElementById (самый надежный, не требует экранирования)
      if (color.inputId) {
        colorInput = document.getElementById(color.inputId);
      }
      
      // Способ 2: Поиск по коду цвета в ID (с атрибутными селекторами)
      if (!colorInput && color.code) {
        const possibleSelectors = [
          `input[id*="${color.code}"]`,
          `input[id*="colorCodeitem-${color.code}"]`,
          `input[data-attr-value="${color.code}"]`
        ];
        
        for (const selector of possibleSelectors) {
          try {
            colorInput = document.querySelector(selector);
            if (colorInput) {
              break;
            }
          } catch (e) {
            // Selector failed, try next
          }
        }
      }
      
      // Способ 3: Поиск среди всех цветовых input-ов
      if (!colorInput) {
        try {
          const allColors = this.extractAllColors();
          const targetColor = allColors.find(c => c.code === color.code || c.name === color.name);
          
          if (targetColor && targetColor.inputId) {
            colorInput = document.getElementById(targetColor.inputId);
          }
        } catch (e) {
          // extractAllColors failed, continue
        }
      }
      
      if (!colorInput) {
        console.error(`TH switchToColor: Could not find input for color ${color.name} (${color.code})`);
        return { success: false, error: `Color input not found for ${color.name}` };
      }
      
      // Проверяем, не выбран ли уже этот цвет
      if (colorInput.checked || colorInput.getAttribute('aria-checked') === 'true') {
        return { success: true, message: 'Color already selected' };
      }
      
      // Кликаем на input для выбора цвета
      colorInput.click();
      
      // Даем время на обновление DOM
      await this.wait(1000);
      
      // Проверяем, что цвет успешно выбран
      const isNowSelected = colorInput.checked || colorInput.getAttribute('aria-checked') === 'true';
      
      if (!isNowSelected) {
        return { success: false, error: `Failed to select color ${color.name}` };
      }
      
      // Дополнительное время для обновления изображений и размеров
      await this.wait(1500);
      
      return { success: true, message: `Successfully switched to ${color.name}` };
      
    } catch (error) {
      console.error(`Error switching to color ${color.name}:`, error);
      return { success: false, error: error.message };
    }
  }

  /**
   * Извлечение данных для ТЕКУЩЕГО выбранного цвета (после переключения)
   * Используется при скрапинге конкретного цветового варианта
   */
  async extractCurrentVariant() {
    try {
      console.log('TH extractCurrentVariant: Starting extraction for current page state...');
      
      const baseJsonData = this.getJsonLdData();
      const baseProductCode = this.extractUniqueProductId();
      const currentName = this.extractName();
      const currentPrice = this.extractPrice(baseJsonData);
      const currentCurrency = this.extractCurrency(baseJsonData);
      const currentAvailability = this.extractAvailability(baseJsonData);
      
      // Извлекаем данные текущего выбранного цвета
      const currentColorCode = this.extractSelectedColorCode();
      const currentColorName = this.extractColor();
      
      console.log(`TH extractCurrentVariant: Current color - Code: "${currentColorCode}", Name: "${currentColorName}"`);
      
      if (!baseProductCode) {
        console.error('TH extractCurrentVariant: No base product code found');
        return null;
      }
      
      if (!currentColorCode) {
        console.error('TH extractCurrentVariant: No current color code found');
        return null;
      }
      
      // Генерируем SKU для текущего цвета
      const currentSku = this.generateColorSpecificSku(baseProductCode, currentColorCode);
      console.log(`TH extractCurrentVariant: Generated SKU: ${currentSku}`);
      
      // Извлекаем размеры и изображения для текущего состояния
      const currentSizes = await this.extractSizes();
      const currentImages = await this.extractImages();
      
      console.log(`TH extractCurrentVariant: Found ${Array.isArray(currentSizes) ? currentSizes.length : 'complex'} sizes and ${currentImages.length} images`);
      
      const variant = {
        sku: currentSku,
        name: currentName,
        price: currentPrice,
        currency: currentCurrency,
        availability: currentAvailability,
        color: currentColorName,
        available_sizes: Array.isArray(currentSizes) ? currentSizes : null,
        size_combinations: !Array.isArray(currentSizes) ? currentSizes : null,
        all_image_urls: currentImages,
        main_image_url: currentImages.length > 0 ? currentImages[0] : null,
        item: baseProductCode,
        product_url: this.sanitizeUrl(window.location.href),
        store: this.config.siteName,
        comment: ''
      };
      
      console.log('TH extractCurrentVariant: Created variant:', {
        sku: variant.sku,
        color: variant.color,
        price: variant.price,
        sizeType: typeof currentSizes,
        imageCount: variant.all_image_urls.length
      });
      
      return variant;
      
    } catch (error) {
      console.error('TH extractCurrentVariant: Error extracting current variant:', error);
      return null;
    }
  }

  /**
   * Основной метод парсинга для SINGLE COLOR (текущего состояния)
   */
  async parseProduct() {
    try {
      console.log('Starting SIMPLIFIED TH product parsing...');
      
      if (!this.isValidProductPage()) {
        console.error('TH parseProduct: Page validation failed');
        return [];
      }
      
      const jsonLdScript = await this.waitForJsonLd();
      if (!jsonLdScript) {
        console.warn('TH parseProduct: No JSON-LD found after waiting, continuing without it');
      }
      
      // Extract basic product data
      const jsonData = this.getJsonLdData();
      const baseProductCode = this.extractUniqueProductId();
      const baseName = this.extractName();
      const basePrice = this.extractPrice(jsonData);
      const baseCurrency = this.extractCurrency(jsonData);
      const baseAvailability = this.extractAvailability(jsonData);
      const currentColorCode = this.extractSelectedColorCode();
      const currentColorName = this.extractColor();
      const currentImages = await this.extractImages();
      const currentSizes = await this.extractSizes();
      
      if (!baseProductCode) {
        console.error('TH parseProduct: No base product code found, cannot create variants');
        return [];
      }
      
      // Create single variant for current state
      const currentSku = this.generateColorSpecificSku(baseProductCode, currentColorCode);
      
      const variant = {
        sku: currentSku,
        name: baseName,
        price: basePrice,
        currency: baseCurrency,
        availability: baseAvailability,
        color: currentColorName,
        available_sizes: currentSizes,
        all_image_urls: currentImages,
        main_image_url: currentImages.length > 0 ? currentImages[0] : null,
        item: baseProductCode,
        product_url: this.sanitizeUrl(window.location.href),
        store: this.config.siteName,
        comment: ''
      };
      
      console.log('TH parseProduct: Created variant:', {
        sku: variant.sku,
        color: variant.color,
        price: variant.price,
        sizeType: typeof variant.available_sizes,
        sizeData: variant.available_sizes,
        imageCount: variant.all_image_urls.length
      });
      
      const validation = this.validateProductData(variant);
      if (!validation.isValid) {
        console.warn(`TH parseProduct: Invalid variant for ${variant.sku}:`, validation.warnings);
        return [];
      }
      
      if (validation.warnings.length > 0) {
        console.warn(`TH parseProduct: Warnings for variant ${variant.sku}:`, validation.warnings);
      }
      
      console.log(`TH parseProduct: Returning 1 valid variant`);
      return [variant];
      
    } catch (error) {
      console.error('Error in TH parseProduct:', error);
      console.error('Stack trace:', error.stack);
      return [];
    }
  }
}

// Register with SiteRegistry
if (typeof SiteRegistry !== 'undefined') {
  SiteRegistry.register({
    domain: 'usa.tommy.com',
    siteId: 'tommy',
    siteName: 'Tommy Hilfiger',
    parserClass: TommyHilfigerParser,
    urlPatterns: ['usa.tommy.com', 'tommy.com'],
    metadata: {
      country: 'US',
      currency: 'USD'
    }
  });
}

// Экспортируем для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TommyHilfigerParser;
}