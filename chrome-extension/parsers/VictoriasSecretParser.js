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
   * Извлечение SKU из JSON-LD с fallback на генерацию из genericId + colorCode
   */
  extractSku(jsonData) {
    console.log('VS extractSku called with jsonData:', jsonData);
    
    // Приоритет 1: Пытаемся получить SKU из JSON-LD
    if (jsonData && jsonData.sku) {
      console.log('VS extractSku from JSON-LD:', jsonData.sku);
      return jsonData.sku;
    }
    
    console.log('VS extractSku: No SKU in JSON-LD, trying fallback generation...');
    
    // Приоритет 2: Fallback - генерируем SKU из generic ID + color code
    const generatedSku = this.generateSkuFromGenericIdAndColor();
    if (generatedSku) {
      console.log('VS extractSku: Generated SKU from generic ID + color:', generatedSku);
      return generatedSku;
    }
    
    console.log('VS extractSku: No SKU found in any method');
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
          // Улучшаем качество изображения перед добавлением в массив
          const enhancedUrl = this.enhanceImageQuality(absoluteUrl);
          imageUrls.push(enhancedUrl);
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
    if (!element) return null;
    
    // Use only span p selector without fallback logic
    const compositionText = element.querySelector('span p');
    if (compositionText) {
      return compositionText.textContent?.trim() || null;
    }
    
    return null;
  }

  /**
   * Генерация SKU из generic ID и color code (fallback метод)
   */
  generateSkuFromGenericIdAndColor() {
    console.log('VS generateSkuFromGenericIdAndColor: Starting SKU generation from generic ID + color...');
    
    try {
      // Извлекаем generic ID из data-testid="ProductInfo-genericId"
      const genericIdElement = document.querySelector(this.config.selectors.genericId);
      if (!genericIdElement) {
        console.log('VS generateSkuFromGenericIdAndColor: No generic ID element found');
        return null;
      }
      
      const genericId = genericIdElement.textContent?.trim();
      if (!genericId) {
        console.log('VS generateSkuFromGenericIdAndColor: Generic ID element is empty');
        return null;
      }
      
      console.log(`VS generateSkuFromGenericIdAndColor: Found generic ID: ${genericId}`);
      
      // Извлекаем color code из выбранного color radio div data-value attribute
      const colorCode = this.extractColorCodeFromSelection();
      if (!colorCode) {
        console.log('VS generateSkuFromGenericIdAndColor: No color code found');
        return null;
      }
      
      console.log(`VS generateSkuFromGenericIdAndColor: Found color code: ${colorCode}`);
      
      // Создаем combined SKU в формате {id}-{color_code}
      const generatedSku = `${genericId}-${colorCode}`;
      console.log(`VS generateSkuFromGenericIdAndColor: Generated SKU: ${generatedSku}`);
      
      return generatedSku;
      
    } catch (error) {
      console.error('VS generateSkuFromGenericIdAndColor: Error generating SKU:', error);
      return null;
    }
  }

  /**
   * Извлечение color code из выбранного color radio элемента
   */
  extractColorCodeFromSelection() {
    console.log('VS extractColorCodeFromSelection: Looking for selected color...');
    
    try {
      // Ищем все color radio элементы
      const colorRadioElements = document.querySelectorAll('input[type="radio"][name*="color"], div[role="radio"][data-value]');
      
      for (const element of colorRadioElements) {
        // Проверяем input radio элементы
        if (element.tagName === 'INPUT' && element.checked) {
          const dataValue = element.getAttribute('data-value');
          if (dataValue) {
            console.log(`VS extractColorCodeFromSelection: Found selected input color code: ${dataValue}`);
            return dataValue;
          }
        }
        
        // Проверяем div[role="radio"] элементы (альтернативный подход)
        if (element.tagName === 'DIV' && element.getAttribute('aria-checked') === 'true') {
          const dataValue = element.getAttribute('data-value');
          if (dataValue) {
            console.log(`VS extractColorCodeFromSelection: Found selected div color code: ${dataValue}`);
            return dataValue;
          }
        }
      }
      
      // Fallback: ищем по визуальным признакам выбранного цвета
      const selectedColorElements = document.querySelectorAll('[class*="selected"], [class*="active"], [aria-selected="true"]');
      for (const element of selectedColorElements) {
        const dataValue = element.getAttribute('data-value');
        if (dataValue && dataValue.match(/^\d+$/)) { // Проверяем что это числовой код
          console.log(`VS extractColorCodeFromSelection: Found color code via visual selection: ${dataValue}`);
          return dataValue;
        }
      }
      
      // Дополнительный fallback: ищем в родительских элементах с color-related селекторами
      const colorContainers = document.querySelectorAll('[class*="color"], [data-testid*="color"], [id*="color"]');
      for (const container of colorContainers) {
        const checkedElement = container.querySelector('[checked], [aria-checked="true"], [class*="selected"]');
        if (checkedElement) {
          const dataValue = checkedElement.getAttribute('data-value');
          if (dataValue) {
            console.log(`VS extractColorCodeFromSelection: Found color code in container: ${dataValue}`);
            return dataValue;
          }
        }
      }
      
      console.log('VS extractColorCodeFromSelection: No color code found in any method');
      return null;
      
    } catch (error) {
      console.error('VS extractColorCodeFromSelection: Error extracting color code:', error);
      return null;
    }
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
      console.log('Static size container found:', !!staticSizeContainer);
      if (staticSizeContainer) {
        console.log('Static size container HTML:', staticSizeContainer.outerHTML);
      }
      
      // Находим BoxSelector-size1 в общем primaryProduct
      let sizeContainer1 = primaryProduct.querySelector(this.config.selectors.boxSelectorSize1);
      console.log('BoxSelector-size1 found in PrimaryProduct:', !!sizeContainer1);
      
      // ВАЖНО: Проверяем, есть ли BoxSelector-size1 в том же родительском контейнере, что и Size
      let isDynamicSizeNearStatic = false;
      if (staticSizeContainer && sizeContainer1) {
        // Ищем общий родительский элемент для Size и BoxSelector-size1
        const staticParent = staticSizeContainer.parentElement;
        const dynamicParent = sizeContainer1.parentElement;
        
        // Проверяем, находятся ли они в одном родителе или близко друг к другу
        isDynamicSizeNearStatic = staticParent === dynamicParent || 
                                  staticParent.contains(sizeContainer1) || 
                                  dynamicParent.contains(staticSizeContainer);
        
        console.log('Static and dynamic containers are related:', isDynamicSizeNearStatic);
        if (isDynamicSizeNearStatic) {
          console.log('Static parent:', staticParent?.className);
          console.log('Dynamic parent:', dynamicParent?.className);
        }
      }
      
      // ОТЛАДКА: Детальная проверка условий
      console.log('=== SIZE CONTAINER ANALYSIS ===');
      console.log('staticSizeContainer exists:', !!staticSizeContainer);
      console.log('sizeContainer1 exists:', !!sizeContainer1);
      console.log('isDynamicSizeNearStatic:', isDynamicSizeNearStatic);
      
      // ИСПРАВЛЕННАЯ ЛОГИКА: используем статический размер только если нет динамических селекторов поблизости
      if (staticSizeContainer && (!sizeContainer1 || !isDynamicSizeNearStatic)) {
        console.log('✅ CONDITION MET: Found static size container without nearby dynamic selectors, extracting text size...');
        const staticSize = this.extractStaticSize(staticSizeContainer);
        console.log('Static size extraction result:', staticSize);
        if (staticSize) {
          console.log('Static size extracted successfully:', staticSize);
          return [staticSize];
        } else {
          console.log('❌ Static size extraction failed');
        }
      } else if (staticSizeContainer && sizeContainer1 && isDynamicSizeNearStatic) {
        console.log('⚠️ Found static size container BUT there are dynamic selectors nearby - using dynamic logic');
      } else if (!staticSizeContainer && sizeContainer1) {
        console.log('ℹ️ No static size container, but found dynamic selectors');
      } else if (!staticSizeContainer && !sizeContainer1) {
        console.log('❌ No size containers found at all');
      }
      
      // Проверяем комбинированные размеры (BoxSelector-comboSize)
      const comboSizeContainer = primaryProduct.querySelector(this.config.selectors.boxSelectorCombo);
      console.log('BoxSelector-comboSize found:', !!comboSizeContainer);
      
      if (comboSizeContainer) {
        console.log('Found BoxSelector-comboSize container, extracting combo sizes...');
        const comboSizes = this.extractComboSizes(comboSizeContainer);
        console.log('Combo sizes result:', comboSizes);
        if (comboSizes.length > 0) {
          console.log('Combo sizes extracted successfully:', comboSizes);
          return comboSizes;
        } else {
          console.log('Combo sizes extraction returned empty array');
        }
      }

      if (!sizeContainer1) {
        console.log('No BoxSelector-size1 found within PrimaryProduct');
        
        // ОТЛАДКА: Если нет динамических селекторов, но есть статический контейнер
        if (staticSizeContainer) {
          console.log('=== DEBUGGING: Have static container but no dynamic selectors ===');
          console.log('Trying to extract static size manually...');
          const manualStaticSize = this.extractStaticSize(staticSizeContainer);
          console.log('Manual static size result:', manualStaticSize);
          
          if (manualStaticSize) {
            console.log('Manual extraction successful, returning:', [manualStaticSize]);
            return [manualStaticSize];
          } else {
            console.log('Manual extraction also failed');
          }
        }
        
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
        console.log('No valid size options found in dynamic selectors');
        
        // FALLBACK: Если динамические селекторы не сработали, попробуем статический размер
        if (staticSizeContainer) {
          console.log('=== FALLBACK: Trying static size extraction ===');
          const fallbackStaticSize = this.extractStaticSize(staticSizeContainer);
          console.log('Fallback static size result:', fallbackStaticSize);
          
          if (fallbackStaticSize) {
            console.log('Fallback successful, returning static size:', [fallbackStaticSize]);
            return [fallbackStaticSize];
          } else {
            console.log('Fallback also failed');
          }
        }
        
        console.log('All extraction methods failed');
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
      console.log('=== EXTRACTING STATIC SIZE ===');
      console.log('Container HTML:', staticSizeContainer.outerHTML);
      
      // Получаем полный текст контейнера для анализа
      const fullText = staticSizeContainer.textContent.trim();
      console.log(`Full container text: "${fullText}"`);
      
      // Сначала пробуем найти все span элементы
      const spans = staticSizeContainer.querySelectorAll('span');
      console.log(`Found ${spans.length} span elements in static size container`);
      
      // Собираем все тексты из spans для анализа
      const spanTexts = [];
      for (let i = 0; i < spans.length; i++) {
        const span = spans[i];
        const text = span.textContent.trim();
        spanTexts.push(text);
        console.log(`Span ${i}: "${text}"`);
      }
      
      console.log('All span texts:', spanTexts);
      
      // Стратегия 1: Ищем span, который содержит размер (не "Size")
      for (let i = 0; i < spans.length; i++) {
        const span = spans[i];
        const text = span.textContent.trim();
        
        // Пропускаем пустые и служебные тексты
        if (!text || text === 'Size' || text === 'Размер' || text === 'Size ') {
          console.log(`Strategy 1: Skipping span ${i} with text: "${text}"`);
          continue;
        }
        
        // Если это не начинается с "Size", то вероятно это размер
        if (!text.toLowerCase().startsWith('size')) {
          console.log(`Strategy 1: Found potential size in span ${i}: "${text}"`);
          return text;
        }
        
        // Проверяем, что это паттерн "Size Something"
        if (text.toLowerCase().startsWith('size ') && text.length > 5) {
          const sizeValue = text.substring(5).trim();
          if (sizeValue) {
            console.log(`Strategy 1: Found size after "Size " in span ${i}: "${sizeValue}"`);
            return sizeValue;
          }
        }
      }
      
      // Стратегия 2: Анализируем полный текст с регулярными выражениями
      console.log('Strategy 1 failed, trying strategy 2: regex on full text');
      
      // Ищем паттерн "Size [размер]"
      const sizeMatch = fullText.match(/Size\s+(.+)/i);
      if (sizeMatch && sizeMatch[1]) {
        const extractedSize = sizeMatch[1].trim();
        console.log(`Strategy 2: Extracted size from full text: "${extractedSize}"`);
        return extractedSize;
      }
      
      // Стратегия 3: Если есть два span'а, второй может быть размером
      if (spans.length === 2) {
        const firstText = spans[0].textContent.trim();
        const secondText = spans[1].textContent.trim();
        
        if ((firstText === 'Size' || firstText === 'Size ') && secondText && secondText !== 'Size') {
          console.log(`Strategy 3: Found size in second span: "${secondText}"`);
          return secondText;
        }
      }
      
      // Стратегия 4: Ищем любой span с содержимым, не равным "Size"
      console.log('Strategy 3 failed, trying strategy 4: any non-Size span');
      for (let i = 0; i < spans.length; i++) {
        const text = spans[i].textContent.trim();
        if (text && text !== 'Size' && text !== 'Size ' && text !== 'Размер') {
          console.log(`Strategy 4: Found non-Size text in span ${i}: "${text}"`);
          return text;
        }
      }
      
      console.log('=== ALL STRATEGIES FAILED ===');
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