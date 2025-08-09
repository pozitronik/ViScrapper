/**
 * Background Service Worker для VIParser Chrome Extension
 * Обрабатывает коммуникацию между popup, side panel и content script
 * Поддерживает двойной режим работы (popup + side panel)
 */

// Поддерживаемые сайты - единый источник истины
const SUPPORTED_SITES = {
  domains: ['victoriassecret.com', 'calvinklein.us', 'carters.com', 'usa.tommy.com'],
  urlPatterns: [
    'https://www.victoriassecret.com/*',
    'https://www.calvinklein.us/*',
    'https://www.carters.com/*',
    'https://usa.tommy.com/*'
  ]
};

// Глобальные настройки расширения
let extensionSettings = {
  defaultMode: 'sidepanel'
};

// Вспомогательная функция для проверки поддержки сайта
function isSiteSupported(url) {
  return SUPPORTED_SITES.domains.some(site => url && url.includes(site));
}

// Обработка установки расширения
chrome.runtime.onInstalled.addListener(async () => {
  console.log('VIParser extension installed');
  
  // Загружаем настройки
  await loadSettings();
  
  // Создаем контекстное меню
  createContextMenu();
});

// Загрузка настроек из storage
async function loadSettings() {
  try {
    const stored = await chrome.storage.sync.get(['viparserSettings']);
    if (stored.viparserSettings) {
      extensionSettings = { ...extensionSettings, ...stored.viparserSettings };
    }
    console.log('Background loaded settings:', extensionSettings);
  } catch (error) {
    console.error('Error loading settings in background:', error);
  }
}

// Создание контекстного меню
function createContextMenu() {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({
      id: 'openVIParser',
      title: 'Открыть VIParser',
      contexts: ['page'],
      documentUrlPatterns: SUPPORTED_SITES.urlPatterns
    });
    
    chrome.contextMenus.create({
      id: 'openSidePanel',
      title: 'Открыть боковую панель',
      contexts: ['page'],
      documentUrlPatterns: SUPPORTED_SITES.urlPatterns
    });
    
    chrome.contextMenus.create({
      id: 'openPopup',
      title: 'Открыть popup',
      contexts: ['page'],
      documentUrlPatterns: SUPPORTED_SITES.urlPatterns
    });
  });
}

// Обработка кликов по контекстному меню
chrome.contextMenus.onClicked.addListener((info, tab) => {
  switch (info.menuItemId) {
    case 'openVIParser':
      if (extensionSettings.defaultMode === 'sidepanel') {
        chrome.sidePanel.open({ tabId: tab.id });
      } else {
        chrome.action.openPopup();
      }
      break;
    case 'openSidePanel':
      chrome.sidePanel.open({ tabId: tab.id });
      break;
    case 'openPopup':
      chrome.action.openPopup();
      break;
  }
});

// Обработка клавиатурных сочетаний
chrome.commands.onCommand.addListener((command) => {
  chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
    // Проверяем, что мы на поддерживаемом сайте
    const isSupportedSite = isSiteSupported(tab.url);
    
    if (!isSupportedSite) {
      console.log('Keyboard shortcut ignored - not on supported site');
      return;
    }
    
    switch (command) {
      case 'open-side-panel':
        chrome.sidePanel.open({ tabId: tab.id });
        break;
      case 'toggle-viparser':
        if (extensionSettings.defaultMode === 'sidepanel') {
          chrome.sidePanel.open({ tabId: tab.id });
        } else {
          chrome.action.openPopup();
        }
        break;
    }
  });
});

// Обработка изменений URL для автоматического обновления панели
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Проверяем только изменения URL
  if (!changeInfo.url) {
    return;
  }
  
  console.log('URL changed to:', changeInfo.url);
  
  // Проверяем, что это поддерживаемый сайт
  const isSupportedSite = isSiteSupported(changeInfo.url);
  
  // Отправляем сообщение в side panel о смене URL (независимо от поддержки)
  // Панель сама решит, что делать с неподдерживаемыми сайтами
  console.log(`URL change detected (supported: ${isSupportedSite}), sending refresh signal`);
  
  chrome.runtime.sendMessage({
    action: 'autoRefreshPanel',
    url: changeInfo.url,
    tabId: tabId,
    supported: isSupportedSite
  }).catch(error => {
    console.log('Could not send auto-refresh message (panel probably not open)');
  });
});

// Обработка сообщений от popup, side panel и content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Background received message:', request);
  
  switch (request.action) {
    case 'getTabData':
      // Получение данных из активной вкладки
      handleGetTabData(sendResponse);
      return true; // Асинхронный ответ
      
    case 'sendToBackend':
      // Отправка данных на бэкенд
      handleSendToBackend(request.data, sendResponse);
      return true; // Асинхронный ответ
      
    case 'checkBackendStatus':
      // Проверка статуса бэкенда
      handleCheckBackendStatus(sendResponse);
      return true; // Асинхронный ответ
      
    case 'checkProductStatus':
      // Проверка статуса продукта
      handleCheckProductStatus(request.data, sendResponse);
      return true; // Асинхронный ответ
      
    case 'startColorObserver':
      // Запуск наблюдателя за цветом
      handleStartColorObserver(sendResponse);
      return true; // Асинхронный ответ
      
    case 'stopColorObserver':
      // Остановка наблюдателя за цветом
      handleStopColorObserver(sendResponse);
      return true; // Асинхронный ответ
      
    case 'colorUpdated':
      // Обновление цвета от content script - пересылаем в popup и side panel
      handleColorUpdated(request, sendResponse);
      return false; // Синхронный ответ
      
    case 'settingsChanged':
      // Обновление настроек от side panel или popup
      handleSettingsChanged(request.settings, sendResponse);
      return false; // Синхронный ответ
  }
});

/**
 * Получение данных из активной вкладки
 */
async function handleGetTabData(sendResponse) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Проверяем, поддерживается ли сайт
    const isSupportedSite = isSiteSupported(tab.url);
    
    if (!isSupportedSite) {
      sendResponse({ error: 'Расширение работает только на поддерживаемых сайтах: ' + SUPPORTED_SITES.domains.join(', ') });
      return;
    }
    
    // Отправка запроса к content script
    chrome.tabs.sendMessage(tab.id, { action: 'extractData' }, (response) => {
      if (chrome.runtime.lastError) {
        sendResponse({ error: 'Не удалось получить данные со страницы' });
      } else {
        sendResponse(response);
      }
    });
  } catch (error) {
    sendResponse({ error: 'Ошибка при получении данных вкладки' });
  }
}

/**
 * Отправка данных на бэкенд
 */
async function handleSendToBackend(data, sendResponse) {
  try {
    const response = await fetch('http://localhost:8000/api/v1/scrape', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    });
    
    if (response.ok) {
      const result = await response.json();
      
      // Формируем правильное сообщение для новых продуктов
      let message = 'Продукт успешно отправлен!';
      let productUrl = null;
      
      if (result && result.id) {
        productUrl = `http://localhost:8000/product/${result.id}`;
        
        if (result.created_at) {
          try {
            const createdDate = new Date(result.created_at);
            message = `Продукт успешно создан (добавлен ${createdDate.toLocaleString('ru-RU')})`;
          } catch (e) {
            console.warn('Error parsing created_at date:', result.created_at);
            message = 'Продукт успешно создан';
          }
        } else {
          message = 'Продукт успешно создан';
        }
      }
      
      sendResponse({ 
        success: true, 
        data: result,
        message: message,
        productUrl: productUrl
      });
    } else {
      sendResponse({ error: `Ошибка сервера: ${response.status}` });
    }
  } catch (error) {
    sendResponse({ error: 'Бэкенд недоступен' });
  }
}

/**
 * Проверка статуса бэкенда и поиск продукта
 */
async function handleCheckBackendStatus(sendResponse) {
  try {
    // Проверка доступности бэкенда
    const healthResponse = await fetch('http://localhost:8000/api/v1/health', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (!healthResponse.ok) {
      sendResponse({ status: 'unavailable', message: 'Бэкенд недоступен' });
      return;
    }
    
    sendResponse({ status: 'available', message: 'Бэкенд доступен' });
  } catch (error) {
    sendResponse({ status: 'unavailable', message: 'Бэкенд недоступен' });
  }
}

/**
 * Проверка статуса продукта (существует ли уже в базе)
 */
async function handleCheckProductStatus(data, sendResponse) {
  try {
    if (!data || !data.sku) {
      sendResponse({ status: 'unknown', message: 'SKU обязателен для поиска продукта' });
      return;
    }

    console.log('Checking product status by SKU:', data.sku);

    // Проверяем только по SKU (надежный метод)
    const skuSearchResponse = await fetch(`http://localhost:8000/api/v1/products/search?sku=${encodeURIComponent(data.sku)}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (skuSearchResponse.ok) {
      const skuResult = await skuSearchResponse.json();
      if (skuResult && skuResult.data && skuResult.data.length > 0) {
        // Ищем точное совпадение по SKU
        const skuMatch = skuResult.data.find(item => item.sku === data.sku);
        if (skuMatch) {
          let message = 'Продукт уже существует';
          if (skuMatch.created_at) {
            try {
              const createdDate = new Date(skuMatch.created_at);
              message = `Продукт уже существует (добавлен ${createdDate.toLocaleString('ru-RU')})`;
            } catch (e) {
              console.warn('Error parsing created_at date:', skuMatch.created_at);
            }
          }
          
          const productLink = `http://localhost:8000/product/${skuMatch.id}`;
          
          sendResponse({ 
            status: 'existing', 
            message: message,
            product: skuMatch,
            productUrl: productLink
          });
          return;
        }
      }
    } else {
      console.warn('SKU search request failed:', skuSearchResponse.status);
    }
    
    // Если не найден по SKU
    sendResponse({ 
      status: 'new', 
      message: 'Новый продукт' 
    });
    
  } catch (error) {
    console.error('Error checking product status:', error);
    sendResponse({ status: 'error', message: 'Ошибка проверки продукта' });
  }
}

/**
 * Запуск наблюдателя за цветом на активной вкладке
 */
async function handleStartColorObserver(sendResponse) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    chrome.tabs.sendMessage(tab.id, { action: 'startColorObserver' }, (response) => {
      if (chrome.runtime.lastError) {
        sendResponse({ error: 'Не удалось запустить наблюдатель за цветом' });
      } else {
        sendResponse(response);
      }
    });
  } catch (error) {
    sendResponse({ error: 'Ошибка при запуске наблюдателя за цветом' });
  }
}

/**
 * Остановка наблюдателя за цветом на активной вкладке
 */
async function handleStopColorObserver(sendResponse) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    chrome.tabs.sendMessage(tab.id, { action: 'stopColorObserver' }, (response) => {
      if (chrome.runtime.lastError) {
        sendResponse({ error: 'Не удалось остановить наблюдатель за цветом' });
      } else {
        sendResponse(response);
      }
    });
  } catch (error) {
    sendResponse({ error: 'Ошибка при остановке наблюдателя за цветом' });
  }
}

/**
 * Обработка обновления цвета от content script
 */
function handleColorUpdated(request, sendResponse) {
  console.log('Color updated from content script:', request.color);
  
  // Отправляем обновление в popup и side panel, если они открыты
  try {
    chrome.runtime.sendMessage({
      action: 'updateColorInPopup',
      color: request.color
    });
  } catch (error) {
    console.log('Could not send color update to popup/side panel (probably closed)');
  }
  
  sendResponse({ success: true });
}

/**
 * Обработка изменения настроек
 */
async function handleSettingsChanged(newSettings, sendResponse) {
  console.log('Settings changed:', newSettings);
  
  // Обновляем глобальные настройки
  extensionSettings = { ...extensionSettings, ...newSettings };
  
  // Пересоздаем контекстное меню с новыми настройками
  createContextMenu();
  
  sendResponse({ success: true });
}