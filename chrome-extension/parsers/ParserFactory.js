/**
 * Фабрика парсеров
 * Управляет созданием парсеров для разных сайтов
 * Now uses SiteRegistry as the single source of truth
 */
class ParserFactory {
  /**
   * Создает парсер для текущего сайта
   * @param {string} url - URL страницы (по умолчанию текущий)
   * @returns {BaseParser|null} - Экземпляр парсера или null если сайт не поддерживается
   */
  static createParser(url = window.location.href) {
    console.log('ParserFactory: Creating parser for URL:', url);
    
    // Use SiteRegistry to create parser
    if (typeof SiteRegistry !== 'undefined') {
      return SiteRegistry.createParser(url);
    }
    
    console.error('ParserFactory: SiteRegistry not available');
    return null;
  }

  /**
   * Получает список поддерживаемых сайтов
   * @returns {string[]} - Массив доменов поддерживаемых сайтов
   */
  static getSupportedSites() {
    if (typeof SiteRegistry !== 'undefined') {
      return SiteRegistry.getSupportedDomains();
    }
    return [];
  }

  /**
   * Проверяет, поддерживается ли сайт
   * @param {string} url - URL для проверки (по умолчанию текущий)
   * @returns {boolean} - true если сайт поддерживается
   */
  static isSiteSupported(url = window.location.href) {
    if (typeof SiteRegistry !== 'undefined') {
      return SiteRegistry.isSupported(url);
    }
    return false;
  }

  /**
   * Получает информацию о поддерживаемых сайтах
   * @returns {Object[]} - Массив объектов с информацией о сайтах
   */
  static getSiteInfo() {
    if (typeof SiteRegistry !== 'undefined') {
      return SiteRegistry.getAllSites();
    }
    return [];
  }

  /**
   * Регистрирует новый парсер (deprecated - use SiteRegistry directly)
   * @param {string} domain - Домен сайта
   * @param {Function} parserClass - Класс парсера
   */
  static registerParser(domain, parserClass) {
    console.log(`ParserFactory.registerParser is deprecated. Use SiteRegistry.register() directly`);
    if (typeof SiteRegistry !== 'undefined') {
      // Try to extract site name from parser class
      let siteName = domain;
      try {
        const parser = new parserClass();
        siteName = parser.siteName || domain;
      } catch (e) {
        // Use domain as fallback
      }
      
      return SiteRegistry.register({
        domain: domain,
        siteId: domain.replace(/\./g, ''),
        siteName: siteName,
        parserClass: parserClass
      });
    }
    return false;
  }

  /**
   * Удаляет парсер для домена (deprecated)
   * @param {string} domain - Домен для удаления
   */
  static unregisterParser(domain) {
    console.log(`ParserFactory.unregisterParser is deprecated and no longer functional`);
    return false;
  }
}

// Экспортируем для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ParserFactory;
}