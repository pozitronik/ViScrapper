/**
 * Фабрика парсеров
 * Управляет созданием парсеров для разных сайтов
 */
class ParserFactory {
  // Карта поддерживаемых сайтов и их парсеров
  static parsers = new Map([
    ['victoriassecret.com', () => new VictoriasSecretParser()],
    ['calvinklein.us', () => new CalvinKleinParser()],
    ['carters.com', () => new CartersParser()],
    ['usa.tommy.com', () => new TommyHilfigerParser()],
    // Добавлять новые парсеры здесь:
    // ['anothersite.com', () => new AnotherSiteParser()],
  ]);

  /**
   * Создает парсер для текущего сайта
   * @param {string} url - URL страницы (по умолчанию текущий)
   * @returns {BaseParser|null} - Экземпляр парсера или null если сайт не поддерживается
   */
  static createParser(url = window.location.href) {
    console.log('Creating parser for URL:', url);
    
    for (const [domain, parserFactory] of this.parsers) {
      if (url.includes(domain)) {
        console.log(`Creating parser for ${domain}`);
        try {
          const parser = parserFactory();
          console.log(`Successfully created ${parser.siteName} parser`);
          return parser;
        } catch (error) {
          console.error(`Failed to create parser for ${domain}:`, error);
          return null;
        }
      }
    }
    
    console.log('No parser found for URL:', url);
    console.log('Supported sites:', Array.from(this.parsers.keys()));
    return null;
  }

  /**
   * Получает список поддерживаемых сайтов
   * @returns {string[]} - Массив доменов поддерживаемых сайтов
   */
  static getSupportedSites() {
    return Array.from(this.parsers.keys());
  }

  /**
   * Проверяет, поддерживается ли сайт
   * @param {string} url - URL для проверки (по умолчанию текущий)
   * @returns {boolean} - true если сайт поддерживается
   */
  static isSiteSupported(url = window.location.href) {
    return this.getSupportedSites().some(domain => url.includes(domain));
  }

  /**
   * Получает информацию о поддерживаемых сайтах
   * @returns {Object[]} - Массив объектов с информацией о сайтах
   */
  static getSiteInfo() {
    const siteInfo = [];
    
    for (const [domain, parserFactory] of this.parsers) {
      try {
        const parser = parserFactory();
        siteInfo.push({
          domain: domain,
          siteName: parser.siteName,
          isAvailable: true
        });
      } catch (error) {
        siteInfo.push({
          domain: domain,
          siteName: domain,
          isAvailable: false,
          error: error.message
        });
      }
    }
    
    return siteInfo;
  }

  /**
   * Регистрирует новый парсер
   * @param {string} domain - Домен сайта
   * @param {Function} parserFactory - Функция-фабрика для создания парсера
   */
  static registerParser(domain, parserFactory) {
    console.log(`Registering parser for domain: ${domain}`);
    this.parsers.set(domain, parserFactory);
  }

  /**
   * Удаляет парсер для домена
   * @param {string} domain - Домен для удаления
   */
  static unregisterParser(domain) {
    console.log(`Unregistering parser for domain: ${domain}`);
    return this.parsers.delete(domain);
  }
}

// Экспортируем для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ParserFactory;
}