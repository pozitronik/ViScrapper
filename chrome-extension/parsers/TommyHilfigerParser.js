/**
 * Simplified Tommy Hilfiger Parser - NO OBSERVERS
 * Focus on core data extraction functionality
 * Observer logic removed to debug size extraction issues
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
        colorsList: '[data-display-id="colorCode"]',
        sizesList: '#sizessize',
        jsonLdScript: 'script[type="application/ld+json"]'
      }
    });
    
    // SELF-INITIALIZATION: Setup color observer immediately when parser is created
    console.log('TH Parser: Self-initializing color change observer...');
    this.initializeColorObserver();
  }
  
  /**
   * Self-initialization of color observer - called from constructor
   */
  initializeColorObserver() {
    // Try immediate setup
    const immediateResult = this.setupColorChangeObserver();
    
    if (immediateResult.success && immediateResult.listeners > 0) {
      console.log(`TH Parser: Color observer self-initialized: ${immediateResult.listeners} listeners`);
    } else {
      // Fallback: DOM might not be ready yet
      console.log('TH Parser: DOM not ready, scheduling delayed color observer setup...');
      
      setTimeout(() => {
        const delayedResult = this.setupColorChangeObserver();
        if (delayedResult.success) {
          console.log(`TH Parser: Color observer setup successful after delay: ${delayedResult.listeners} listeners`);
        } else {
          console.warn('TH Parser: Color observer setup failed even after delay');
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
    console.log('Checking TH page validity, URL:', url);
    
    if (!url.includes(this.config.domain)) {
      console.log('Not a Tommy Hilfiger page');
      return false;
    }
    
    // Приоритет 1: Проверяем JSON-LD на наличие Product
    const jsonData = this.getJsonLdData();
    if (jsonData && jsonData['@type'] === 'Product') {
      console.log('Valid TH product page: JSON-LD Product found');
      return true;
    }
    
    // Приоритет 2: Проверяем основные элементы продукта
    const productName = document.querySelector(this.config.selectors.productName);
    const buyBox = document.querySelector(this.config.selectors.buyBox);
    
    console.log('ProductName element:', productName);
    console.log('BuyBox element:', buyBox);
    
    if (!productName || !buyBox) {
      console.log('Missing core product elements');
      return false;
    }
    
    console.log('Page is valid TH product page');
    return true;
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
      console.log('TH extractSku: No base product code found, trying fallbacks');
      
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
        console.log('TH extractSelectedColorCode: Found selected color in main colorsList');
      }
    }
    
    // Вариант 2: Grouped-by-price структура - ищем во всех видимых colorGroup
    if (!selectedColor) {
      const colorGroups = document.querySelectorAll('.colors-variant-list:not(.d-none)');
      console.log(`TH extractSelectedColorCode: Searching in ${colorGroups.length} visible color groups`);
      
      for (const group of colorGroups) {
        selectedColor = group.querySelector('input[type="radio"]:checked, input[type="radio"][aria-checked="true"]');
        if (selectedColor) {
          console.log('TH extractSelectedColorCode: Found selected color in color group:', group.className);
          break;
        }
      }
    }
    
    // Вариант 3: Поиск по всему документу как fallback
    if (!selectedColor) {
      selectedColor = document.querySelector('input[type="radio"].variant-colorCode:checked, input[type="radio"].variant-colorCode[aria-checked="true"]');
      if (selectedColor) {
        console.log('TH extractSelectedColorCode: Found selected color via fallback selector');
      }
    }
    
    if (!selectedColor) {
      console.log('TH extractSelectedColorCode: No selected color found, looking for first available color');
      
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
        console.log('TH extractSelectedColorCode: Using first color as fallback');
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
    console.log('TH extractImages: Starting image extraction...');
    
    // Приоритет 1: Извлекаем из DOM (актуальные изображения для текущего цвета)
    const domImages = await this.extractImagesFromDOM();
    if (domImages.length > 0) {
      console.log(`TH extractImages: Found ${domImages.length} images from DOM`);
      return domImages;
    }
    
    // Приоритет 2: Fallback к JSON-LD (может быть устаревшим)
    console.log('TH extractImages: No DOM images found, falling back to JSON-LD...');
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
    
    console.log(`TH extractImages: Found ${imageUrls.length} images from JSON-LD fallback`);
    return imageUrls;
  }

  /**
   * Извлечение изображений из DOM (актуальные данные)
   * Парсит структуру: [data-comp="ProductImage"] > .product-image.swiper-slide > img
   */
  async extractImagesFromDOM() {
    try {
      console.log('TH extractImagesFromDOM: Starting DOM extraction...');
      
      // Находим основной контейнер с изображениями
      const productImageContainer = document.querySelector('[data-comp="ProductImage"]');
      if (!productImageContainer) {
        console.log('TH extractImagesFromDOM: ProductImage container not found');
        return [];
      }
      
      // Находим все слайды с изображениями
      const imageSlides = productImageContainer.querySelectorAll('.product-image.swiper-slide');
      if (imageSlides.length === 0) {
        console.log('TH extractImagesFromDOM: No image slides found');
        return [];
      }
      
      console.log(`TH extractImagesFromDOM: Found ${imageSlides.length} image slides`);
      
      const imageUrls = [];
      
      imageSlides.forEach((slide, index) => {
        const img = slide.querySelector('img');
        if (!img) {
          console.log(`TH extractImagesFromDOM: No img tag found in slide ${index}`);
          return;
        }
        
        let imageUrl = null;
        
        // Приоритет 1: Загруженное изображение (src атрибут)
        const src = img.getAttribute('src');
        if (src && src.startsWith('http') && !src.includes('data:image')) {
          imageUrl = src;
          console.log(`TH extractImagesFromDOM: Found loaded image in slide ${index}: ${imageUrl}`);
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
                  console.log(`TH extractImagesFromDOM: Found lazy image in slide ${index}: ${imageUrl}`);
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
          console.log(`TH extractImagesFromDOM: Added enhanced image: ${enhancedUrl}`);
        } else {
          console.log(`TH extractImagesFromDOM: No valid image URL found in slide ${index}`);
        }
      });
      
      console.log(`TH extractImagesFromDOM: Extracted ${imageUrls.length} images from DOM`);
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
        console.log('TH extractColor: Found selected color in main colorsList');
      }
    }
    
    // Вариант 2: Grouped-by-price структура - ищем во всех видимых colorGroup
    if (!selectedColor) {
      const colorGroups = document.querySelectorAll('.colors-variant-list:not(.d-none)');
      for (const group of colorGroups) {
        selectedColor = group.querySelector('input[type="radio"]:checked, input[type="radio"][aria-checked="true"]');
        if (selectedColor) {
          console.log('TH extractColor: Found selected color in color group:', group.className);
          break;
        }
      }
    }
    
    // Вариант 3: Поиск по всему документу как fallback
    if (!selectedColor) {
      selectedColor = document.querySelector('input[type="radio"].variant-colorCode:checked, input[type="radio"].variant-colorCode[aria-checked="true"]');
      if (selectedColor) {
        console.log('TH extractColor: Found selected color via fallback selector');
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
      console.log('TH extractSizes: Starting simplified size extraction...');
      
      // Look for size containers using .variant-list approach
      const sizeContainers = document.querySelectorAll('.variant-list[data-display-value]:not([data-display-id="colorCode"])');
      console.log(`TH extractSizes: Found ${sizeContainers.length} size containers with .variant-list`);
      
      if (sizeContainers.length >= 2) {
        console.log('TH extractSizes: Detected two-dimensional size system (e.g., Waist × Length)');
        return await this.extractSizeCombinations(sizeContainers[0], sizeContainers[1]);
      } else if (sizeContainers.length === 1) {
        console.log('TH extractSizes: Detected one-dimensional size system');
        return await this.extractSimpleSizes(sizeContainers[0]);
      }
      
      // Fallback: try old method
      console.log('TH extractSizes: No .variant-list containers found, trying fallback methods');
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
        console.log(`TH extractSimpleSizes: Found ${sizeInputs.length} size radio inputs`);
        
        sizeInputs.forEach(input => {
          const inputId = input.getAttribute('id');
          const label = document.querySelector(`label[for="${inputId}"]`);
          
          // Проверяем, что размер не отключен (не имеет класс size-disabled)
          if (label && label.classList.contains('size-disabled')) {
            console.log(`TH extractSimpleSizes: Skipping disabled size for input ${inputId}`);
            return;
          }
          
          if (input.classList.contains('disabled') || input.classList.contains('oos-variant')) {
            console.log(`TH extractSimpleSizes: Skipping disabled input ${inputId}`);
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
          console.log(`TH extractSimpleSizes: Found ${availableSizes.length} simple sizes:`, availableSizes);
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
            console.log(`TH extractSimpleSizes: Found size from header:`, sizeText);
            availableSizes.push(sizeText);
            break;
          }
        }
      }
      
      if (availableSizes.length === 0) {
        const oneSize = document.querySelector('[data-testid="size-onesize"], .size-one-size');
        if (oneSize) {
          console.log('TH extractSimpleSizes: Found ONE SIZE indicator');
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
      console.log('TH extractSizeCombinations: Starting SIMPLIFIED two-dimensional size extraction...');
      
      // Get dimension types
      const dimension1Type = this.getDimensionType(dimension1Container);
      const dimension2Type = this.getDimensionType(dimension2Container);
      
      console.log(`TH extractSizeCombinations: Dimensions detected - ${dimension1Type} × ${dimension2Type}`);
      
      const dimension1Options = Array.from(dimension1Container.querySelectorAll('input[type="radio"].variant-item'));
      const combinations = {};
      
      console.log(`TH extractSizeCombinations: Found ${dimension1Options.length} ${dimension1Type} options to test`);
      
      // Save original selections for restoration (simplified)
      const originalDim1 = dimension1Container.querySelector('input[type="radio"][aria-checked="true"]');
      const originalDim2 = dimension2Container.querySelector('input[type="radio"][aria-checked="true"]');
      
      console.log(`TH extractSizeCombinations: Original selections - ${dimension1Type}: ${originalDim1?.id || 'none'}, ${dimension2Type}: ${originalDim2?.id || 'none'}`);
      
      // Test each dimension1 option
      for (let i = 0; i < dimension1Options.length; i++) {
        const dim1Option = dimension1Options[i];
        const dim1Value = dim1Option.getAttribute('data-attr-value');
        
        // Skip obviously disabled options
        if (dim1Option.classList.contains('disabled') || dim1Option.classList.contains('oos-variant')) {
          console.log(`TH extractSizeCombinations: Skipping disabled ${dimension1Type} option: ${dim1Value}`);
          continue;
        }
        
        console.log(`TH extractSizeCombinations: Testing ${dimension1Type} option: ${dim1Value} (${i + 1}/${dimension1Options.length})`);
        
        // Click dimension1 option (try clicking the label instead of the input for better results)
        const dim1Label = document.querySelector(`label[for="${dim1Option.id}"]`);
        if (dim1Label) {
          console.log(`TH extractSizeCombinations: Clicking ${dimension1Type} label for ${dim1Value}`);
          dim1Label.click();
        } else {
          console.log(`TH extractSizeCombinations: No label found, clicking ${dimension1Type} input for ${dim1Value}`);
          dim1Option.click();
        }
        
        // Wait for DOM to update - using conservative timing
        console.log('TH extractSizeCombinations: Waiting for DOM update after dimension1 click...');
        await this.wait(2000); // Even longer wait to ensure DOM fully updates
        
        // Verify the dimension1 selection was successful
        const selectedDim1 = dimension1Container.querySelector('input[type="radio"]:checked, input[type="radio"][aria-checked="true"]');
        const selectedDim1Value = selectedDim1?.getAttribute('data-attr-value') || 'none';
        console.log(`TH extractSizeCombinations: After click, ${dimension1Type} selection is: ${selectedDim1Value}`);
        
        if (selectedDim1Value !== dim1Value) {
          console.log(`TH extractSizeCombinations: WARNING - Expected ${dim1Value} but ${selectedDim1Value} is selected`);
        }
        
        // Get available dimension2 options after dimension1 selection
        const dimension2Options = Array.from(dimension2Container.querySelectorAll('input[type="radio"].variant-item'));
        const availableDim2Values = [];
        
        console.log(`TH extractSizeCombinations: Testing ${dimension2Options.length} ${dimension2Type} options for ${dimension1Type} ${dim1Value}`);
        
        // CORRECT APPROACH: Observe label.size-disabled changes in second radiogroup
        console.log(`TH extractSizeCombinations: After selecting ${dimension1Type} ${dim1Value}, observing ${dimension2Type} label states...`);
        
        // DEBUG: First, let's see what's happening with all labels in the second radiogroup
        console.log(`TH extractSizeCombinations: === DEBUGGING ${dimension2Type} LABELS STATE ===`);
        const allDim2Labels = dimension2Container.querySelectorAll('label');
        console.log(`TH extractSizeCombinations: Found ${allDim2Labels.length} labels in ${dimension2Type} container`);
        
        allDim2Labels.forEach((label, index) => {
          const forAttr = label.getAttribute('for');
          const hasDisabled = label.classList.contains('size-disabled');
          const hasDisabled2 = label.classList.contains('disabled');
          const labelText = label.textContent?.trim();
          const allClasses = Array.from(label.classList).join(', ');
          
          console.log(`TH extractSizeCombinations: Label ${index}: for="${forAttr}", text="${labelText}", classes="${allClasses}", size-disabled=${hasDisabled}, disabled=${hasDisabled2}`);
        });
        
        // Tommy Hilfiger adds .size-disabled class to labels of unavailable options in the second radiogroup
        // We just need to observe which labels DON'T have this class
        
        for (let j = 0; j < dimension2Options.length; j++) {
          const dim2Option = dimension2Options[j];
          const dim2Value = dim2Option.getAttribute('data-attr-value');
          
          if (!dim2Value) {
            console.log(`TH extractSizeCombinations: Skipping ${dimension2Type} option without value at index ${j}`);
            continue;
          }
          
          // Find the label for this radio input
          const dim2Label = document.querySelector(`label[for="${dim2Option.id}"]`);
          
          if (!dim2Label) {
            console.log(`TH extractSizeCombinations: No label found for ${dimension2Type} ${dim2Value}, skipping`);
            continue;
          }
          
          // Check multiple possible disabled indicators on the label
          const hasDisabledClass = dim2Label.classList.contains('disabled');
          const hasSizeDisabledClass = dim2Label.classList.contains('size-disabled');
          const hasOosClass = dim2Label.classList.contains('oos');
          const isLabelDisabled = hasDisabledClass || hasSizeDisabledClass || hasOosClass;
          
          console.log(`TH extractSizeCombinations: Checking ${dimension2Type} ${dim2Value}:`);
          console.log(`  - label.disabled: ${hasDisabledClass}`);
          console.log(`  - label.size-disabled: ${hasSizeDisabledClass}`);
          console.log(`  - label.oos: ${hasOosClass}`);
          console.log(`  - final assessment: ${isLabelDisabled ? 'DISABLED' : 'AVAILABLE'}`);
          
          if (!isLabelDisabled) {
            // Label is not disabled - option is available for this waist size
            availableDim2Values.push(dim2Value);
            console.log(`TH extractSizeCombinations: ✓ ${dimension2Type} ${dim2Value} is AVAILABLE for ${dimension1Type} ${dim1Value}`);
          } else {
            console.log(`TH extractSizeCombinations: ✗ ${dimension2Type} ${dim2Value} is DISABLED for ${dimension1Type} ${dim1Value}`);
          }
        }
        
        console.log(`TH extractSizeCombinations: ${dimension1Type} ${dim1Value} → Available ${dimension2Type}:`, availableDim2Values);
        
        if (availableDim2Values.length > 0) {
          combinations[dim1Value] = availableDim2Values;
        } else {
          console.log(`TH extractSizeCombinations: No available ${dimension2Type} options for ${dimension1Type} ${dim1Value}`);
        }
      }
      
      // Simple restoration - just restore original selections if they existed
      console.log('TH extractSizeCombinations: Restoring original selections...');
      try {
        if (originalDim1 && !originalDim1.checked) {
          console.log(`TH extractSizeCombinations: Restoring ${dimension1Type} to: ${originalDim1.id}`);
          originalDim1.click();
          await this.wait(200);
        }
        if (originalDim2 && !originalDim2.checked) {
          console.log(`TH extractSizeCombinations: Restoring ${dimension2Type} to: ${originalDim2.id}`);
          originalDim2.click();
          await this.wait(200);
        }
        console.log('TH extractSizeCombinations: Restoration completed');
      } catch (e) {
        console.log('TH extractSizeCombinations: Error during restoration (non-critical):', e);
      }
      
      console.log('TH extractSizeCombinations: Final combinations extracted:', combinations);
      
      return {
        dimension1_type: dimension1Type,
        dimension2_type: dimension2Type,
        combinations: combinations
      };
      
    } catch (error) {
      console.error('Error extracting TH size combinations:', error);
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
      console.error('Error getting dimension type:', error);
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
      if (firstColorInput) {
        console.log('TH extractUniqueProductId: Found color input in main colorsList');
      }
    }
    
    // Вариант 2: Grouped-by-price структура - ищем во всех colorGroup
    if (!firstColorInput) {
      const colorGroups = document.querySelectorAll('.colors-variant-list:not(.d-none)');
      console.log(`TH extractUniqueProductId: Found ${colorGroups.length} visible color groups`);
      
      for (const group of colorGroups) {
        const input = group.querySelector('input[type="radio"]');
        if (input) {
          firstColorInput = input;
          console.log('TH extractUniqueProductId: Found color input in color group:', group.className);
          break;
        }
      }
    }
    
    // Вариант 3: Поиск по всему документу как fallback
    if (!firstColorInput) {
      firstColorInput = document.querySelector('input[type="radio"].variant-colorCode');
      if (firstColorInput) {
        console.log('TH extractUniqueProductId: Found color input via fallback selector');
      }
    }
    
    if (!firstColorInput) {
      console.log('TH extractUniqueProductId: No color radio inputs found');
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
    
    console.log(`TH extractUniqueProductId: Extracted (fallback) "${uniqueProductId}" from "${fullPart}" using first-part-only rule (consistent with CK)`);
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
      console.log('TH extractColorCodeFromId: ID format does not match expected pattern:', inputId);
      return null;
    }
    
    const colorCode = match[1]; // DW5
    console.log(`TH extractColorCodeFromId: Extracted color code "${colorCode}" from "${inputId}"`);
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
      console.log('TH generateColorSpecificSku: No color code, returning base product code');
      return baseProductCode;
    }

    const colorSpecificSku = `${baseProductCode}-${colorCode}`;
    console.log(`TH generateColorSpecificSku: Generated ${colorSpecificSku} from base ${baseProductCode} and color ${colorCode}`);
    
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
      console.log('TH setupColorChangeObserver: Setting up color change detection...');
      
      // Очистка предыдущих слушателей если есть
      if (this.colorListeners && this.colorListeners.length > 0) {
        console.log(`TH setupColorChangeObserver: Cleaning up ${this.colorListeners.length} existing listeners first...`);
        this.cleanup();
      }
      
      // Сохраняем текущий цвет для сравнения
      this.currentColorCode = this.extractSelectedColorCode();
      this.colorListeners = []; // Массив для очистки
      
      console.log(`TH setupColorChangeObserver: Initial color code: ${this.currentColorCode}`);
      
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
      
      console.log(`TH setupColorChangeObserver: Found ${colorInputs.length} color inputs and ${colorLabels.length} color labels`);
      
      if (colorInputs.length === 0) {
        console.warn('TH setupColorChangeObserver: No color inputs found, setup failed');
        return { success: false, error: 'No color inputs found', listeners: 0 };
      }
      
      // Устанавливаем слушатели на radio inputs
      colorInputs.forEach((input, index) => {
        const handler = this.handleColorChange.bind(this);
        input.addEventListener('change', handler);
        this.colorListeners.push({ element: input, type: 'change', handler });
        console.log(`TH setupColorChangeObserver: Added change listener to color input ${index}: ${input.id}`);
      });
      
      // Устанавливаем слушатели на labels (иногда более надежно)
      colorLabels.forEach((label, index) => {
        const handler = this.handleColorLabelClick.bind(this);
        label.addEventListener('click', handler);
        this.colorListeners.push({ element: label, type: 'click', handler });
        console.log(`TH setupColorChangeObserver: Added click listener to color label ${index}: ${label.getAttribute('for')}`);
      });
      
      // Автоматическая очистка при уходе со страницы
      const cleanupHandler = this.cleanup.bind(this);
      window.addEventListener('beforeunload', cleanupHandler);
      document.addEventListener('visibilitychange', () => {
        if (document.hidden) this.cleanup();
      });
      
      console.log('TH setupColorChangeObserver: Color change observer setup complete');
      return { success: true, listeners: this.colorListeners.length };
      
    } catch (error) {
      console.error('TH setupColorChangeObserver: Error setting up color observer:', error);
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
      console.log('TH handleColorChange: Color input change detected');
      
      // Небольшая задержка для стабилизации DOM
      await this.wait(100);
      
      const newColorCode = this.extractSelectedColorCode();
      console.log(`TH handleColorChange: New color code detected: ${newColorCode}`);
      
      // Проверяем, действительно ли цвет изменился
      if (newColorCode && newColorCode !== this.currentColorCode) {
        console.log(`TH handleColorChange: Color actually changed from ${this.currentColorCode} to ${newColorCode}`);
        
        this.currentColorCode = newColorCode;
        await this.sendColorUpdateMessage();
      } else {
        console.log('TH handleColorChange: Color did not actually change, ignoring');
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
   * Отправка сообщения об изменении цвета - триггерит ПОЛНОЕ обновление данных
   * Поскольку смена цвета на TH = совершенно новый продукт (SKU, изображения, размеры)
   */
  async sendColorUpdateMessage() {
    try {
      console.log('TH sendColorUpdateMessage: Color changed - triggering FULL data refresh...');
      
      // Для Tommy Hilfiger смена цвета = новый продукт, нужно полное обновление
      // Используем существующую систему SPA refresh из viparser-events.js
      chrome.runtime.sendMessage({
        action: 'spaPanelRefresh',
        source: 'tommy-hilfiger-color-change',
        reason: 'Color changed - new product variant with different SKU/images/sizes'
      });
      
      console.log('TH sendColorUpdateMessage: Full data refresh message sent');
      
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
   * Извлечение всех вариантов (цвет + размеры) для создания отдельных продуктов
   * Генерирует уникальные SKU в формате: {baseProductCode}-{colorCode}
   * Каждый цвет = отдельный продукт с массивом доступных размеров
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

// Экспортируем для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
  module.exports = TommyHilfigerParser;
}