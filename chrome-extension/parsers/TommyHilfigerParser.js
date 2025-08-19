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
        colorsList: '[data-display-id="colorCode"]',
        sizesList: '#sizessize',
        jsonLdScript: 'script[type="application/ld+json"]'
      }
    });
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
    
    // Приоритет 3: Проверяем наличие характерных функций продукта
    const hasColorSelector = !!document.querySelector(this.config.selectors.colorsList);
    const hasProductImages = !!document.querySelector('[data-comp="ProductImage"]');
    const hasPriceElement = !!document.querySelector('.sales .value[content]');
    
    console.log('Color selector found:', hasColorSelector);
    console.log('Product images found:', hasProductImages);
    console.log('Price element found:', hasPriceElement);
    
    // Если есть базовые элементы + любая из характерных функций = валидная страница
    const hasProductFeatures = hasColorSelector || hasProductImages || hasPriceElement;
    const isValid = hasProductFeatures;
    
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
   * Настройка наблюдателя для отслеживания изменений цвета и обновления изображений
   */
  setupColorObserver(callback) {
    console.log('TH setupColorObserver: Setting up Tommy Hilfiger color observer...');
    
    // Создаем MutationObserver для отслеживания изменений
    const observer = new MutationObserver(async (mutations) => {
      let shouldUpdateImages = false;
      
      for (const mutation of mutations) {
        // Отслеживаем изменения атрибутов у radio inputs (checked/aria-checked)
        if (mutation.type === 'attributes' && 
            (mutation.attributeName === 'checked' || mutation.attributeName === 'aria-checked')) {
          const target = mutation.target;
          
          // Проверяем различные возможные контейнеры для цветов
          const isColorRadio = target.type === 'radio' && (
            // Обычная структура
            target.closest('[data-display-id="colorCode"]') ||
            // Grouped-by-price структура
            target.closest('.colors-variant-list') ||
            // Fallback по классу
            target.classList.contains('variant-colorCode')
          );
          
          if (isColorRadio) {
            console.log('TH setupColorObserver: Color radio change detected:', target.id);
            shouldUpdateImages = true;
            break;
          }
        }
        
        // Также отслеживаем добавление/удаление узлов в изображениях (динамические обновления)
        if (mutation.type === 'childList') {
          const addedNodes = Array.from(mutation.addedNodes);
          const hasImageChanges = addedNodes.some(node => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              return node.matches && (
                node.matches('[data-comp="ProductImage"]') ||
                node.matches('.product-image.swiper-slide') ||
                node.querySelector && (
                  node.querySelector('[data-comp="ProductImage"]') ||
                  node.querySelector('.product-image.swiper-slide')
                )
              );
            }
            return false;
          });
          
          if (hasImageChanges) {
            console.log('TH setupColorObserver: Image container changes detected');
            shouldUpdateImages = true;
            break;
          }
        }
      }
      
      if (shouldUpdateImages) {
        console.log('TH setupColorObserver: Updating images after color change...');
        
        // Небольшая задержка для завершения DOM обновлений
        await this.wait(300);
        
        try {
          // Извлекаем новые изображения из обновленного DOM
          const updatedImages = await this.extractImagesFromDOM();
          console.log(`TH setupColorObserver: Found ${updatedImages.length} updated images`);
          
          // Извлекаем обновленный цвет
          const updatedColor = this.extractColor();
          console.log('TH setupColorObserver: Updated color:', updatedColor);
          
          // Уведомляем callback о изменениях
          if (callback) {
            callback({
              color: updatedColor,
              images: updatedImages,
              source: 'tommy-hilfiger-color-change'
            });
          }
          
        } catch (error) {
          console.error('TH setupColorObserver: Error updating images:', error);
        }
      }
    });
    
    // Настраиваем наблюдение за всем документом
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['checked', 'aria-checked']
    });
    
    console.log('TH setupColorObserver: Tommy Hilfiger color observer set up');
    return observer;
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
      const availableSizes = [];
      
      // Вариант 1: Обычная структура с размерными input'ами
      const sizesList = document.querySelector(this.config.selectors.sizesList);
      if (sizesList) {
        const sizeInputs = sizesList.querySelectorAll('input[type="radio"]');
        console.log(`TH extractSizes: Found ${sizeInputs.length} size radio inputs`);
        
        sizeInputs.forEach(input => {
          const inputId = input.getAttribute('id');
          const label = document.querySelector(`label[for="${inputId}"]`);
          
          // Проверяем, что размер не отключен (не имеет класс size-disabled)
          if (label && label.classList.contains('size-disabled')) {
            console.log(`TH extractSizes: Skipping disabled size for input ${inputId}`);
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
          console.log(`TH extractSizes: Found ${availableSizes.length} sizes from radio inputs:`, availableSizes);
          return availableSizes;
        }
      }
      
      // Вариант 2: "ONE SIZE" структура - ищем в тексте заголовка
      const sizeHeader = document.querySelector('#pdp-attr-size');
      if (sizeHeader) {
        const sizeValueSpan = sizeHeader.querySelector('.variation__attr--value');
        if (sizeValueSpan) {
          const sizeText = sizeValueSpan.textContent?.trim();
          console.log(`TH extractSizes: Found size from header:`, sizeText);
          
          if (sizeText && sizeText !== '') {
            availableSizes.push(sizeText);
            return availableSizes;
          }
        }
      }
      
      // Вариант 3: Альтернативный поиск размера в заголовке
      const altSizeHeader = document.querySelector('.size.attribute-label');
      if (altSizeHeader) {
        const sizeValueSpan = altSizeHeader.querySelector('.variation__attr--value');
        if (sizeValueSpan) {
          const sizeText = sizeValueSpan.textContent?.trim();
          console.log(`TH extractSizes: Found size from alternative header:`, sizeText);
          
          if (sizeText && sizeText !== '') {
            availableSizes.push(sizeText);
            return availableSizes;
          }
        }
      }
      
      // Вариант 4: Поиск по всему документу для "ONE SIZE" или других размеров
      const oneSize = document.querySelector('[data-testid="size-onesize"], .size-one-size');
      if (oneSize) {
        console.log('TH extractSizes: Found ONE SIZE indicator');
        availableSizes.push('ONE SIZE');
        return availableSizes;
      }
      
      console.log('TH extractSizes: No sizes found');
      return availableSizes;
      
    } catch (error) {
      console.error('Error in TH extractSizes:', error);
      return [];
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
      console.log(`TH extractAllColors: Found ${inputs.length} color inputs in main colorsList`);
    }
    
    // Вариант 2: Grouped-by-price структура - собираем из всех видимых colorGroup
    const colorGroups = document.querySelectorAll('.colors-variant-list:not(.d-none)');
    console.log(`TH extractAllColors: Found ${colorGroups.length} visible color groups`);
    
    colorGroups.forEach((group, index) => {
      const inputs = group.querySelectorAll('input[type="radio"]');
      colorInputs = colorInputs.concat(Array.from(inputs));
      console.log(`TH extractAllColors: Found ${inputs.length} color inputs in color group ${index}: ${group.className}`);
    });
    
    // Вариант 3: Fallback - поиск по всему документу
    if (colorInputs.length === 0) {
      const fallbackInputs = document.querySelectorAll('input[type="radio"].variant-colorCode');
      colorInputs = colorInputs.concat(Array.from(fallbackInputs));
      console.log(`TH extractAllColors: Found ${fallbackInputs.length} color inputs via fallback selector`);
    }
    
    console.log(`TH extractAllColors: Total found ${colorInputs.length} color radio inputs`);
    
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
    
    console.log(`TH extractAllColors: After deduplication: ${uniqueInputs.length} unique color inputs`);
    
    uniqueInputs.forEach(input => {
      const inputId = input.getAttribute('id');
      if (!inputId) {
        console.log('TH extractAllColors: Skipping input without ID');
        return;
      }
      
      // Извлекаем цветовой код из ID
      const colorCode = this.extractColorCodeFromId(inputId);
      if (!colorCode) {
        console.log('TH extractAllColors: No color code found for input ID:', inputId);
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
      
      console.log(`TH extractAllColors: Added color - Code: "${colorCode}", Name: "${colorName}", Selected: ${input.checked || input.getAttribute('aria-checked') === 'true'}`);
    });
    
    console.log(`TH extractAllColors: Extracted ${colors.length} colors`);
    return colors;
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
   * Извлечение всех вариантов (цвет + размеры) для создания отдельных продуктов
   * Генерирует уникальные SKU в формате: {baseProductCode}-{colorCode}
   * Каждый цвет = отдельный продукт с массивом доступных размеров
   */
  async extractAllVariants() {
    try {
      console.log('Starting TH variant extraction...');
      
      const baseJsonData = this.getJsonLdData();
      const baseProductCode = this.extractUniqueProductId();
      const baseName = this.extractName();
      const basePrice = this.extractPrice(baseJsonData);
      const baseCurrency = this.extractCurrency(baseJsonData);
      const baseAvailability = this.extractAvailability(baseJsonData);
      
      if (!baseProductCode) {
        console.error('TH extractAllVariants: No base product code found, cannot create variants');
        return [];
      }
      
      const colors = this.extractAllColors();
      const variants = [];
      
      if (colors.length === 0) {
        console.log('TH extractAllVariants: No colors found, creating single variant with current state');
        const sizes = await this.extractSizes();
        const currentColorCode = this.extractSelectedColorCode();
        const currentColorName = this.extractColor();
        const baseImages = await this.extractImages();
        
        // Создаем один вариант с текущим цветом и всеми размерами
        const variantSku = `${baseProductCode}-${currentColorCode || 'default'}`;
        
        variants.push({
          sku: variantSku,
          name: baseName,
          price: basePrice,
          currency: baseCurrency,
          availability: baseAvailability,
          color: currentColorName,
          available_sizes: sizes, // Все размеры для этого цвета
          all_image_urls: baseImages,
          item: baseProductCode, // Добавляем артикул
          product_url: this.sanitizeUrl(window.location.href)
        });
      } else {
        // Для каждого цвета создаем один вариант с всеми размерами
        for (const color of colors) {
          console.log(`TH extractAllVariants: Processing color: ${color.name} (${color.code})`);
          
          // Кликаем на цвет если он не выбран
          if (!color.isSelected) {
            // Используем ID для поиска radio input вместо data-attr-value
            const colorInput = document.querySelector(`#${color.inputId}`);
            if (colorInput) {
              console.log(`TH extractAllVariants: Clicking color input with ID: ${color.inputId}`);
              colorInput.click();
              await this.wait(500); // Ждем обновления размеров и изображений
            } else {
              console.warn(`TH extractAllVariants: Could not find color input with ID: ${color.inputId}`);
            }
          }
          
          const sizes = await this.extractSizes();
          const colorImages = await this.extractImages();
          
          // Создаем один вариант для этого цвета со всеми размерами
          const variantSku = `${baseProductCode}-${color.code}`;
          
          variants.push({
            sku: variantSku,
            name: baseName,
            price: basePrice,
            currency: baseCurrency,
            availability: baseAvailability,
            color: color.name,
            available_sizes: sizes, // Все размеры для этого цвета
            all_image_urls: colorImages,
            item: baseProductCode, // Добавляем артикул
            product_url: this.sanitizeUrl(window.location.href)
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