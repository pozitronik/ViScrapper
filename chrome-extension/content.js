/**
 * Content Script для VIParser Chrome Extension
 * Извлекает данные продукта со страницы Victoria's Secret
 */

console.log('VIParser content script loaded');

// Глобальные переменные для отслеживания состояния
let currentProductData = null;
let lastJsonLdContent = null;
let isPageValid = true;
let extractionInProgress = false;
let isProductChanged = false;
let changeTrackingActive = false;
let mutationObserver = null;
let currentUrl = window.location.href;
let changeTrackingStartTime = null;

// Обработчик сообщений от background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Content script received message:', request);
  
  switch (request.action) {
    case 'extractData':
      handleExtractData(sendResponse);
      return true; // Асинхронный ответ
      
    case 'checkPageChanges':
      handleCheckPageChanges(sendResponse);
      return true;
      
    default:
      sendResponse({ error: 'Unknown action' });
  }
});

/**
 * Обработка запроса на извлечение данных
 */
async function handleExtractData(sendResponse) {
  if (extractionInProgress) {
    sendResponse({ error: 'Извлечение данных уже выполняется' });
    return;
  }
  
  extractionInProgress = true;
  
  try {
    console.log('Starting data extraction...');
    
    // Проверяем, что мы на правильной странице
    if (!isValidProductPage()) {
      sendResponse({ 
        error: 'Расширение работает только на страницах товаров Victoria\'s Secret',
        isValid: false
      });
      return;
    }
    
    // Проверяем, изменился ли продукт
    if (isProductChanged) {
      sendResponse({
        error: 'Продукт был изменен. Необходимо обновить страницу для получения актуальных данных.',
        needsRefresh: true,
        isValid: false
      });
      return;
    }
    
    // Извлекаем данные
    const productData = await extractProductData();
    
    if (!productData) {
      sendResponse({ 
        error: 'Не удалось извлечь данные продукта',
        isValid: false
      });
      return;
    }
    
    currentProductData = productData;
    
    // Проверяем валидность данных
    const validation = validateProductData(productData);
    
    sendResponse({
      data: productData,
      isValid: validation.isValid,
      warnings: validation.warnings,
      needsRefresh: false
    });
    
  } catch (error) {
    console.error('Error extracting data:', error);
    sendResponse({ 
      error: 'Ошибка при извлечении данных: ' + error.message,
      isValid: false
    });
  } finally {
    extractionInProgress = false;
  }
}

/**
 * Проверка, что мы на странице товара
 */
function isValidProductPage() {
  // Проверяем URL
  const url = window.location.href;
  console.log('Checking page validity, URL:', url);
  
  if (!url.includes('victoriassecret.com')) {
    console.log('Not a Victoria\'s Secret page');
    return false;
  }
  
  // Проверяем наличие ключевых элементов
  const hasProductInfo = document.querySelector('[data-testid="ProductInfo-shortDescription"]');
  const hasProductPrice = document.querySelector('[data-testid="ProductPrice"]');
  
  console.log('ProductInfo element:', hasProductInfo);
  console.log('ProductPrice element:', hasProductPrice);
  
  const isValid = hasProductInfo && hasProductPrice;
  console.log('Page is valid product page:', isValid);
  
  return isValid;
}

/**
 * Проверка необходимости обновления страницы
 */
async function checkIfPageNeedsRefresh() {
  try {
    console.log('Checking if page needs refresh...');
    
    // Ждем появления JSON-LD скрипта
    const jsonLdScript = await waitForJsonLd();
    
    if (!jsonLdScript) {
      return true; // Требуется обновление
    }
    
    const currentJsonLd = jsonLdScript.textContent;
    console.log('JSON-LD found, content length:', currentJsonLd.length);
    
    // Если это первая загрузка, всегда считаем данные актуальными
    if (lastJsonLdContent === null) {
      console.log('First load, saving JSON-LD content');
      lastJsonLdContent = currentJsonLd;
      return false;
    }
    
    // Проверяем только если JSON-LD полностью идентичен,
    // но есть параметр choice в URL (что означает динамическое изменение)
    const urlParams = new URLSearchParams(window.location.search);
    const currentChoice = urlParams.get('choice');
    
    if (currentChoice && lastJsonLdContent === currentJsonLd) {
      console.log('Choice parameter detected with identical JSON-LD - may need refresh');
      
      // Дополнительная проверка - сравниваем SKU из JSON-LD с отображаемым на странице
      const pageData = extractBasicPageData();
      const jsonData = parseJsonLd(currentJsonLd);
      
      if (jsonData && pageData && jsonData.sku && pageData.sku) {
        if (jsonData.sku !== pageData.sku) {
          console.log('SKU mismatch detected:', jsonData.sku, 'vs', pageData.sku);
          return true;
        }
      }
    }
    
    // Обновляем сохраненный контент
    lastJsonLdContent = currentJsonLd;
    console.log('Page data appears fresh');
    return false;
    
  } catch (error) {
    console.error('Error checking page refresh need:', error);
    // В случае ошибки проверки, не блокируем работу
    return false;
  }
}

/**
 * Ожидание появления JSON-LD скрипта
 */
async function waitForJsonLd(timeout = 10000) {
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    const jsonLdScript = document.querySelector('script[type="application/ld+json"][id="structured-data-pdp"]');
    if (jsonLdScript && jsonLdScript.textContent.trim()) {
      return jsonLdScript;
    }
    
    // Ждем 100мс перед следующей попыткой
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  
  return null;
}

/**
 * Извлечение базовых данных со страницы (для сравнения)
 */
function extractBasicPageData() {
  try {
    const nameElement = document.querySelector('[data-testid="ProductInfo-shortDescription"]');
    const itemElement = document.querySelector('[data-testid="ProductInfo-genericId"]');
    
    return {
      name: nameElement?.textContent?.trim() || null,
      sku: itemElement?.textContent?.trim() || null
    };
  } catch (error) {
    console.error('Error extracting basic page data:', error);
    return null;
  }
}

/**
 * Основная функция извлечения данных продукта
 */
async function extractProductData() {
  try {
    console.log('Extracting product data...');
    
    // Ждем JSON-LD
    const jsonLdScript = await waitForJsonLd();
    let jsonData = null;
    
    if (jsonLdScript) {
      jsonData = parseJsonLd(jsonLdScript.textContent);
    }
    
    // Базовые данные
    const productData = {
      product_url: sanitizeProductUrl(window.location.href),
      name: extractName(),
      sku: extractSku(jsonData),
      price: extractPrice(jsonData),
      currency: extractCurrency(jsonData),
      availability: extractAvailability(jsonData),
      color: extractColor(),
      composition: extractComposition(),
      item: extractItem(),
      comment: ''
    };
    
    // Извлекаем изображения
    const allImages = extractImages();
    if (allImages.length > 0) {
      productData.main_image_url = allImages[0];
      productData.all_image_urls = allImages;
    }
    
    // Извлекаем размеры (это может занять время)
    try {
      // Временно отключаем отслеживание мутаций во время извлечения размеров
      const wasTrackingActive = changeTrackingActive;
      if (mutationObserver) {
        console.log('Temporarily disabling mutation tracking for size extraction');
        mutationObserver.disconnect();
        changeTrackingActive = false;
      }
      
      const sizesData = await extractSizes();
      if (sizesData) {
        // Проверяем тип данных размеров
        if (Array.isArray(sizesData)) {
          // Простые размеры
          productData.available_sizes = sizesData;
        } else if (sizesData.combinations) {
          // Комбинации размеров
          productData.size_combinations = sizesData;
        }
      }
      
      // Восстанавливаем отслеживание
      if (wasTrackingActive && mutationObserver) {
        console.log('Re-enabling mutation tracking after size extraction');
        setTimeout(() => {
          setupJsonLdTracking();
        }, 1000); // Небольшая задержка чтобы дать странице стабилизироваться
      }
    } catch (error) {
      console.error('Error extracting sizes:', error);
    }
    
    console.log('Product data extracted:', productData);
    return productData;
    
  } catch (error) {
    console.error('Error in extractProductData:', error);
    return null;
  }
}

/**
 * Парсинг JSON-LD данных
 */
function parseJsonLd(jsonLdText) {
  try {
    const data = JSON.parse(jsonLdText);
    return data;
  } catch (error) {
    console.error('Error parsing JSON-LD:', error);
    return null;
  }
}

/**
 * Сантизация URL продукта - удаляет параметры, которые не влияют на идентификацию продукта
 */
function sanitizeProductUrl(url) {
  try {
    const urlObj = new URL(url);
    
    // Сохраняем только базовую часть URL без параметров
    // Параметры choice, utm_*, session_id и подобные не влияют на идентификацию продукта
    const cleanUrl = `${urlObj.protocol}//${urlObj.host}${urlObj.pathname}`;
    
    console.log(`URL sanitized: ${url} -> ${cleanUrl}`);
    return cleanUrl;
  } catch (error) {
    console.error('Error sanitizing URL:', error);
    return url; // Возвращаем оригинальный URL если не удалось обработать
  }
}

/**
 * Извлечение названия
 */
function extractName() {
  const element = document.querySelector('[data-testid="ProductInfo-shortDescription"]');
  return element?.textContent?.trim() || null;
}

/**
 * Извлечение SKU
 */
function extractSku(jsonData) {
  if (jsonData && jsonData.sku) {
    return jsonData.sku;
  }
  return null;
}

/**
 * Извлечение цены
 */
function extractPrice(jsonData) {
  if (jsonData && jsonData.offers && jsonData.offers.price) {
    return parseFloat(jsonData.offers.price);
  }
  
  // Альтернативный способ - из элемента на странице
  const priceElement = document.querySelector('[data-testid="ProductPrice"]');
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
 * Извлечение валюты
 */
function extractCurrency(jsonData) {
  if (jsonData && jsonData.offers && jsonData.offers.priceCurrency) {
    return jsonData.offers.priceCurrency;
  }
  return 'USD'; // По умолчанию для Victoria's Secret
}

/**
 * Извлечение доступности
 */
function extractAvailability(jsonData) {
  if (jsonData && jsonData.offers && jsonData.offers.availability) {
    const availabilityUrl = jsonData.offers.availability;
    
    // Извлекаем тип из URL schema.org
    if (availabilityUrl.includes('schema.org/')) {
      const type = availabilityUrl.split('schema.org/').pop();
      console.log(`Extracted availability type: ${type} from ${availabilityUrl}`);
      return type;
    }
    
    // Если не URL schema.org, возвращаем как есть
    return availabilityUrl;
  }
  
  // Если доступность не найдена, считаем продукт доступным
  return 'InStock';
}

/**
 * Извлечение цвета
 */
function extractColor() {
  const element = document.querySelector('[data-testid="SelectedChoiceLabel"]');
  if (element) {
    return element.textContent.replace('|', '').trim();
  }
  return null;
}

/**
 * Извлечение состава
 */
function extractComposition() {
  const element = document.querySelector('[data-testid="ProductComposition"]');
  return element?.textContent?.trim() || null;
}

/**
 * Извлечение артикула
 */
function extractItem() {
  const element = document.querySelector('[data-testid="ProductInfo-genericId"]');
  return element?.textContent?.trim() || null;
}

/**
 * Извлечение изображений
 */
function extractImages() {
  const container = document.querySelector('[data-testid="PrimaryProductImage"]');
  if (!container) return [];
  
  const images = container.querySelectorAll('img');
  const imageUrls = [];
  
  images.forEach(img => {
    if (img.src && img.src.startsWith('http')) {
      // Конвертируем относительные URL в абсолютные
      const absoluteUrl = new URL(img.src, window.location.href).href;
      if (!imageUrls.includes(absoluteUrl)) {
        imageUrls.push(absoluteUrl);
      }
    }
  });
  
  return imageUrls;
}

/**
 * Извлечение размеров продукта
 */
async function extractSizes() {
  try {
    console.log('Starting size extraction...');
    
    const sizeContainer1 = document.querySelector('[data-testid="BoxSelector-size1"]');
    const sizeContainer2 = document.querySelector('[data-testid="BoxSelector-size2"]');
    
    // Проверяем связность контейнеров
    let areContainersRelated = false;
    if (sizeContainer1 && sizeContainer2) {
      const container1Parent = sizeContainer1.closest('.sc-s4utl4-0, .size-selection, .product-variants, .variant-selector, [class*="size"], [class*="variant"]');
      const container2Parent = sizeContainer2.closest('.sc-s4utl4-0, .size-selection, .product-variants, .variant-selector, [class*="size"], [class*="variant"]');
      
      if (container1Parent && container2Parent) {
        areContainersRelated = container1Parent === container2Parent || 
                              container1Parent.contains(sizeContainer2) || 
                              container2Parent.contains(sizeContainer1);
      }
      
      console.log(`Containers related check: ${areContainersRelated}`);
    }
    
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
      const combinationResult = await extractSizeCombinations(sizeContainer1, sizeContainer2);
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
    } else if (hasValidSize2 && !areContainersRelated) {
      // Одноразмерный продукт (используем несвязанный size2)
      console.log('Single size selector detected (using unrelated size2), extracting simple sizes...');
      const availableSizes = size2Options.map(btn => btn.textContent.trim()).filter(size => size);
      console.log('Simple sizes extracted:', availableSizes);
      return availableSizes;
    } else {
      console.log('No valid size options found');
      return [];
    }
    
  } catch (error) {
    console.error('Error in extractSizes:', error);
    return [];
  }
}

/**
 * Извлечение комбинаций размеров для двухразмерных продуктов
 */
async function extractSizeCombinations(sizeContainer1, sizeContainer2) {
  try {
    console.log('Starting size combination extraction...');
    
    // Получаем типы размеров
    const size1Type = getSizeTypeLabel(sizeContainer1);
    const size2Type = getSizeTypeLabel(sizeContainer2);
    
    console.log(`Size types detected: ${size1Type} and ${size2Type}`);
    
    // Получаем все опции size1
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
      
      // Пропускаем disabled опции
      if (size1Option.getAttribute('aria-disabled') === 'true') {
        console.log(`Skipping disabled size1 option: ${size1Value}`);
        continue;
      }
      
      console.log(`Clicking size1 option: ${size1Value}`);
      
      // Кликаем по опции size1
      size1Option.click();
      
      // Ждем обновления страницы
      await wait(200);
      
      // Получаем доступные опции size2 после выбора size1
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
        await wait(100);
      }
      if (originallySelected2) {
        originallySelected2.click();
        await wait(100);
      }
    } catch (e) {
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
    console.error('Error extracting size combinations:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Получение типа размера из контейнера
 */
function getSizeTypeLabel(sizeContainer) {
  try {
    // Ищем label в родительском контейнере
    const parent = sizeContainer.closest('.sc-s4utl4-0');
    if (parent) {
      const labelElement = parent.querySelector('[data-testid]');
      if (labelElement) {
        return labelElement.getAttribute('data-testid');
      }
    }
    
    // Резерв: используем aria-label от radiogroup
    const ariaLabel = sizeContainer.getAttribute('aria-label');
    if (ariaLabel) {
      return ariaLabel;
    }
    
    // Резерв: используем data-testid
    const testId = sizeContainer.getAttribute('data-testid');
    if (testId) {
      return testId.replace('BoxSelector-', '');
    }
    
    return 'Unknown';
  } catch (e) {
    return 'Unknown';
  }
}

/**
 * Функция ожидания
 */
function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Валидация данных продукта
 */
function validateProductData(data) {
  const warnings = [];
  const requiredFields = ['name', 'sku', 'price', 'currency'];
  
  let isValid = true;
  
  // Проверяем обязательные поля
  requiredFields.forEach(field => {
    if (!data[field]) {
      warnings.push(`Отсутствует обязательное поле: ${field}`);
      isValid = false;
    }
  });
  
  // Предупреждения для опциональных полей (не влияют на isValid)
  if (!data.all_image_urls || data.all_image_urls.length === 0) {
    warnings.push('Изображения не найдены');
  }
  
  if (!data.available_sizes && !data.size_combinations) {
    warnings.push('Размеры не извлечены');
  }
  
  return {
    isValid: isValid, // Только обязательные поля влияют на валидность
    warnings
  };
}

/**
 * Обработка проверки изменений страницы
 */
function handleCheckPageChanges(sendResponse) {
  checkIfPageNeedsRefresh()
    .then(needsRefresh => {
      sendResponse({ needsRefresh });
    })
    .catch(error => {
      console.error('Error checking page changes:', error);
      sendResponse({ needsRefresh: true });
    });
}

// Инициализация при загрузке страницы
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  initialize();
}

function initialize() {
  console.log('VIParser content script initialized');
  
  // Сброс флага изменения продукта при инициализации
  resetProductChangeFlag();
  
  // Ожидание загрузки элементов и настройка отслеживания
  waitForPageElements();
}

/**
 * Ожидание загрузки ключевых элементов страницы
 */
async function waitForPageElements() {
  console.log('Waiting for page elements to load...');
  
  let attempts = 0;
  const maxAttempts = 20; // 10 секунд максимум
  
  while (attempts < maxAttempts) {
    isPageValid = isValidProductPage();
    
    if (isPageValid) {
      console.log('Valid product page detected after', attempts * 500, 'ms');
      
      // Настройка отслеживания изменений
      setupChangeTracking();
      return;
    }
    
    attempts++;
    console.log(`Attempt ${attempts}/${maxAttempts} - elements not ready yet`);
    
    // Ждем 500мс перед следующей попыткой
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  
}

// Слушатель события обновления страницы
window.addEventListener('beforeunload', () => {
  console.log('Page unloading, cleaning up observers');
  
  // Отключаем MutationObserver при выгрузке страницы
  if (mutationObserver) {
    mutationObserver.disconnect();
    mutationObserver = null;
  }
  
  changeTrackingActive = false;
});

/**
 * Настройка отслеживания изменений продукта
 */
function setupChangeTracking() {
  if (changeTrackingActive) {
    console.log('Change tracking already active');
    return;
  }
  
  console.log('Setting up change tracking...');
  
  // Ждем полной загрузки страницы
  if (document.readyState === 'complete') {
    // Страница уже загружена
    console.log('Page already loaded, starting change tracking immediately');
    startChangeTracking();
  } else {
    // Ждем события load
    console.log('Waiting for page load event...');
    window.addEventListener('load', () => {
      console.log('Page load event fired, starting change tracking...');
      // Небольшая дополнительная задержка для асинхронных скриптов
      setTimeout(startChangeTracking, 1000);
    });
  }
}

/**
 * Запуск отслеживания изменений
 */
function startChangeTracking() {
  console.log('Starting change tracking after page load...');
  
  // Записываем время начала отслеживания
  changeTrackingStartTime = Date.now();
  
  // 1. Отслеживание изменений JSON-LD
  setupJsonLdTracking();
  
  // 2. Отслеживание изменений URL
  setupUrlTracking();
  
  changeTrackingActive = true;
  console.log('Change tracking activated');
}

/**
 * Настройка отслеживания изменений JSON-LD через MutationObserver
 */
function setupJsonLdTracking() {
  const jsonLdElement = document.querySelector('#structured-data-pdp');
  
  if (!jsonLdElement) {
    setTimeout(setupJsonLdTracking, 2000);
    return;
  }
  
  console.log('Setting up MutationObserver for JSON-LD changes');
  
  // Останавливаем предыдущий observer если есть
  if (mutationObserver) {
    mutationObserver.disconnect();
  }
  
  // Находим родительский элемент (head или body)
  const parentElement = jsonLdElement.parentNode || document.head;
  console.log('Observing parent element:', parentElement.tagName);
  
  // Создаем новый MutationObserver
  mutationObserver = new MutationObserver((mutations) => {
    console.log('JSON-LD area mutations detected:', mutations.length);
    
    mutations.forEach((mutation) => {
      if (mutation.type === 'childList') {
        // Проверяем добавленные узлы
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE && 
              node.id === 'structured-data-pdp') {
            console.log('JSON-LD element replaced, marking product as changed');
            handleProductChange('JSON-LD element replaced');
          }
        });
        
        // Проверяем удаленные узлы
        mutation.removedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE && 
              node.id === 'structured-data-pdp') {
            console.log('JSON-LD element removed');
          }
        });
      }
      
      // Также отслеживаем изменения внутри текущего элемента
      if (mutation.target.id === 'structured-data-pdp' && 
          (mutation.type === 'characterData' || mutation.type === 'childList')) {
        console.log('JSON-LD content changed, marking product as changed');
        handleProductChange('JSON-LD content changed');
      }
    });
  });
  
  // Настраиваем observer для отслеживания замены элемента
  mutationObserver.observe(parentElement, {
    childList: true,        // отслеживать добавление/удаление дочерних элементов
    subtree: true          // отслеживать изменения во всех потомках
  });
  
  console.log('MutationObserver for JSON-LD activated');
}

/**
 * Настройка отслеживания изменений URL
 */
function setupUrlTracking() {
  console.log('Setting up URL change tracking');
  
  // 1. Слушатель события popstate (назад/вперед в браузере)
  window.addEventListener('popstate', (event) => {
    console.log('Popstate event detected');
    handleUrlChange();
  });
  
  // 2. Перехват методов history для SPA навигации
  const originalPushState = history.pushState;
  const originalReplaceState = history.replaceState;
  
  history.pushState = function(...args) {
    originalPushState.apply(history, args);
    console.log('PushState detected');
    handleUrlChange();
  };
  
  history.replaceState = function(...args) {
    originalReplaceState.apply(history, args);
    console.log('ReplaceState detected');
    handleUrlChange();
  };
  
  console.log('URL change tracking activated');
}

/**
 * Обработка изменения URL
 */
function handleUrlChange() {
  const newUrl = window.location.href;
  
  if (newUrl !== currentUrl) {
    console.log('URL changed:', currentUrl, '->', newUrl);
    currentUrl = newUrl;
    handleProductChange('URL changed');
  }
}

/**
 * Обработка события изменения продукта
 */
function handleProductChange(reason) {
  console.log(`Product change detected: ${reason}`);
  
  // Игнорируем изменения в первые 2 секунды после начала отслеживания
  if (changeTrackingStartTime && (Date.now() - changeTrackingStartTime < 2000)) {
    console.log('Ignoring change during initial tracking setup period');
    return;
  }
  
  if (!isProductChanged) {
    isProductChanged = true;
    console.log('Marking product as changed - popup will show refresh warning');
    
    // Опционально: можно отправить сообщение в popup если он открыт
    try {
      chrome.runtime.sendMessage({
        action: 'productChanged',
        reason: reason
      });
    } catch (error) {
      // Popup может быть закрыт, это нормально
      console.log('Could not send message to popup (probably closed)');
    }
  }
}

/**
 * Сброс флага изменения продукта (вызывается при обновлении страницы)
 */
function resetProductChangeFlag() {
  console.log('Resetting product change flag');
  isProductChanged = false;
}