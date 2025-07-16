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
  
  // Определение сайта и применение брендинга
  await setupSiteBranding();
  
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
 * Определение текущего сайта и применение соответствующего брендинга
 */
async function setupSiteBranding() {
  try {
    // Получаем информацию о текущей активной вкладке
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab || !tab.url) {
      console.warn('Could not get current tab URL for branding');
      return;
    }
    
    console.log('Setting up branding for URL:', tab.url);
    
    // Определяем сайт на основе URL
    const siteInfo = detectSite(tab.url);
    console.log('Detected site:', siteInfo);
    
    // Применяем соответствующий класс к body
    document.body.className = `site-${siteInfo.id}`;
    
    // Обновляем заголовок
    const titleElement = document.getElementById('appTitle');
    if (titleElement) {
      titleElement.textContent = `VIParser: ${siteInfo.name}`;
    }
    
    console.log(`Applied branding for ${siteInfo.name}`);
    
  } catch (error) {
    console.error('Error setting up site branding:', error);
  }
}

/**
 * Определение сайта на основе URL
 */
function detectSite(url) {
  if (url.includes('victoriassecret.com')) {
    return {
      id: 'victoriassecret',
      name: "Victoria's Secret"
    };
  } else if (url.includes('calvinklein.us')) {
    return {
      id: 'calvinklein', 
      name: 'Calvin Klein'
    };
  } else {
    // Дефолтный сайт
    return {
      id: 'victoriassecret',
      name: 'VIParser'
    };
  }
}

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
  const commentContainer = document.querySelector('.comment-container');
  commentContainer.style.display = 'none';
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
      const commentContainer = document.querySelector('.comment-container');
      commentContainer.style.display = 'none';
      
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
    const commentContainer = document.querySelector('.comment-container');
    commentContainer.style.display = 'none';
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
          <div class="image-selection-header">
            <div class="selected-count">Выбрано: <span id="selectedCount">0</span>/${data.all_image_urls.length}</div>
            <div class="image-selection-actions">
              <button class="image-selection-btn" id="selectAllBtn">Все</button>
              <button class="image-selection-btn" id="deselectAllBtn">Ничего</button>
            </div>
          </div>
          <div class="images-preview">
            ${data.all_image_urls.map((img, index) => 
              `<div class="image-selector" data-index="${index}">
                <img src="${img}" alt="Product image" class="image-thumbnail">
                <input type="checkbox" class="image-checkbox" data-index="${index}" ${index < 4 ? 'checked' : ''}>
              </div>`
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
    // Комбинации размеров (двухразмерный продукт) - показываем все без сокращений
    const combinations = data.size_combinations.combinations;
    let combinationDisplay = '';
    
    if (Object.keys(combinations).length > 0) {
      const combLines = [];
      for (const [size1, size2Array] of Object.entries(combinations)) {
        combLines.push(`${size1}: ${size2Array.join(', ')}`);
      }
      combinationDisplay = combLines.join('; ');
    }
    
    html += `
      <div class="data-item">
        <div class="data-label">Размеры:</div>
        <div class="data-value">
          <small style="color: #666;">${combinationDisplay}</small>
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
  
  // Настраиваем обработчики для селекции изображений
  setupImageSelection();
}

/**
 * Настройка обработчиков для селекции изображений
 */
function setupImageSelection() {
  const checkboxes = document.querySelectorAll('.image-checkbox');
  const selectAllBtn = document.getElementById('selectAllBtn');
  const deselectAllBtn = document.getElementById('deselectAllBtn');
  const imageSelectors = document.querySelectorAll('.image-selector');
  
  if (checkboxes.length === 0) {
    return; // Нет изображений для настройки
  }
  
  // Обработчики для чекбоксов
  checkboxes.forEach(checkbox => {
    checkbox.addEventListener('change', handleImageSelectionChange);
  });
  
  // Обработчики для кликов по изображениям (для удобства)
  imageSelectors.forEach(selector => {
    selector.addEventListener('click', (e) => {
      if (e.target.type !== 'checkbox') {
        const checkbox = selector.querySelector('.image-checkbox');
        checkbox.checked = !checkbox.checked;
        handleImageSelectionChange();
      }
    });
  });
  
  // Обработчики для кнопок
  if (selectAllBtn) {
    selectAllBtn.addEventListener('click', selectAllImages);
  }
  
  if (deselectAllBtn) {
    deselectAllBtn.addEventListener('click', deselectAllImages);
  }
  
  // Обновляем начальное состояние
  updateImageSelectionUI();
}

/**
 * Обработка изменения выбора изображения
 */
function handleImageSelectionChange() {
  updateImageSelectionUI();
}

/**
 * Обновление интерфейса селекции изображений
 */
function updateImageSelectionUI() {
  const checkboxes = document.querySelectorAll('.image-checkbox');
  const selectedCountSpan = document.getElementById('selectedCount');
  const imageSelectors = document.querySelectorAll('.image-selector');
  
  let selectedCount = 0;
  
  checkboxes.forEach((checkbox, index) => {
    const selector = imageSelectors[index];
    if (checkbox.checked) {
      selectedCount++;
      selector.classList.add('selected');
    } else {
      selector.classList.remove('selected');
    }
  });
  
  if (selectedCountSpan) {
    selectedCountSpan.textContent = selectedCount;
  }
}

/**
 * Выбрать все изображения
 */
function selectAllImages() {
  const checkboxes = document.querySelectorAll('.image-checkbox');
  checkboxes.forEach(checkbox => {
    checkbox.checked = true;
  });
  updateImageSelectionUI();
}

/**
 * Снять выбор со всех изображений
 */
function deselectAllImages() {
  const checkboxes = document.querySelectorAll('.image-checkbox');
  checkboxes.forEach(checkbox => {
    checkbox.checked = false;
  });
  updateImageSelectionUI();
}

/**
 * Получить выбранные изображения
 */
function getSelectedImages() {
  const checkboxes = document.querySelectorAll('.image-checkbox:checked');
  const selectedImages = [];
  
  checkboxes.forEach(checkbox => {
    const index = parseInt(checkbox.dataset.index);
    if (appState.productData && appState.productData.all_image_urls && appState.productData.all_image_urls[index]) {
      selectedImages.push(appState.productData.all_image_urls[index]);
    }
  });
  
  return selectedImages;
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
      statusClass = 'existing';
      
      // Делаем саму надпись ссылкой, если есть URL продукта
      if (statusResponse.productUrl) {
        statusText = `<a href="${statusResponse.productUrl}" target="_blank" style="color: #4ade80; text-decoration: underline;">${statusResponse.message || '✅ Продукт уже существует'}</a>`;
      } else {
        statusText = statusResponse.message || '✅ Уже существует';
      }
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
    // Получаем только выбранные изображения
    const selectedImages = getSelectedImages();
    
    const dataToSend = {
      ...appState.productData,
      comment: commentInput.value.trim(),
      // Заменяем все изображения на выбранные
      all_image_urls: selectedImages,
      main_image_url: selectedImages.length > 0 ? selectedImages[0] : null
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
      // Показываем сообщение с ссылкой на продукт
      const statusCard = document.getElementById('productStatus');
      
      if (response.productUrl && response.message) {
        // Обновляем статус на зеленый с ссылкой
        statusCard.classList.remove('new', 'existing', 'unavailable', 'warning');
        statusCard.classList.add('existing');
        statusCard.innerHTML = `<div class="status-text"><a href="${response.productUrl}" target="_blank" style="color: #4ade80; text-decoration: underline;">${response.message}</a></div>`;
        
        submitBtn.textContent = 'Данные отправлены!';
      } else {
        submitBtn.textContent = 'Данные отправлены!';
      }
      
      setTimeout(() => window.close(), 2000);
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

