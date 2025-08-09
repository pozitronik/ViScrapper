/**
 * Side Panel Script для VIParser Chrome Extension
 * Управляет интерфейсом side panel и коммуникацией с background script
 * Использует общую логику из VIParserCore, VIParserUI, VIParserEvents
 */

// Инициализация shared modules
let viParserCore = null;
let viParserUI = null;
let viParserEvents = null;

// Настройки side panel
let currentSettings = {
  defaultMode: 'sidepanel'
};

// Инициализация side panel
document.addEventListener('DOMContentLoaded', async () => {
  console.log('VIParser side panel initialized');
  
  // Создаем экземпляры shared modules
  viParserCore = new VIParserCore();
  viParserUI = new VIParserUI(viParserCore);
  viParserEvents = new VIParserEvents(viParserCore, viParserUI);
  
  // Загрузка настроек
  await loadSettings();
  
  // Инициализация приложения через shared events module
  await viParserEvents.initializeApp({
    setupBranding: true,
    loadSettings: false, // Already loaded above
    checkBackend: true,
    loadProductData: true,
    startColorObserver: true, // Side panel needs color observer for Tommy Hilfiger image updates
    closeOnSubmit: false, // Side panel-specific: don't close after submit
    onManualRefresh: refreshPanelData // Side panel-specific refresh function
  });
  
  // Setup cleanup handlers
  viParserEvents.setupCleanupHandlers();
});

// Site branding setup now handled by VIParserEvents.setupSiteBranding()

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

// Message handling now handled by VIParserEvents.setupMessageListener() with custom autoRefresh handling

// Auto-refresh handling enhanced in VIParserEvents but handleAutoRefresh still needed for sidepanel-specific logic

// Refresh indication methods now handled by VIParserUI:
// - showRefreshIndication()
// - hideRefreshIndication()
// - showUnsupportedSiteMessage()

/**
 * Перезагрузка данных панели (sidepanel-specific function)
 */
async function refreshPanelData() {
  try {
    // Обновляем брендинг для нового сайта
    const siteInfo = await viParserEvents.setupSiteBranding();
    
    // Если сайт не поддерживается, показываем соответствующее сообщение
    if (!siteInfo.supported) {
      viParserUI.showUnsupportedSiteMessage();
      return;
    }
    
    // Сбрасываем состояние приложения для поддерживаемых сайтов
    if (viParserCore) {
      viParserCore.appState = {
        backendStatus: 'checking',
        productData: null,
        productStatus: null,
        isDataValid: false
      };
    }
    
    // Очищаем превью данных
    viParserUI.showLoadingState('dataPreview', 'Загрузка данных...');
    const previewContainer = document.getElementById('dataPreview');
    previewContainer.style.display = 'block';
    
    // Показываем поле комментария
    const commentContainer = document.querySelector('.comment-container');
    commentContainer.style.display = 'block';
    
    // Проверяем статус бэкенда
    await viParserEvents.checkBackendStatus();
    
    // Загружаем данные продукта
    await viParserEvents.loadProductData();
    
  } catch (error) {
    console.error('Error refreshing panel data:', error);
    
    // Показываем ошибку
    const statusCard = document.getElementById('productStatus');
    statusCard.classList.remove('new', 'existing', 'unavailable', 'warning');
    statusCard.classList.add('warning');
    statusCard.innerHTML = '<div class="status-text">⚠️ Ошибка обновления</div>';
  } finally {
    // Убираем индикацию загрузки
    viParserUI.hideRefreshIndication();
  }
}

// Product change notifications and color updates now handled by VIParserCore methods

// Element initialization now handled by VIParserUI.initializeCommentCounter()

// Backend status checking now handled by VIParserEvents.checkBackendStatus()
// Backend status UI updates now handled by VIParserUI.updateBackendStatusUI()

// Product data loading now handled by VIParserEvents.loadProductData()

// Data preview rendering now handled by VIParserUI.updateDataPreview()

// Image selection functionality now handled by VIParserCore methods:
// - setupImageSelection()
// - handleImageSelectionChange() 
// - updateImageSelectionUI()
// - selectAllImages()
// - deselectAllImages()
// - getSelectedImages()

// Product status checking and updates now handled by VIParserEvents.checkProductStatus() and VIParserCore.updateProductStatusUI()

// Event handlers setup now handled by VIParserEvents.setupEventHandlers() with manual refresh support
// Button state updates now handled by VIParserCore.updateButtonsState()

// Submit handling now handled by VIParserEvents.handleSubmit()

// Color observer functionality now handled by VIParserEvents:
// - startColorObserverIfNeeded()
// - stopColorObserver()
// - setupCleanupHandlers()