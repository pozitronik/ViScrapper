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
    
    // Проверяем актуальность данных
    const needsRefresh = await checkIfPageNeedsRefresh();
    if (needsRefresh) {
      sendResponse({
        error: 'Страница содержит неактуальные данные. Требуется обновление.',
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
  if (!url.includes('victoriassecret.com')) {
    return false;
  }
  
  // Проверяем наличие ключевых элементов
  const hasProductInfo = document.querySelector('[data-testid="ProductInfo-shortDescription"]');
  const hasProductPrice = document.querySelector('[data-testid="ProductPrice"]');
  
  return hasProductInfo && hasProductPrice;
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
      console.warn('JSON-LD script not found after waiting');
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
      product_url: window.location.href,
      name: extractName(),
      sku: extractSku(jsonData),
      price: extractPrice(jsonData),
      currency: extractCurrency(jsonData),
      availability: extractAvailability(jsonData),
      color: extractColor(),
      composition: extractComposition(),
      item: extractItem(),
      images: extractImages(),
      sizes: [] // Будет заполнено позже
    };
    
    // Извлекаем размеры (это может занять время)
    try {
      const sizesData = await extractSizes();
      if (sizesData) {
        productData.sizes = sizesData;
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
    return jsonData.offers.availability;
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
 * Извлечение размеров (заглушка для сложной логики)
 */
async function extractSizes() {
  // Эта функция будет реализована в следующем этапе
  // с использованием сложной логики из технического задания
  console.log('Size extraction not implemented yet');
  return [];
}

/**
 * Валидация данных продукта
 */
function validateProductData(data) {
  const warnings = [];
  const requiredFields = ['name', 'sku', 'price', 'currency'];
  
  let isValid = true;
  
  requiredFields.forEach(field => {
    if (!data[field]) {
      warnings.push(`Отсутствует обязательное поле: ${field}`);
      isValid = false;
    }
  });
  
  if (!data.images || data.images.length === 0) {
    warnings.push('Изображения не найдены');
  }
  
  if (!data.sizes || data.sizes.length === 0) {
    warnings.push('Размеры не найдены');
  }
  
  return {
    isValid: isValid && warnings.length === 0,
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
  
  // Начальная проверка страницы
  isPageValid = isValidProductPage();
  
  if (isPageValid) {
    console.log('Valid product page detected');
    
    // Настройка отслеживания изменений (будет реализовано позже)
    setupChangeTracking();
  }
}

/**
 * Настройка отслеживания изменений (заглушка)
 */
function setupChangeTracking() {
  // Будет реализовано в следующем этапе
  console.log('Change tracking setup - not implemented yet');
}