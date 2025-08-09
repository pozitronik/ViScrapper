/**
 * Popup Script для VIParser Chrome Extension
 * Управляет интерфейсом popup и коммуникацией с background script
 * Использует общую логику из VIParserCore, VIParserUI, VIParserEvents
 */

// Инициализация shared modules
let viParserCore = null;
let viParserUI = null;
let viParserEvents = null;

// Инициализация popup
document.addEventListener('DOMContentLoaded', async () => {
  console.log('VIParser popup initialized');
  
  // Создаем экземпляры shared modules
  viParserCore = new VIParserCore();
  viParserUI = new VIParserUI(viParserCore);
  viParserEvents = new VIParserEvents(viParserCore, viParserUI);
  
  // Инициализация приложения через shared events module
  await viParserEvents.initializeApp({
    setupBranding: true,
    loadSettings: false,
    checkBackend: true,
    loadProductData: true,
    startColorObserver: true,
    closeOnSubmit: true // Popup-specific: close after submit
  });
  
  // Setup cleanup handlers
  viParserEvents.setupCleanupHandlers();
});

// Site detection now handled by VIParserCore.detectSite()
// Branding setup now handled by VIParserEvents.setupSiteBranding()

// Message handling now handled by VIParserEvents.setupMessageListener()
// Product change notifications now handled by VIParserCore.handleProductChangedNotification()
// Color updates now handled by VIParserCore.handleColorUpdate()

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

// Product status checking now handled by VIParserEvents.checkProductStatus()

// Product status updates now handled by VIParserCore.updateProductStatusUI()

// Event handlers setup now handled by VIParserEvents.setupEventHandlers()
// Button state updates now handled by VIParserCore.updateButtonsState()

// Submit handling now handled by VIParserEvents.handleSubmit()

// Color observer functionality now handled by VIParserEvents:
// - startColorObserverIfNeeded()
// - stopColorObserver()
// - setupCleanupHandlers()

