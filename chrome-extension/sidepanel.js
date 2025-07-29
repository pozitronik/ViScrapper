/**
 * Side Panel Script для VIParser Chrome Extension
 * Управляет интерфейсом side panel и коммуникацией с background script
 * Использует общую логику из VIParserCore
 */

// Инициализация core и состояния
let viParserCore = null;
let currentSettings = {
  defaultMode: 'sidepanel'
};

// Инициализация side panel
document.addEventListener('DOMContentLoaded', async () => {
  console.log('VIParser side panel initialized');
  
  // Создаем экземпляр core
  viParserCore = new VIParserCore();
  
  // Определение сайта и применение брендинга
  await setupSiteBranding();
  
  // Загрузка настроек
  await loadSettings();
  
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
    const siteInfo = await viParserCore.detectSite();
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
 * Загрузка настроек из chrome.storage
 */
async function loadSettings() {
  try {
    const stored = await chrome.storage.sync.get(['viparserSettings']);
    if (stored.viparserSettings) {
      currentSettings = { ...currentSettings, ...stored.viparserSettings };
    }
    console.log('Loaded settings:', currentSettings);
  } catch (error) {
    console.error('Error loading settings:', error);
  }
}

/**
 * Сохранение настроек в chrome.storage
 */
async function saveSettings() {
  try {
    await chrome.storage.sync.set({ viparserSettings: currentSettings });
    console.log('Settings saved:', currentSettings);
  } catch (error) {
    console.error('Error saving settings:', error);
  }
}

/**
 * Настройка слушателя сообщений от content script и background script
 */
function setupMessageListener() {
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('Side panel received message:', request);
    
    if (request.action === 'productChanged') {
      handleProductChangedNotification(request.reason);
    } else if (request.action === 'updateColorInPopup') {
      handleColorUpdate(request.color);
    } else if (request.action === 'autoRefreshPanel') {
      handleAutoRefresh(request.url);
    }
  });
}

/**
 * Обработка автоматического обновления при смене URL
 */
function handleAutoRefresh(newUrl) {
  console.log('Auto-refresh triggered for URL:', newUrl);
  
  // Показываем индикацию обновления
  showRefreshIndication('Обновление данных...');
  
  // Перезагружаем данные
  refreshPanelData();
}

/**
 * Показать индикацию обновления
 */
function showRefreshIndication(message) {
  const statusCard = document.getElementById('productStatus');
  const refreshBtn = document.getElementById('manualRefreshBtn');
  
  // Добавляем класс загрузки к кнопке
  refreshBtn.classList.add('loading');
  
  // Показываем сообщение в статусе, сохраняя структуру
  statusCard.classList.remove('new', 'existing', 'unavailable', 'warning');
  statusCard.classList.add('warning');
  
  // Ищем существующий status-text или создаем новый
  let statusText = statusCard.querySelector('.status-text');
  if (!statusText) {
    statusCard.innerHTML = `<div class="status-text">${message}</div>`;
  } else {
    statusText.textContent = message;
  }
}

/**
 * Убрать индикацию обновления
 */
function hideRefreshIndication() {
  const refreshBtn = document.getElementById('manualRefreshBtn');
  refreshBtn.classList.remove('loading');
}

/**
 * Перезагрузка данных панели
 */
async function refreshPanelData() {
  try {
    // Обновляем брендинг для нового сайта
    await setupSiteBranding();
    
    // Сбрасываем состояние приложения
    if (viParserCore) {
      viParserCore.appState = {
        backendStatus: 'checking',
        productData: null,
        productStatus: null,
        isDataValid: false
      };
    }
    
    // Очищаем превью данных
    const previewContainer = document.getElementById('dataPreview');
    previewContainer.innerHTML = '<div class="loading">Загрузка данных...</div>';
    previewContainer.style.display = 'block';
    
    // Показываем поле комментария
    const commentContainer = document.querySelector('.comment-container');
    commentContainer.style.display = 'block';
    
    // Проверяем статус бэкенда
    await checkBackendStatus();
    
    // Загружаем данные продукта
    await loadProductData();
    
  } catch (error) {
    console.error('Error refreshing panel data:', error);
    
    // Показываем ошибку
    const statusCard = document.getElementById('productStatus');
    statusCard.classList.remove('new', 'existing', 'unavailable', 'warning');
    statusCard.classList.add('warning');
    statusCard.innerHTML = '<div class="status-text">⚠️ Ошибка обновления</div>';
  } finally {
    // Убираем индикацию загрузки
    hideRefreshIndication();
  }
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
 * Обработка обновления цвета в реальном времени
 */
function handleColorUpdate(color) {
  console.log('Received color update:', color);
  
  // Обновляем данные в состоянии приложения
  if (viParserCore.appState.productData) {
    viParserCore.appState.productData.color = color;
  }
  
  // Находим элемент цвета в превью и обновляем его
  const colorValueElement = document.querySelector('[data-field="color"] .data-value');
  if (colorValueElement) {
    colorValueElement.textContent = color;
    colorValueElement.classList.remove('missing');
    console.log('Updated color in side panel preview:', color);
  }
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
    const response = await viParserCore.checkBackendStatus();
    
    if (response.status === 'available') {
      updateBackendStatus('available', 'Доступен');
    } else {
      updateBackendStatus('unavailable', 'Недоступен');
    }
    
  } catch (error) {
    console.error('Error checking backend status:', error);
    updateBackendStatus('unavailable', 'Ошибка');
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
    
    // Запрос данных через core
    const response = await viParserCore.loadProductData();
    
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
 * Обновление предварительного просмотра данных (оптимизировано для side panel)
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
    { key: 'availability', label: 'Доступность', format: (value) => viParserCore.formatAvailability(value) },
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
      <div class="data-item" data-field="${field.key}">
        <div class="data-label">${field.label}:</div>
        <div class="data-value ${hasValue ? '' : 'missing'}">
          ${displayValue}
        </div>
      </div>
    `;
  });
  
  // Добавляем изображения (с уменьшенным размером для компактности)
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
    html += `
      <div class="data-item">
        <div class="data-label">Размеры:</div>
        <div class="data-value">${data.available_sizes.join(', ')}</div>
      </div>
    `;
  } else if (data.size_combinations && data.size_combinations.combinations) {
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
    return;
  }
  
  // Обработчики для чекбоксов
  checkboxes.forEach(checkbox => {
    checkbox.addEventListener('change', handleImageSelectionChange);
  });
  
  // Обработчики для кликов по изображениям
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
 * Проверка статуса продукта на бэкенде
 */
async function checkProductStatus(data) {
  try {
    const response = await viParserCore.checkProductStatus(data);
    updateProductStatus(null, response);
    
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
  const manualRefreshBtn = document.getElementById('manualRefreshBtn');
  
  // Кнопка отправки
  submitBtn.addEventListener('click', async () => {
    await handleSubmit();
  });
  
  // Кнопка обновления страницы (старая)
  refreshBtn.addEventListener('click', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      chrome.tabs.reload(tabs[0].id);
    });
  });
  
  // Кнопка ручного обновления данных (новая)
  manualRefreshBtn.addEventListener('click', () => {
    console.log('Manual refresh button clicked');
    
    // Показываем индикацию обновления
    showRefreshIndication('Обновление данных...');
    
    // Перезагружаем данные
    refreshPanelData();
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
  
  const canSubmit = viParserCore.canSubmitData();
  submitBtn.disabled = !canSubmit;
  submitBtn.textContent = viParserCore.getSubmitButtonText();
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
    const selectedImages = viParserCore.getSelectedImages();
    
    const dataToSend = {
      ...viParserCore.appState.productData,
      comment: commentInput.value.trim(),
      // Заменяем все изображения на выбранные
      all_image_urls: selectedImages,
      main_image_url: selectedImages.length > 0 ? selectedImages[0] : null
    };
    
    const response = await viParserCore.submitData(dataToSend);
    
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
      
      // Сбрасываем форму через 2 секунды
      setTimeout(() => {
        updateButtons();
        commentInput.value = '';
        commentInput.dispatchEvent(new Event('input')); // Trigger char counter update
      }, 2000);
    }
    
  } catch (error) {
    console.error('Error submitting data:', error);
    submitBtn.textContent = 'Ошибка отправки - попробуйте снова';
    setTimeout(() => {
      updateButtons();
    }, 3000);
  } finally {
    submitBtn.disabled = false;
  }
}

/**
 * Запуск наблюдателя за цветом если нужно (для Carter's и если цвет отсутствует)
 */
async function startColorObserverIfNeeded() {
  try {
    // Получаем информацию о текущей активной вкладке
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab || !tab.url) {
      return;
    }
    
    // Проверяем, что это Carter's
    if (!tab.url.includes('carters.com')) {
      console.log('Not Carter\'s site, skipping color observer');
      return;
    }
    
    // Проверяем, нужен ли observer (если цвет отсутствует)
    const colorValueElement = document.querySelector('[data-field="color"] .data-value');
    if (colorValueElement) {
      const colorText = colorValueElement.textContent.trim();
      if (colorText === 'Отсутствует' || colorText === '' || colorValueElement.classList.contains('missing')) {
        console.log('Color is missing, starting observer...');
        
        const response = await viParserCore.startColorObserver();
        
        if (response.success) {
          console.log('Color observer started successfully');
        } else {
          console.log('Failed to start color observer:', response.error);
        }
      } else {
        console.log('Color already available:', colorText);
      }
    }
    
  } catch (error) {
    console.error('Error starting color observer:', error);
  }
}

// Останавливаем observer при закрытии side panel
window.addEventListener('beforeunload', () => {
  if (viParserCore) {
    viParserCore.stopColorObserver();
  }
});

// После загрузки данных запускаем color observer если нужно
document.addEventListener('dataLoaded', () => {
  startColorObserverIfNeeded();
});