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
      handleCheckProductStatus(request.data, sendResponse);
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
async function handleCheckProductStatus(data, sendResponse) {
  try {
    if (!data || (!data.sku && !data.product_url)) {
      sendResponse({ status: 'unknown', message: 'Недостаточно данных для поиска' });
      return;
    }

    // Сначала проверяем по URL (более точно)
    if (data.product_url) {
      const urlSearchResponse = await fetch(`http://localhost:8000/api/v1/products/search?q=${encodeURIComponent(data.product_url)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (urlSearchResponse.ok) {
        const urlResult = await urlSearchResponse.json();
        if (urlResult && urlResult.data && urlResult.data.length > 0) {
          // Ищем по точному совпадению или по сантизированному URL
          const urlMatch = urlResult.data.find(item => {
            if (!item.product_url) return false;
            // Точное совпадение
            if (item.product_url === data.product_url) return true;
            // Сравнение сантизированных URL
            try {
              const itemUrl = new URL(item.product_url);
              const dataUrl = new URL(data.product_url);
              const itemClean = `${itemUrl.protocol}//${itemUrl.host}${itemUrl.pathname}`;
              const dataClean = `${dataUrl.protocol}//${dataUrl.host}${dataUrl.pathname}`;
              return itemClean === dataClean;
            } catch (e) {
              return false;
            }
          });
          if (urlMatch) {
            let message = 'Продукт уже существует';
            if (urlMatch.created_at) {
              try {
                const createdDate = new Date(urlMatch.created_at);
                message = `Продукт уже существует (добавлен ${createdDate.toLocaleString('ru-RU')})`;
              } catch (e) {
                console.warn('Error parsing created_at date:', urlMatch.created_at);
              }
            }
            sendResponse({ 
              status: 'existing', 
              message: message,
              product: urlMatch
            });
            return;
          }
        }
      }
    }

    // Если не найден по URL, проверяем по SKU
    if (data.sku) {
      const skuSearchResponse = await fetch(`http://localhost:8000/api/v1/products/search?q=${encodeURIComponent(data.sku)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (skuSearchResponse.ok) {
        const skuResult = await skuSearchResponse.json();
        if (skuResult && skuResult.data && skuResult.data.length > 0) {
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
            sendResponse({ 
              status: 'existing', 
              message: message,
              product: skuMatch
            });
            return;
          }
        }
      }
    }
    
    // Если не найден ни по URL, ни по SKU
    sendResponse({ 
      status: 'new', 
      message: 'Новый продукт' 
    });
    
  } catch (error) {
    console.error('Error checking product status:', error);
    sendResponse({ status: 'error', message: 'Ошибка проверки продукта' });
  }
}