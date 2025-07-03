/**
 * Background Service Worker для VIParser Chrome Extension
 * Обрабатывает коммуникацию между popup и content script
 */

// Обработка установки расширения
chrome.runtime.onInstalled.addListener(() => {
  console.log('VIParser extension installed');
});

// Обработка сообщений от popup и content script
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
      handleCheckProductStatus(request.sku, sendResponse);
      return true; // Асинхронный ответ
  }
});

/**
 * Получение данных из активной вкладки
 */
async function handleGetTabData(sendResponse) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab.url.includes('victoriassecret.com')) {
      sendResponse({ error: 'Расширение работает только на сайте Victoria\'s Secret' });
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
      sendResponse({ success: true, data: result });
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
async function handleCheckProductStatus(sku, sendResponse) {
  try {
    if (!sku) {
      sendResponse({ status: 'unknown', message: 'SKU не найден' });
      return;
    }

    const searchResponse = await fetch(`http://localhost:8000/api/v1/products/search?q=${encodeURIComponent(sku)}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (!searchResponse.ok) {
      sendResponse({ status: 'error', message: 'Ошибка поиска продукта' });
      return;
    }
    
    const searchResult = await searchResponse.json();
    
    // Проверяем, найден ли продукт с этим SKU
    if (searchResult && searchResult.items && searchResult.items.length > 0) {
      // Ищем точное совпадение по SKU
      const exactMatch = searchResult.items.find(item => item.sku === sku);
      if (exactMatch) {
        sendResponse({ 
          status: 'existing', 
          message: 'Продукт уже существует',
          product: exactMatch
        });
      } else {
        sendResponse({ 
          status: 'new', 
          message: 'Новый продукт' 
        });
      }
    } else {
      sendResponse({ 
        status: 'new', 
        message: 'Новый продукт' 
      });
    }
    
  } catch (error) {
    console.error('Error checking product status:', error);
    sendResponse({ status: 'error', message: 'Ошибка проверки продукта' });
  }
}