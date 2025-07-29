/**
 * Content Script для VIParser Chrome Extension
 * Универсальный парсер продуктов с поддержкой множественных сайтов
 */

console.log('VIParser content script loaded');

// Глобальные переменные для отслеживания состояния
let currentParser = null;
let currentProductData = null;
let lastJsonLdContent = null;
let isPageValid = true;
let extractionInProgress = false;
let isProductChanged = false;
let changeTrackingActive = false;
let mutationObserver = null;
let colorObserver = null;
let currentUrl = window.location.href;
let changeTrackingStartTime = null;
let initialPageLoadComplete = false;
let pageInitializedTime = null;

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
      
    case 'startColorObserver':
      handleStartColorObserver(sendResponse);
      return true;
      
    case 'stopColorObserver':
      handleStopColorObserver(sendResponse);
      return true;
      
    default:
      sendResponse({ error: 'Unknown action' });
  }
});

/**
 * Инициализация парсера для текущего сайта
 */
function initializeParser() {
  try {
    console.log('Initializing parser for current site...');
    
    if (typeof ParserFactory === 'undefined') {
      console.error('ParserFactory not available! Make sure parsers are loaded.');
      return false;
    }
    
    currentParser = ParserFactory.createParser();
    
    if (!currentParser) {
      console.log('No parser available for current site');
      console.log('Supported sites:', ParserFactory.getSupportedSites());
      return false;
    }
    
    console.log(`Successfully initialized parser: ${currentParser.siteName}`);
    return true;
  } catch (error) {
    console.error('Error initializing parser:', error);
    return false;
  }
}

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
    
    // Инициализируем парсер если еще не инициализирован
    if (!currentParser) {
      if (!initializeParser()) {
        sendResponse({ 
          error: 'Сайт не поддерживается расширением',
          isValid: false,
          supportedSites: typeof ParserFactory !== 'undefined' ? ParserFactory.getSupportedSites() : []
        });
        return;
      }
    }
    
    // Проверяем, что мы на правильной странице
    if (!currentParser.isValidProductPage()) {
      sendResponse({ 
        error: `Расширение работает только на страницах товаров ${currentParser.siteName}`,
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
    
    // Проверяем валидность данных
    const validation = currentParser.validateProductData(productData);
    
    // Если нет SKU - не отправляем данные на бэкенд
    if (!validation.isValid) {
      sendResponse({
        error: 'Продукт не может быть отправлен на сервер: отсутствует SKU',
        isValid: false,
        warnings: validation.warnings,
        needsRefresh: false
      });
      return;
    }
    
    currentProductData = productData;
    
    sendResponse({
      data: productData,
      isValid: validation.isValid,
      warnings: validation.warnings,
      needsRefresh: false,
      siteName: currentParser.siteName
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
 * Основная функция извлечения данных продукта
 */
async function extractProductData() {
  if (!currentParser) {
    console.error('No parser available for data extraction');
    return null;
  }
  
  try {
    console.log(`Extracting product data using ${currentParser.siteName} parser...`);
    
    // Получаем JSON-LD данные (если парсер их поддерживает)
    let jsonData = null;
    if (typeof currentParser.waitForJsonLd === 'function') {
      const jsonLdScript = await currentParser.waitForJsonLd();
      if (jsonLdScript && typeof currentParser.parseJsonLd === 'function') {
        jsonData = currentParser.parseJsonLd(jsonLdScript.textContent);
        console.log('JSON-LD data loaded:', !!jsonData);
      }
    }
    
    // Базовые данные продукта
    const baseSku = currentParser.extractSku(jsonData);
    let finalSku = baseSku;
    
    // Для Calvin Klein генерируем уникальный SKU с кодом цвета
    if (currentParser.config && currentParser.config.domain === 'calvinklein.us') {
      console.log('Calvin Klein detected - generating color-specific SKU...');
      console.log('Base SKU:', baseSku);
      
      const colorCode = currentParser.extractColorCodeFromSelection ? currentParser.extractColorCodeFromSelection() : null;
      console.log('Extracted color code:', colorCode);
      
      if (colorCode && currentParser.generateColorSpecificSku) {
        finalSku = currentParser.generateColorSpecificSku(baseSku, colorCode);
        console.log(`Generated color-specific SKU: ${finalSku} (was: ${baseSku})`);
      } else {
        console.log('Using base SKU as final SKU (no color code or method missing)');
      }
    } else {
      console.log('Not Calvin Klein - using base SKU as final SKU');
    }
    
    const productData = {
      product_url: window.location.href,  // Полный URL с параметрами для хранения
      name: currentParser.extractName(),
      sku: finalSku,
      price: currentParser.extractPrice(jsonData),
      currency: currentParser.extractCurrency(jsonData),
      availability: currentParser.extractAvailability(jsonData),
      store: currentParser.config.siteName,  // Store name from parser configuration
      comment: ''
    };

    // Дополнительные поля (если поддерживаются парсером)
    if (typeof currentParser.extractColor === 'function') {
      productData.color = await currentParser.extractColor();
    }
    
    if (typeof currentParser.extractComposition === 'function') {
      productData.composition = await currentParser.extractComposition();
    }
    
    if (typeof currentParser.extractItem === 'function') {
      productData.item = currentParser.extractItem();
    }

    // Извлекаем изображения
    const allImages = await currentParser.extractImages();
    if (allImages && allImages.length > 0) {
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
      
      const sizesData = await currentParser.extractSizes();
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
        }, 1000); // Небольшая задержка для стабилизации страницы
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
 * Проверка необходимости обновления страницы
 */
async function checkIfPageNeedsRefresh() {
  try {
    console.log('Checking if page needs refresh...');
    
    // Если нет парсера или он не поддерживает JSON-LD, считаем данные актуальными
    if (!currentParser || typeof currentParser.waitForJsonLd !== 'function') {
      console.log('Parser does not support JSON-LD tracking');
      return false;
    }
    
    // Ждем появления JSON-LD скрипта
    const jsonLdScript = await currentParser.waitForJsonLd();
    
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
      const jsonData = currentParser.parseJsonLd(currentJsonLd);
      
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
 * Извлечение базовых данных со страницы (для сравнения)
 */
function extractBasicPageData() {
  if (!currentParser) return null;
  
  try {
    return {
      name: currentParser.extractName(),
      sku: currentParser.extractItem ? currentParser.extractItem() : null
    };
  } catch (error) {
    console.error('Error extracting basic page data:', error);
    return null;
  }
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

/**
 * Запуск наблюдателя за цветом
 */
function handleStartColorObserver(sendResponse) {
  try {
    console.log('Starting color observer...');
    
    if (!currentParser || !currentParser.setupColorObserver) {
      sendResponse({ error: 'Parser does not support color observation' });
      return;
    }
    
    // Останавливаем предыдущий observer если есть
    if (colorObserver) {
      colorObserver.disconnect();
    }
    
    // Создаем callback для обновления popup
    const colorUpdateCallback = (color) => {
      console.log('Color detected by observer:', color);
      
      // Обновляем сохраненные данные
      if (currentProductData) {
        currentProductData.color = color;
      }
      
      // Отправляем обновление в popup
      try {
        chrome.runtime.sendMessage({
          action: 'colorUpdated',
          color: color
        });
      } catch (error) {
        console.log('Could not send color update to popup (probably closed)');
      }
    };
    
    // Настраиваем observer
    colorObserver = currentParser.setupColorObserver(colorUpdateCallback);
    
    console.log('Color observer started successfully');
    sendResponse({ success: true });
    
  } catch (error) {
    console.error('Error starting color observer:', error);
    sendResponse({ error: 'Failed to start color observer' });
  }
}

/**
 * Остановка наблюдателя за цветом
 */
function handleStopColorObserver(sendResponse) {
  try {
    console.log('Stopping color observer...');
    
    if (colorObserver) {
      colorObserver.disconnect();
      colorObserver = null;
      console.log('Color observer stopped');
    }
    
    sendResponse({ success: true });
    
  } catch (error) {
    console.error('Error stopping color observer:', error);
    sendResponse({ error: 'Failed to stop color observer' });
  }
}

// Инициализация при загрузке страницы
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize);
} else {
  initialize();
}

function initialize() {
  console.log('VIParser content script initialized');
  
  // Отмечаем время инициализации
  pageInitializedTime = Date.now();
  
  // Инициализируем парсер
  if (!initializeParser()) {
    console.log('Site not supported, extension will remain inactive');
    return;
  }
  
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
    if (currentParser) {
      isPageValid = currentParser.isValidProductPage();
      
      if (isPageValid) {
        console.log('Valid product page detected after', attempts * 500, 'ms');
        
        // Настройка отслеживания изменений
        setupChangeTracking();
        return;
      }
    }
    
    attempts++;
    console.log(`Attempt ${attempts}/${maxAttempts} - elements not ready yet`);
    
    // Ждем 500мс перед следующей попыткой
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  
  console.log('Page elements failed to load within timeout');
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
    console.log('Page already loaded, starting change tracking immediately');
    startChangeTracking();
  } else {
    console.log('Waiting for page load event...');
    window.addEventListener('load', () => {
      console.log('Page load event fired, starting change tracking...');
      setTimeout(startChangeTracking, 1000);
    });
  }
}

/**
 * Запуск отслеживания изменений
 */
function startChangeTracking() {
  console.log('Starting change tracking after page load...');
  
  changeTrackingStartTime = Date.now();
  
  // Отмечаем, что начальная загрузка страницы завершена
  setTimeout(() => {
    initialPageLoadComplete = true;
    console.log('Initial page load marked as complete');
  }, 3000); // Даем 3 секунды на завершение всех начальных загрузок
  
  // 1. Отслеживание изменений JSON-LD (если поддерживается и необходимо)
  if (currentParser && typeof currentParser.waitForJsonLd === 'function') {
    // Для Carter's отключаем mutation observer - используем URL-based navigation
    if (currentParser.config && currentParser.config.domain === 'carters.com') {
      console.log('Carter\'s detected - skipping JSON-LD mutation observer (URL-based navigation)');
    } else {
      setupJsonLdTracking();
    }
  }
  
  // 2. Отслеживание изменений URL
  // Для Carter's URL изменения нормальны (смена стилей), для других сайтов могут означать проблему
  if (currentParser.config && currentParser.config.domain === 'carters.com') {
    console.log('Carter\'s detected - URL changes are normal, minimal URL tracking');
  } else {
    setupUrlTracking();
  }
  
  changeTrackingActive = true;
  console.log('Change tracking activated');
}

/**
 * Настройка отслеживания изменений JSON-LD через MutationObserver
 */
function setupJsonLdTracking() {
  // Для сайтов без JSON-LD не настраиваем отслеживание
  if (!currentParser || typeof currentParser.waitForJsonLd !== 'function') {
    console.log('Current parser does not support JSON-LD tracking');
    return;
  }
  
  // Ищем JSON-LD элемент (для VS это специфичный селектор)
  let jsonLdSelector = 'script[type="application/ld+json"]';
  if (currentParser.config && currentParser.config.selectors && currentParser.config.selectors.jsonLdScript) {
    jsonLdSelector = currentParser.config.selectors.jsonLdScript;
  }
  
  const jsonLdElement = document.querySelector(jsonLdSelector);
  
  if (!jsonLdElement) {
    setTimeout(setupJsonLdTracking, 2000);
    return;
  }
  
  console.log('Setting up MutationObserver for JSON-LD changes');
  
  // Останавливаем предыдущий observer если есть
  if (mutationObserver) {
    mutationObserver.disconnect();
  }
  
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
              node.matches && node.matches(jsonLdSelector)) {
            console.log('JSON-LD element replaced, marking product as changed');
            handleProductChange('JSON-LD element replaced');
          }
        });
      }
      
      // Также отслеживаем изменения внутри текущего элемента
      if (mutation.target.matches && mutation.target.matches(jsonLdSelector) && 
          (mutation.type === 'characterData' || mutation.type === 'childList')) {
        console.log('JSON-LD content changed, marking product as changed');
        handleProductChange('JSON-LD content changed');
      }
    });
  });
  
  // Настраиваем observer для отслеживания замены элемента
  mutationObserver.observe(parentElement, {
    childList: true,
    subtree: true
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
  
  // Игнорируем изменения во время начальной загрузки страницы
  if (!initialPageLoadComplete) {
    console.log('Ignoring change during initial page load period');
    return;
  }
  
  // Игнорируем изменения в первые 5 секунд после инициализации скрипта
  if (pageInitializedTime && (Date.now() - pageInitializedTime < 5000)) {
    console.log('Ignoring change during initial script setup period');
    return;
  }
  
  // Игнорируем изменения в первые 3 секунды после начала отслеживания
  if (changeTrackingStartTime && (Date.now() - changeTrackingStartTime < 3000)) {
    console.log('Ignoring change during initial tracking setup period');
    return;
  }
  
  // Для Carter's: если можем извлечь SKU из URL, не требуем обновления страницы
  if (currentParser && currentParser.config && currentParser.config.domain === 'carters.com') {
    const url = window.location.href;
    const urlMatch = url.match(/\/V_([A-Z0-9]+)$/i);
    if (urlMatch) {
      console.log('Carter\'s detected with valid URL SKU pattern - no refresh needed');
      console.log(`Reason for change: ${reason}, but URL SKU is available`);
      return; // Не устанавливаем флаг изменения
    }
  }
  
  // Дополнительная проверка: если это URL изменение на той же странице (anchor/параметры), игнорируем
  if (reason === 'URL changed') {
    const currentBasePath = window.location.pathname;
    const previousBasePath = currentUrl ? new URL(currentUrl).pathname : '';
    if (currentBasePath === previousBasePath) {
      console.log('URL change detected but same page path - ignoring');
      return;
    }
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
  console.log('Resetting product change flag and page load state');
  isProductChanged = false;
  initialPageLoadComplete = false;
  pageInitializedTime = null;
  changeTrackingStartTime = null;
}