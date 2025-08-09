/**
 * VIParser UI - Shared rendering functionality for popup and side panel
 * Handles data preview rendering and UI updates
 */

class VIParserUI {
  constructor(viParserCore) {
    this.core = viParserCore;
  }

  /**
   * Обновление предварительного просмотра данных (универсальная версия)
   */
  updateDataPreview(data, containerId = 'dataPreview') {
    const container = document.getElementById(containerId);
    
    if (!container) {
      console.error(`Container ${containerId} not found`);
      return;
    }
    
    if (!data) {
      container.innerHTML = '<div class="error">Нет данных для отображения</div>';
      return;
    }
    
    const fields = [
      { key: 'name', label: 'Название' },
      { key: 'sku', label: 'SKU' },
      { key: 'price', label: 'Цена', format: (value, data) => value ? `${value} ${data.currency || 'USD'}` : value },
      { key: 'availability', label: 'Доступность', format: (value) => this.core.formatAvailability(value) },
      { key: 'color', label: 'Цвет' },
      { key: 'composition', label: 'Состав' },
      { key: 'item', label: 'Артикул' }
    ];
    
    let html = '';
    
    // Render basic fields
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
    
    // Add images section
    html += this.renderImagesSection(data);
    
    // Add sizes section
    html += this.renderSizesSection(data);
    
    container.innerHTML = html;
    
    // Setup image selection handlers using VIParserCore
    this.core.setupImageSelection();
  }

  /**
   * Рендеринг секции изображений
   */
  renderImagesSection(data) {
    if (data.all_image_urls && data.all_image_urls.length > 0) {
      return `
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
      return `
        <div class="data-item">
          <div class="data-label">Изображения:</div>
          <div class="data-value missing">Отсутствуют</div>
        </div>
      `;
    }
  }

  /**
   * Рендеринг секции размеров
   */
  renderSizesSection(data) {
    if (data.available_sizes && data.available_sizes.length > 0) {
      // Simple sizes (single-dimensional product)
      return `
        <div class="data-item">
          <div class="data-label">Размеры:</div>
          <div class="data-value">${data.available_sizes.join(', ')}</div>
        </div>
      `;
    } else if (data.size_combinations && data.size_combinations.combinations) {
      // Size combinations (two-dimensional product)
      const combinations = data.size_combinations.combinations;
      let combinationDisplay = '';
      
      if (Object.keys(combinations).length > 0) {
        const combLines = [];
        for (const [size1, size2Array] of Object.entries(combinations)) {
          combLines.push(`${size1}: ${size2Array.join(', ')}`);
        }
        combinationDisplay = combLines.join('; ');
      }
      
      return `
        <div class="data-item">
          <div class="data-label">Размеры:</div>
          <div class="data-value">
            <small style="color: #666;">${combinationDisplay}</small>
          </div>
        </div>
      `;
    } else {
      return `
        <div class="data-item">
          <div class="data-label">Размеры:</div>
          <div class="data-value missing">Не найдены</div>
        </div>
      `;
    }
  }

  /**
   * Обновление индикатора статуса бэкенда
   */
  updateBackendStatusUI(status, text, elementId = 'backendStatus') {
    const statusElement = document.getElementById(elementId);
    if (!statusElement) return;
    
    const dot = statusElement.querySelector('.status-dot');
    const textElement = statusElement.querySelector('.status-text');
    
    if (!dot || !textElement) return;
    
    // Remove old classes
    dot.classList.remove('available', 'unavailable', 'checking');
    
    // Add new class
    if (status) {
      dot.classList.add(status);
    }
    
    textElement.textContent = text;
  }

  /**
   * Инициализация счетчика символов для комментария
   */
  initializeCommentCounter(inputId = 'commentInput', counterId = 'charCount') {
    const commentInput = document.getElementById(inputId);
    const charCount = document.getElementById(counterId);
    
    if (!commentInput || !charCount) return;
    
    // Character counter for comment
    commentInput.addEventListener('input', () => {
      const count = commentInput.value.length;
      charCount.textContent = count;
      
      const counter = document.querySelector('.char-counter');
      if (counter) {
        counter.classList.toggle('warning', count > 400);
        counter.classList.toggle('error', count > 500);
      }
    });
  }

  /**
   * Показать индикацию обновления
   */
  showRefreshIndication(message, statusElementId = 'productStatus', refreshBtnId = 'manualRefreshBtn') {
    const statusCard = document.getElementById(statusElementId);
    const refreshBtn = document.getElementById(refreshBtnId);
    
    // Add loading class to refresh button
    if (refreshBtn) {
      refreshBtn.classList.add('loading');
    }
    
    // Show message in status, preserving structure
    if (statusCard) {
      statusCard.classList.remove('new', 'existing', 'unavailable', 'warning');
      statusCard.classList.add('warning');
      
      // Find existing status-text or create new one
      let statusText = statusCard.querySelector('.status-text');
      if (!statusText) {
        statusCard.innerHTML = `<div class="status-text">${message}</div>`;
      } else {
        statusText.textContent = message;
      }
    }
  }

  /**
   * Убрать индикацию обновления
   */
  hideRefreshIndication(refreshBtnId = 'manualRefreshBtn') {
    const refreshBtn = document.getElementById(refreshBtnId);
    if (refreshBtn) {
      refreshBtn.classList.remove('loading');
    }
  }

  /**
   * Показать сообщение о неподдерживаемом сайте
   */
  showUnsupportedSiteMessage(statusElementId = 'productStatus') {
    const statusCard = document.getElementById(statusElementId);
    if (!statusCard) return;
    
    // Show unsupported site message
    statusCard.classList.remove('new', 'existing', 'unavailable', 'warning');
    statusCard.classList.add('unavailable');
    
    // Find existing status-text or create new one
    let statusText = statusCard.querySelector('.status-text');
    if (!statusText) {
      statusCard.innerHTML = '<div class="status-text">ℹ️ Сайт не поддерживается</div>';
    } else {
      statusText.textContent = 'ℹ️ Сайт не поддерживается';
    }
    
    console.log('Showed unsupported site message');
  }

  /**
   * Показать состояние загрузки
   */
  showLoadingState(containerId, message = 'Загрузка данных...') {
    const container = document.getElementById(containerId);
    if (container) {
      container.innerHTML = `<div class="loading">${message}</div>`;
    }
  }

  /**
   * Показать состояние ошибки
   */
  showErrorState(containerId, message = 'Произошла ошибка') {
    const container = document.getElementById(containerId);
    if (container) {
      container.innerHTML = `<div class="error">${message}</div>`;
    }
  }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
  window.VIParserUI = VIParserUI;
}