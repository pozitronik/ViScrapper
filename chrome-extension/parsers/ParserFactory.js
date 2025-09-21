/**
 * Фабрика парсеров
 * Управляет созданием парсеров для разных сайтов
 * Использует SiteDetector как единый источник истины
 */
class ParserFactory {
  /**
   * Создает парсер для текущего сайта
   * @param {string} url - URL страницы (по умолчанию текущий)
   * @returns {BaseParser|null} - Экземпляр парсера или null если сайт не поддерживается
   */
  static createParser(url = window.location.href) {
    console.log('Creating parser for URL:', url);

    // Delegate to SiteDetector for unified detection logic
    return SiteDetector.createParser(url);
  }

  /**
   * Получает список поддерживаемых сайтов
   * @returns {string[]} - Массив доменов поддерживаемых сайтов
   */
  static getSupportedSites() {
    return SiteDetector.getSupportedDomains();
  }

  /**
   * Проверяет, поддерживается ли сайт
   * @param {string} url - URL для проверки (по умолчанию текущий)
   * @returns {boolean} - true если сайт поддерживается
   */
  static isSiteSupported(url = window.location.href) {
    return SiteDetector.isSiteSupported(url);
  }

  /**
   * Получает информацию о поддерживаемых сайтах
   * @returns {Object[]} - Массив объектов с информацией о сайтах
   */
  static getSiteInfo() {
    const sites = SiteDetector.getAllSites();

    return sites.map(site => {
      try {
        // Test parser creation to verify availability
        const parser = site.parserFactory ? site.parserFactory() : null;
        return {
          domain: site.domain,
          siteName: parser ? parser.siteName : site.name,
          isAvailable: true
        };
      } catch (error) {
        return {
          domain: site.domain,
          siteName: site.name,
          isAvailable: false,
          error: error.message
        };
      }
    });
  }

  /**
   * Регистрирует новый парсер
   * @param {string} domain - Домен сайта
   * @param {Function} parserFactory - Функция-фабрика для создания парсера
   * @deprecated - Use SiteDetector.SUPPORTED_SITES instead
   */
  static registerParser(domain, parserFactory) {
    console.warn('ParserFactory.registerParser is deprecated. Update SiteDetector.SUPPORTED_SITES instead.');
    console.log(`Registering parser for domain: ${domain}`);
    // This method is kept for backward compatibility but should not be used
  }

  /**
   * Удаляет парсер для домена
   * @param {string} domain - Домен для удаления
   * @deprecated - Use SiteDetector.SUPPORTED_SITES instead
   */
  static unregisterParser(domain) {
    console.warn('ParserFactory.unregisterParser is deprecated. Update SiteDetector.SUPPORTED_SITES instead.');
    console.log(`Unregistering parser for domain: ${domain}`);
    // This method is kept for backward compatibility but should not be used
    return false;
  }
}

// Экспортируем для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ParserFactory;
}