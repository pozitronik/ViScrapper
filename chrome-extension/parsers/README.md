# VIParser - Модульная система парсеров

Эта папка содержит модульную систему парсеров для поддержки множественных сайтов.

## 🏗️ Архитектура

### Файлы системы

1. **`BaseParser.js`** - Базовый класс со всеми общими методами
2. **`VictoriasSecretParser.js`** - Парсер для Victoria's Secret
3. **`ParserFactory.js`** - Фабрика для создания парсеров
4. **`index.js`** - Индексный файл для загрузки всех парсеров

### Порядок загрузки

Файлы загружаются в `manifest.json` в следующем порядке:
```json
"js": [
  "parsers/BaseParser.js",
  "parsers/VictoriasSecretParser.js", 
  "parsers/ParserFactory.js",
  "parsers/index.js",
  "content.js"
]
```

## 🔧 Добавление нового сайта

### Шаг 1: Создать парсер

Создайте новый файл `YourSiteParser.js`:

```javascript
class YourSiteParser extends BaseParser {
  constructor() {
    super({
      siteName: 'Your Site Name',
      domain: 'yoursite.com',
      selectors: {
        productInfo: '.product-title',
        productPrice: '.price',
        // ... другие селекторы
      }
    });
  }

  // Обязательные методы
  isValidProductPage() {
    // Логика проверки страницы товара
  }

  extractName() {
    // Извлечение названия
  }

  extractSku(jsonData) {
    // Извлечение SKU
  }

  extractPrice(jsonData) {
    // Извлечение цены
  }

  extractImages() {
    // Извлечение изображений
  }

  async extractSizes() {
    // Извлечение размеров
  }

  // Опциональные методы (переопределить при необходимости)
  extractColor() {
    // Специфичная логика извлечения цвета
  }
}
```

### Шаг 2: Зарегистрировать парсер

Добавьте парсер в `ParserFactory.js`:

```javascript
static parsers = new Map([
  ['victoriassecret.com', () => new VictoriasSecretParser()],
  ['yoursite.com', () => new YourSiteParser()], // <- добавить сюда
]);
```

### Шаг 3: Подключить в manifest.json

Добавьте новый файл в `manifest.json`:

```json
"js": [
  "parsers/BaseParser.js",
  "parsers/VictoriasSecretParser.js",
  "parsers/YourSiteParser.js", // <- добавить сюда
  "parsers/ParserFactory.js",
  "parsers/index.js",
  "content.js"
]
```

### Шаг 4: Обновить host_permissions

Добавьте домен в `host_permissions`:

```json
"host_permissions": [
  "https://www.victoriassecret.com/*",
  "https://www.yoursite.com/*", // <- добавить сюда
  "http://localhost:8000/*"
]
```

### Шаг 5: Обновить content_scripts

Добавьте домен в `matches`:

```json
"content_scripts": [
  {
    "matches": [
      "https://www.victoriassecret.com/*",
      "https://www.yoursite.com/*" // <- добавить сюда
    ],
    "js": [...]
  }
]
```

## 📝 Базовые методы

### Обязательные методы (должны быть переопределены)

- `isValidProductPage()` - Проверка что это страница товара
- `extractName()` - Извлечение названия продукта
- `extractSku(jsonData)` - Извлечение SKU
- `extractPrice(jsonData)` - Извлечение цены
- `extractImages()` - Извлечение изображений
- `extractSizes()` - Извлечение размеров

### Опциональные методы (базовая реализация есть)

- `extractCurrency(jsonData)` - Извлечение валюты (по умолчанию USD)
- `extractAvailability(jsonData)` - Извлечение доступности (по умолчанию InStock)
- `extractColor()` - Извлечение цвета (по умолчанию null)
- `extractComposition()` - Извлечение состава (по умолчанию null)
- `extractItem()` - Извлечение артикула (по умолчанию null)
- `waitForJsonLd(timeout)` - Ожидание JSON-LD (по умолчанию null)
- `parseJsonLd(jsonLdText)` - Парсинг JSON-LD (базовая реализация)
- `validateProductData(data)` - Валидация данных (базовая реализация)

### Утилитарные методы (общие)

- `sanitizeUrl(url)` - Очистка URL от лишних параметров
- `wait(ms)` - Функция ожидания

## 🎯 Конфигурация парсера

Каждый парсер имеет конфигурацию:

```javascript
{
  siteName: 'Название сайта',
  domain: 'domain.com',
  selectors: {
    // CSS селекторы для элементов
    productInfo: '.product-title',
    productPrice: '.price',
    // ... и т.д.
  }
}
```

## 🚀 Тестирование

1. Загрузите расширение в Chrome
2. Откройте страницу поддерживаемого сайта
3. Проверьте консоль браузера на наличие ошибок
4. Проверьте работу парсера через popup расширения

## 🔍 Отладка

- Все парсеры выводят подробные логи в консоль
- Используйте `console.log` для отладки
- Проверяйте правильность селекторов на странице
- Тестируйте каждый метод по отдельности