/**
 * Popup Script для VIParser Chrome Extension
 * Управляет интерфейсом popup и коммуникацией с background script
 */

// Состояние приложения
let appState = {
  backendStatus: 'checking',
  productData: null,
  productStatus: null,
  isDataValid: false
};

// Инициализация popup
document.addEventListener('DOMContentLoaded', async () => {
  console.log('VIParser popup initialized');
  
  // Инициализация элементов
  initializeElements();
  
  // Настройка слушателя сообщений от content script
  setupMessageListener();
  
  // Проверка статуса бэкенда
  await checkBackendStatus();
  
  // Загрузка данных продукта
  await loadProductData();
  
  // Настройка обработчиков событий
  setupEventHandlers();
});

/**
 * Настройка слушателя сообщений от content script
 */
function setupMessageListener() {
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Popup received message:', request);
    
    if (request.action === 'productChanged') {
      handleProductChangedNotification(request.reason);
    }
  });
}

/**
 * Обработка уведомления о смене продукта
 */
function handleProductChangedNotification(reason) {
  console.log('Product changed notification received:', reason);
  
  // Показываем статус в блоке статуса
  updateProductStatus(null, { 
    status: 'changed', 
    message: 'Нужно обновить страницу' 
  });
  
  // Показываем кнопку обновления, скрываем кнопку отправки
  const refreshBtn = document.getElementById('refreshBtn');
  const submitBtn = document.getElementById('submitBtn');
  
  refreshBtn.style.display = 'block';
  submitBtn.style.display = 'none';
  
  // Скрываем превью данных
  const previewContainer = document.getElementById('dataPreview');
  previewContainer.style.display = 'none';
  
  // Скрываем поле комментария
  const commentInput = document.getElementById('commentInput');
  const charCounter = document.querySelector('.char-counter');
  commentInput.style.display = 'none';
  charCounter.style.display = 'none';
}

/**
 * Инициализация элементов интерфейса
 */
function initializeElements() {
  const commentInput = document.getElementById('commentInput');
  const charCount = document.getElementById('charCount');
  
  // Счетчик символов для комментария
  commentInput.addEventListener('input', () => {
    const count = commentInput.value.length;
    charCount.textContent = count;
    
    const counter = document.querySelector('.char-counter');
    counter.classList.toggle('warning', count > 400);
    counter.classList.toggle('error', count > 500);
  });
}

/**
 * Проверка статуса бэкенда
 */
async function checkBackendStatus() {
  updateBackendStatus('checking', 'Проверка...');
  
  try {
    const response = await new Promise((resolve) => {
      chrome.runtime.sendMessage(
        { action: 'checkBackendStatus' },
        resolve
      );
    });
    
    if (response.status === 'available') {
      updateBackendStatus('available', 'Доступен');
    } else {
      updateBackendStatus('unavailable', 'Недоступен');
    }
    
    appState.backendStatus = response.status;
  } catch (error) {
    console.error('Error checking backend status:', error);
    updateBackendStatus('unavailable', 'Ошибка');
    appState.backendStatus = 'unavailable';
  }
}

/**
 * Обновление индикатора статуса бэкенда
 */
function updateBackendStatus(status, text) {
  const statusElement = document.getElementById('backendStatus');
  const dot = statusElement.querySelector('.status-dot');
  const textElement = statusElement.querySelector('.status-text');
  
  // Удаляем старые классы
  dot.classList.remove('available', 'unavailable', 'checking');
  
  // Добавляем новый класс
  if (status) {
    dot.classList.add(status);
  }
  
  textElement.textContent = text;
}

/**
 * Загрузка данных продукта
 */
async function loadProductData() {
  const previewContainer = document.getElementById('dataPreview');
  const productStatus = document.getElementById('productStatus');
  
  try {
    previewContainer.innerHTML = '<div class="loading">Загрузка данных...</div>';
    productStatus.innerHTML = '<div class="loading">Проверка статуса...</div>';
    
    // Запрос данных через background script
    const response = await new Promise((resolve) => {
      chrome.runtime.sendMessage(
        { action: 'getTabData' },
        resolve
      );
    });
    
    if (response.error) {
      // Скрываем превью данных при ошибке
      previewContainer.style.display = 'none';
      
      // Показываем ошибку в статусе продукта
      if (response.needsRefresh) {
        updateProductStatus(null, { 
          status: 'changed', 
          message: 'Нужно обновить страницу' 
        });
      } else {
        updateProductStatus(null, { 
          status: 'error', 
          message: 'Не удалось загрузить данные' 
        });
      }
      
      // Скрываем поле комментария
      const commentInput = document.getElementById('commentInput');
      const charCounter = document.querySelector('.char-counter');
      commentInput.style.display = 'none';
      charCounter.style.display = 'none';
      
      return;
    }
    
    appState.productData = response.data;
    appState.isDataValid = response.isValid;
    
    // Обновляем интерфейс
    updateDataPreview(response.data);
    
    // Проверяем статус продукта на бэкенде
    if (response.data && (response.data.sku || response.data.product_url)) {
      await checkProductStatus(response.data);
    } else {
      updateProductStatus(null, { status: 'unknown', message: 'Недостаточно данных для поиска' });
    }
    
  } catch (error) {
    console.error('Error loading product data:', error);
    
    // Скрываем превью данных
    previewContainer.style.display = 'none';
    
    // Показываем ошибку в статусе
    updateProductStatus(null, { 
      status: 'error', 
      message: 'Не удалось загрузить данные' 
    });
    
    // Скрываем поле комментария
    const commentInput = document.getElementById('commentInput');
    const charCounter = document.querySelector('.char-counter');
    commentInput.style.display = 'none';
    charCounter.style.display = 'none';
  }
}

/**
 * Обновление предварительного просмотра данных
 */
function updateDataPreview(data) {
  const container = document.getElementById('dataPreview');
  
  if (!data) {
    container.innerHTML = '<div class="error">Нет данных для отображения</div>';
    return;
  }
  
  const fields = [
    { key: 'name', label: 'Название' },
    { key: 'sku', label: 'SKU' },
    { key: 'price', label: 'Цена', format: (value, data) => value ? `${value} ${data.currency || 'USD'}` : value },
    { key: 'availability', label: 'Доступность', format: (value) => {
      const availabilityMap = {
        'InStock': '✅ В наличии',
        'OutOfStock': '❌ Нет в наличии', 
        'SoldOut': '❌ Распродано',
        'PreOrder': '⏰ Предзаказ',
        'PreSale': '⏰ Предпродажа',
        'BackOrder': '📦 Под заказ',
        'MadeToOrder': '🔨 Изготовление на заказ',
        'Discontinued': '🚫 Снят с производства',
        'InStoreOnly': '🏪 Только в магазине',
        'OnlineOnly': '💻 Только онлайн',
        'LimitedAvailability': '⚠️ Ограниченная доступность',
        'Reserved': '🔒 Зарезервировано'
      };
      
      return availabilityMap[value] || `❓ ${value}`;
    }},
    { key: 'color', label: 'Цвет' },
    { key: 'composition', label: 'Состав' },
    { key: 'item', label: 'Артикул' }
  ];
  
  let html = '';
  
  fields.forEach(field => {
    const value = data[field.key];
    const hasValue = value !== undefined && value !== null && value !== '';
    
    let displayValue = hasValue ? value : 'Отсутствует';
    if (hasValue && field.format) {
      displayValue = field.format(value, data);
    }
    
    html += `
      <div class="data-item">
        <div class="data-label">${field.label}:</div>
        <div class="data-value ${hasValue ? '' : 'missing'}">
          ${displayValue}
        </div>
      </div>
    `;
  });
  
  // Добавляем изображения
  if (data.all_image_urls && data.all_image_urls.length > 0) {
    html += `
      <div class="data-item">
        <div class="data-label">Изображения:</div>
        <div class="data-value">
          <div class="images-preview">
            ${data.all_image_urls.slice(0, 6).map(img => 
              `<img src="${img}" alt="Product image" class="image-thumbnail">`
            ).join('')}
          </div>
          <div class="images-count">Всего: ${data.all_image_urls.length}</div>
        </div>
      </div>
    `;
  } else {
    html += `
      <div class="data-item">
        <div class="data-label">Изображения:</div>
        <div class="data-value missing">Отсутствуют</div>
      </div>
    `;
  }
  
  // Добавляем размеры
  if (data.available_sizes && data.available_sizes.length > 0) {
    // Простые размеры (одноразмерный продукт)
    html += `
      <div class="data-item">
        <div class="data-label">Размеры:</div>
        <div class="data-value">${data.available_sizes.join(', ')}</div>
      </div>
    `;
  } else if (data.size_combinations && data.size_combinations.combinations) {
    // Комбинации размеров (двухразмерный продукт)
    const combinationCount = Object.keys(data.size_combinations.combinations).length;
    let combinationPreview = '';
    
    if (combinationCount > 0) {
      const firstKey = Object.keys(data.size_combinations.combinations)[0];
      const firstCombination = data.size_combinations.combinations[firstKey];
      combinationPreview = `${firstKey}: ${firstCombination.slice(0, 3).join(', ')}${firstCombination.length > 3 ? '...' : ''}`;
      if (combinationCount > 1) {
        combinationPreview += ` (+${combinationCount - 1} др.)`;
      }
    }
    
    html += `
      <div class="data-item">
        <div class="data-label">Размеры:</div>
        <div class="data-value">
          <small style="color: #666;">${combinationPreview}</small>
        </div>
      </div>
    `;
  } else {
    html += `
      <div class="data-item">
        <div class="data-label">Размеры:</div>
        <div class="data-value missing">Не найдены</div>
      </div>
    `;
  }
  
  container.innerHTML = html;
}

/**
 * Проверка статуса продукта на бэкенде
 */
async function checkProductStatus(data) {
  try {
    const response = await new Promise((resolve) => {
      chrome.runtime.sendMessage(
        { action: 'checkProductStatus', data: data },
        resolve
      );
    });
    
    updateProductStatus(null, response);
    appState.productStatus = response.status;
    
  } catch (error) {
    console.error('Error checking product status:', error);
    updateProductStatus(null, { status: 'error', message: 'Не удалось проверить статус' });
  }
}

/**
 * Обновление статуса продукта
 */
function updateProductStatus(data, statusResponse) {
  const statusCard = document.getElementById('productStatus');
  
  // Удаляем старые классы
  statusCard.classList.remove('new', 'existing', 'unavailable', 'warning');
  
  if (!statusResponse) {
    statusCard.innerHTML = `<div class="status-text">Проверяется...</div>`;
    statusCard.classList.add('warning');
    return;
  }
  
  let statusText = '';
  let statusClass = '';
  
  switch (statusResponse.status) {
    case 'new':
      statusText = statusResponse.message || '🆕 Новый продукт';
      statusClass = 'new';
      break;
    case 'existing':
      statusText = statusResponse.message || '✅ Уже существует';
      statusClass = 'existing';
      break;
    case 'unavailable':
      statusText = statusResponse.message || '❌ Бэкенд недоступен';
      statusClass = 'unavailable';
      break;
    case 'error':
      statusText = statusResponse.message || '⚠️ Не удалось проверить';
      statusClass = 'warning';
      break;
    case 'changed':
      statusText = statusResponse.message || '🔄 Нужно обновить страницу';
      statusClass = 'warning';
      break;
    default:
      statusText = statusResponse.message || '❓ Неизвестно';
      statusClass = 'warning';
  }
  
  statusCard.innerHTML = `<div class="status-text">${statusText}</div>`;
  statusCard.classList.add(statusClass);
  
  // Специальная обработка для случая изменения продукта
  if (statusResponse && statusResponse.status === 'changed') {
    const refreshBtn = document.getElementById('refreshBtn');
    const submitBtn = document.getElementById('submitBtn');
    
    refreshBtn.style.display = 'block';
    submitBtn.style.display = 'none';
  } else {
    // Обновляем состояние кнопок для других случаев
    updateButtons();
  }
}

/**
 * Настройка обработчиков событий
 */
function setupEventHandlers() {
  const submitBtn = document.getElementById('submitBtn');
  const refreshBtn = document.getElementById('refreshBtn');
  
  // Кнопка отправки
  submitBtn.addEventListener('click', async () => {
    await handleSubmit();
  });
  
  // Кнопка обновления
  refreshBtn.addEventListener('click', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      chrome.tabs.reload(tabs[0].id);
      window.close();
    });
  });
  
  // Обновление состояния кнопок
  updateButtons();
}

/**
 * Обновление состояния кнопок
 */
function updateButtons() {
  const submitBtn = document.getElementById('submitBtn');
  const refreshBtn = document.getElementById('refreshBtn');
  
  // Если показывается кнопка обновления, не трогаем состояние
  if (refreshBtn.style.display !== 'none') {
    return;
  }
  
  // Показываем кнопку отправки, скрываем кнопку обновления
  submitBtn.style.display = 'block';
  refreshBtn.style.display = 'none';
  
  const canSubmit = appState.backendStatus === 'available' && 
                   appState.productData && 
                   appState.isDataValid;
  
  submitBtn.disabled = !canSubmit;
  
  if (!canSubmit) {
    if (appState.backendStatus !== 'available') {
      submitBtn.textContent = 'Бэкенд недоступен';
    } else if (!appState.productData) {
      submitBtn.textContent = 'Нет данных';
    } else if (!appState.isDataValid) {
      submitBtn.textContent = 'Данные некорректны';
    }
  } else {
    // Проверяем статус продукта для определения текста кнопки
    if (appState.productStatus === 'existing') {
      submitBtn.textContent = 'Повторно отправить';
    } else {
      submitBtn.textContent = 'Отправить данные';
    }
  }
}

/**
 * Обработка отправки данных
 */
async function handleSubmit() {
  const submitBtn = document.getElementById('submitBtn');
  const commentInput = document.getElementById('commentInput');
  
  submitBtn.disabled = true;
  submitBtn.textContent = 'Отправка...';
  
  try {
    const dataToSend = {
      ...appState.productData,
      comment: commentInput.value.trim()
    };
    
    const response = await new Promise((resolve) => {
      chrome.runtime.sendMessage(
        { action: 'sendToBackend', data: dataToSend },
        resolve
      );
    });
    
    if (response.error) {
      // Показываем ошибку в кнопке
      submitBtn.textContent = 'Ошибка отправки - попробуйте снова';
      setTimeout(() => {
        updateButtons();
      }, 3000);
    } else {
      submitBtn.textContent = 'Данные отправлены!';
      setTimeout(() => window.close(), 1500);
    }
    
  } catch (error) {
    console.error('Error submitting data:', error);
    // Показываем ошибку в кнопке
    submitBtn.textContent = 'Ошибка отправки - попробуйте снова';
    setTimeout(() => {
      updateButtons();
    }, 3000);
  } finally {
    submitBtn.disabled = false;
  }
}

