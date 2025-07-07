/**
 * Парсер для Victoria's Secret
 * Содержит всю логику извлечения данных, специфичную для VS
 */
class VictoriasSecretParser extends BaseParser {
  constructor() {
    super({
      siteName: 'Victoria\'s Secret',
      domain: 'victoriassecret.com',
      selectors: {
        productInfo: '[data-testid="ProductInfo-shortDescription"]',
        productPrice: '[data-testid="ProductPrice"]',
        genericId: '[data-testid="ProductInfo-genericId"]',
        selectedChoice: '[data-testid="SelectedChoiceLabel"]',
        composition: '[data-testid="ProductComposition"]',
        primaryProduct: '[data-testid="PrimaryProduct"]',
        primaryImage: '[data-testid="PrimaryProductImage"]',
        staticSize: '[data-testid="Size"]',
        boxSelectorSize1: '[data-testid="BoxSelector-size1"]',
        boxSelectorSize2: '[data-testid="BoxSelector-size2"]',
        boxSelectorCombo: '[data-testid="BoxSelector-comboSize"]',
        jsonLdScript: 'script[type="application/ld+json"][id="structured-data-pdp"]'
      }
    });
  }

  /**
   * Проверка, что мы на странице товара VS
   */
  isValidProductPage() {
    const url = window.location.href;
    console.log('Checking VS page validity, URL:', url);
    
    if (!url.includes(this.config.domain)) {
      console.log('Not a Victoria\'s Secret page');
      return false;
    }
    
    const hasProductInfo = document.querySelector(this.config.selectors.productInfo);
    const hasProductPrice = document.querySelector(this.config.selectors.productPrice);
    
    console.log('ProductInfo element:', hasProductInfo);
    console.log('ProductPrice element:', hasProductPrice);
    
    const isValid = hasProductInfo && hasProductPrice;
    console.log('Page is valid VS product page:', isValid);
    
    return isValid;
  }

  /**
   * Извлечение названия продукта
   */
  extractName() {
    const element = document.querySelector(this.config.selectors.productInfo);
    return element?.textContent?.trim() || null;
  }

  /**
   * Извлечение SKU из JSON-LD
   */
  extractSku(jsonData) {
    if (jsonData && jsonData.sku) {
      return jsonData.sku;
    }
    return null;
  }

  /**
   * Извлечение цены
   */
  extractPrice(jsonData) {
    if (jsonData && jsonData.offers && jsonData.offers.price) {
      return parseFloat(jsonData.offers.price);
    }
    
    // Альтернативный способ - из элемента на странице
    const priceElement = document.querySelector(this.config.selectors.productPrice);
    if (priceElement) {
      const priceText = priceElement.textContent.trim();
      const priceMatch = priceText.match(/[\d,]+\.?\d*/);
      if (priceMatch) {
        return parseFloat(priceMatch[0].replace(',', ''));
      }
    }
    
    return null;
  }

  /**
   * Извлечение изображений
   */
  extractImages() {
    const container = document.querySelector(this.config.selectors.primaryImage);
    if (!container) return [];
    
    const images = container.querySelectorAll('img');
    const imageUrls = [];
    
    images.forEach(img => {
      if (img.src && img.src.startsWith('http')) {
        const absoluteUrl = new URL(img.src, window.location.href).href;
        if (!imageUrls.includes(absoluteUrl)) {
          imageUrls.push(absoluteUrl);
        }
      }
    });
    
    return imageUrls;
  }

  /**
   * Извлечение цвета (переопределение базового метода)
   */
  extractColor() {
    const element = document.querySelector(this.config.selectors.selectedChoice);
    if (element) {
      return element.textContent.replace('|', '').trim();
    }
    return null;
  }

  /**
   * Извлечение состава (переопределение базового метода)
   */
  extractComposition() {
    const element = document.querySelector(this.config.selectors.composition);
    return element?.textContent?.trim() || null;
  }

  /**
   * Извлечение артикула (переопределение базового метода)
   */
  extractItem() {
    const element = document.querySelector(this.config.selectors.genericId);
    return element?.textContent?.trim() || null;
  }

  /**
   * Ожидание появления JSON-LD скрипта (переопределение базового метода)
   */
  async waitForJsonLd(timeout = 10000) {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const jsonLdScript = document.querySelector(this.config.selectors.jsonLdScript);
      if (jsonLdScript && jsonLdScript.textContent.trim()) {
        return jsonLdScript;
      }
      
      await this.wait(100);
    }
    
    return null;
  }

  /**
   * Извлечение размеров продукта (основной метод - точная копия из content.js)
   */
  async extractSizes() {
    try {
      console.log('Starting VS size extraction...');
      
      // Ограничиваем поиск основным блоком продукта
      const primaryProduct = document.querySelector(this.config.selectors.primaryProduct);
      
      if (!primaryProduct) {
        console.log('No PrimaryProduct container found');
        return [];
      }
      
      console.log('Found PrimaryProduct container, searching within it...');
      
      // Проверяем статические размеры (простой текст)
      const staticSizeContainer = primaryProduct.querySelector(this.config.selectors.staticSize);
      
      // Находим первый блок BoxSelector-size1 в primaryProduct
      const sizeContainer1 = primaryProduct.querySelector(this.config.selectors.boxSelectorSize1);
      
      if (staticSizeContainer && !sizeContainer1) {
        console.log('Found static size container, extracting text size...');
        const staticSize = this.extractStaticSize(staticSizeContainer);
        if (staticSize) {
          console.log('Static size extracted:', staticSize);
          return [staticSize];
        }
      }
      
      // Проверяем комбинированные размеры (BoxSelector-comboSize)
      const comboSizeContainer = primaryProduct.querySelector(this.config.selectors.boxSelectorCombo);
      
      if (comboSizeContainer) {
        console.log('Found BoxSelector-comboSize container, extracting combo sizes...');
        const comboSizes = this.extractComboSizes(comboSizeContainer);
        if (comboSizes.length > 0) {
          console.log('Combo sizes extracted:', comboSizes);
          return comboSizes;
        }
      }

      if (!sizeContainer1) {
        console.log('No BoxSelector-size1 found within PrimaryProduct');
        return [];
      }
      
      // Ищем BoxSelector-size2 на том же уровне DOM
      const sizeContainer2 = this.findRelatedSizeContainer(sizeContainer1);
      
      console.log(`Found size containers: size1=${!!sizeContainer1}, size2=${!!sizeContainer2}`);
      
      // Проверяем связность - size2 должен быть на том же уровне DOM
      const areContainersRelated = !!sizeContainer2;
      
      // Проверяем валидность контейнеров
      let hasValidSize1 = false;
      let hasValidSize2 = false;
      let size1Options = [];
      let size2Options = [];
      
      if (sizeContainer1) {
        size1Options = Array.from(sizeContainer1.querySelectorAll('[role="radio"]'));
        const enabledSize1Options = size1Options.filter(opt => opt.getAttribute('aria-disabled') !== 'true');
        hasValidSize1 = enabledSize1Options.length > 0;
        size1Options = enabledSize1Options;
      }
      
      if (sizeContainer2 && areContainersRelated) {
        size2Options = Array.from(sizeContainer2.querySelectorAll('[role="radio"]'));
        const enabledSize2Options = size2Options.filter(opt => opt.getAttribute('aria-disabled') !== 'true');
        hasValidSize2 = enabledSize2Options.length > 0;
        size2Options = enabledSize2Options;
      }
      
      console.log(`Size detection: Size1 valid: ${hasValidSize1} (${size1Options.length} options), Size2 valid: ${hasValidSize2} (${size2Options.length} options)`);
      
      // Определяем тип продукта
      const isRealCombination = hasValidSize1 && hasValidSize2 && areContainersRelated;
      
      console.log(`Is real combination product: ${isRealCombination}`);
      
      if (isRealCombination) {
        // Двухразмерный продукт - извлекаем комбинации
        console.log('True dual size selectors detected, extracting combinations...');
        const combinationResult = await this.extractSizeCombinations(sizeContainer1, sizeContainer2);
        if (combinationResult.success) {
          console.log('Size combinations extracted:', combinationResult.data);
          return combinationResult.data;
        } else {
          console.error('Failed to extract size combinations:', combinationResult.error);
          return null;
        }
      } else if (hasValidSize1) {
        // Одноразмерный продукт (используем size1)
        console.log('Single size selector detected (using size1), extracting simple sizes...');
        const availableSizes = size1Options.map(btn => btn.textContent.trim()).filter(size => size);
        console.log('Simple sizes extracted:', availableSizes);
        return availableSizes;
      } else {
        console.log('No valid size options found');
        return [];
      }
      
    } catch (error) {
      console.error('Error in VS extractSizes:', error);
      return [];
    }
  }

  /**
   * Извлечение статических размеров из data-testid="Size"
   */
  extractStaticSize(staticSizeContainer) {
    try {
      console.log('Extracting static size...');
      
      // Сначала пробуем найти все span элементы
      const spans = staticSizeContainer.querySelectorAll('span');
      console.log(`Found ${spans.length} span elements in static size container`);
      
      for (const span of spans) {
        const text = span.textContent.trim();
        console.log(`Checking span text: "${text}"`);
        
        // Пропускаем пустые и служебные тексты
        if (!text || text === 'Size' || text === 'Размер' || text === 'Size ') {
          console.log(`Skipping span with text: "${text}"`);
          continue;
        }
        
        // Проверяем, что это не просто слово "Size" в начале
        if (text.toLowerCase().startsWith('size ') && text.length > 5) {
          // Извлекаем размер после "Size "
          const sizeValue = text.substring(5).trim();
          if (sizeValue) {
            console.log(`Found static size after "Size ": ${sizeValue}`);
            return sizeValue;
          }
        }
        
        // Если это не начинается с "Size ", то вероятно это и есть размер
        if (!text.toLowerCase().startsWith('size')) {
          console.log(`Found static size: ${text}`);
          return text;
        }
      }
      
      // Если spans не дали результата, попробуем получить весь текст контейнера
      const fullText = staticSizeContainer.textContent.trim();
      console.log(`Full container text: "${fullText}"`);
      
      // Ищем паттерн "Size [размер]"
      const sizeMatch = fullText.match(/Size\s+(.+)/i);
      if (sizeMatch && sizeMatch[1]) {
        const extractedSize = sizeMatch[1].trim();
        console.log(`Extracted size from full text: ${extractedSize}`);
        return extractedSize;
      }
      
      console.log('No static size found in container');
      return null;
      
    } catch (error) {
      console.error('Error extracting static size:', error);
      return null;
    }
  }

  /**
   * Извлечение комбинированных размеров из BoxSelector-comboSize
   */
  extractComboSizes(comboSizeContainer) {
    try {
      console.log('Extracting combo sizes...');
      
      const sizeOptions = Array.from(comboSizeContainer.querySelectorAll('[role="radio"]'));
      const availableOptions = sizeOptions.filter(opt => opt.getAttribute('aria-disabled') !== 'true');
      
      const comboSizes = availableOptions.map(option => {
        const dataValue = option.getAttribute('data-value');
        if (dataValue) {
          return dataValue.trim();
        }
        
        const ariaLabel = option.getAttribute('aria-label');
        if (ariaLabel) {
          return ariaLabel.trim();
        }
        
        const textContent = option.textContent;
        if (textContent) {
          return textContent.trim();
        }
        
        return null;
      }).filter(size => size && size.length > 0);
      
      console.log(`Found ${comboSizes.length} combo sizes:`, comboSizes);
      return comboSizes;
      
    } catch (error) {
      console.error('Error extracting combo sizes:', error);
      return [];
    }
  }

  /**
   * Поиск связанного контейнера size2 на том же уровне DOM
   */
  findRelatedSizeContainer(sizeContainer1) {
    try {
      const parentElement = sizeContainer1.closest('.sc-s4utl4-0, .size-selection, .product-variants, .variant-selector, [class*="size"], [class*="variant"]');
      
      if (!parentElement) {
        console.log('No parent element found for size1 container');
        return null;
      }
      
      const sizeContainer2 = parentElement.querySelector(this.config.selectors.boxSelectorSize2);
      
      if (sizeContainer2) {
        console.log('Found related size2 container in the same parent element');
        return sizeContainer2;
      }
      
      console.log('No related size2 container found in the same parent element');
      return null;
    } catch (error) {
      console.error('Error finding related size container:', error);
      return null;
    }
  }

  /**
   * Извлечение комбинаций размеров для двухразмерных продуктов
   */
  async extractSizeCombinations(sizeContainer1, sizeContainer2) {
    try {
      console.log('Starting VS size combination extraction...');
      
      const size1Type = this.getSizeTypeLabel(sizeContainer1);
      const size2Type = this.getSizeTypeLabel(sizeContainer2);
      
      console.log(`Size types detected: ${size1Type} and ${size2Type}`);
      
      const size1Options = Array.from(sizeContainer1.querySelectorAll('[role="radio"]'));
      const combinations = {};
      
      console.log(`Found ${size1Options.length} size1 options to iterate through`);
      
      // Сохраняем оригинальные выборы для восстановления
      const originallySelected1 = sizeContainer1.querySelector('[role="radio"][aria-checked="true"]');
      const originallySelected2 = sizeContainer2.querySelector('[role="radio"][aria-checked="true"]');
      
      // Итерируемся по каждой опции size1
      for (let i = 0; i < size1Options.length; i++) {
        const size1Option = size1Options[i];
        const size1Value = size1Option.getAttribute('data-value');
        
        if (size1Option.getAttribute('aria-disabled') === 'true') {
          console.log(`Skipping disabled size1 option: ${size1Value}`);
          continue;
        }
        
        console.log(`Clicking size1 option: ${size1Value}`);
        
        size1Option.click();
        await this.wait(200);
        
        const availableSize2Options = Array.from(sizeContainer2.querySelectorAll('[role="radio"][aria-disabled="false"]'));
        const size2Values = availableSize2Options.map(opt => opt.getAttribute('data-value'));
        
        console.log(`Size1 ${size1Value} -> Available size2 options:`, size2Values);
        
        if (size2Values.length > 0) {
          combinations[size1Value] = size2Values;
        }
      }
      
      // Восстанавливаем оригинальные выборы
      try {
        if (originallySelected1) {
          originallySelected1.click();
          await this.wait(100);
        }
        if (originallySelected2) {
          originallySelected2.click();
          await this.wait(100);
        }
      } catch (e) {
        // Игнорируем ошибки восстановления
      }
      
      console.log('Final combinations extracted:', combinations);
      
      return {
        success: true,
        data: {
          size1_type: size1Type,
          size2_type: size2Type,
          combinations: combinations
        }
      };
      
    } catch (error) {
      console.error('Error extracting VS size combinations:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Получение типа размера из контейнера
   */
  getSizeTypeLabel(sizeContainer) {
    try {
      const parent = sizeContainer.closest('.sc-s4utl4-0');
      if (parent) {
        const labelElement = parent.querySelector('[data-testid]');
        if (labelElement) {
          return labelElement.getAttribute('data-testid');
        }
      }
      
      const ariaLabel = sizeContainer.getAttribute('aria-label');
      if (ariaLabel) {
        return ariaLabel;
      }
      
      const testId = sizeContainer.getAttribute('data-testid');
      if (testId) {
        return testId.replace('BoxSelector-', '');
      }
      
      return 'Unknown';
    } catch (e) {
      return 'Unknown';
    }
  }
}

// Экспортируем для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
  module.exports = VictoriasSecretParser;
}