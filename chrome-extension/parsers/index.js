/**
 * Индексный файл для загрузки всех парсеров
 * Этот файл должен быть включен в content.js для доступа к парсерам
 */

// Загружаем все классы парсеров
// В среде расширения Chrome эти файлы будут загружены через <script> теги в manifest.json

console.log('Loading VIParser parsers...');

// Проверяем, что все необходимые классы загружены
if (typeof SiteDetector === 'undefined') {
  console.error('SiteDetector not loaded!');
}

if (typeof BaseParser === 'undefined') {
  console.error('BaseParser not loaded!');
}

if (typeof VictoriasSecretParser === 'undefined') {
  console.error('VictoriasSecretParser not loaded!');
}

if (typeof CalvinKleinParser === 'undefined') {
  console.error('CalvinKleinParser not loaded!');
}

if (typeof CartersParser === 'undefined') {
  console.error('CartersParser not loaded!');
}

if (typeof TommyHilfigerParser === 'undefined') {
  console.error('TommyHilfigerParser not loaded!');
}

if (typeof HMParser === 'undefined') {
  console.error('HMParser not loaded!');
}

if (typeof ParserFactory === 'undefined') {
  console.error('ParserFactory not loaded!');
}

console.log('VIParser parsers loaded successfully');

// Экспортируем для использования в других файлах (если используется система модулей)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    SiteDetector,
    BaseParser,
    VictoriasSecretParser,
    CalvinKleinParser,
    CartersParser,
    TommyHilfigerParser,
    HMParser,
    ParserFactory
  };
}