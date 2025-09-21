# VIParser - Модульная система парсеров

Эта папка содержит модульную систему парсеров для поддержки множественных сайтов.

## 🏗️ Архитектура

### Файлы системы

1. **`../shared/site-detector.js`** - Единый модуль детекции сайтов (источник истины)
2. **`BaseParser.js`** - Базовый класс со всеми общими методами
3. **`VictoriasSecretParser.js`** - Парсер для Victoria's Secret
4. **`CalvinKleinParser.js`** - Парсер для Calvin Klein
5. **`CartersParser.js`** - Парсер для Carter's
6. **`TommyHilfigerParser.js`** - Парсер для Tommy Hilfiger
7. **`HMParser.js`** - Парсер для H&M
8. **`ParserFactory.js`** - Фабрика для создания парсеров (использует SiteDetector)
9. **`index.js`** - Индексный файл для загрузки всех парсеров

### Порядок загрузки

Файлы загружаются в `manifest.json` в следующем порядке:
```json
"js": [
  "shared/site-detector.js",
  "parsers/BaseParser.js",
  "parsers/VictoriasSecretParser.js",
  "parsers/CalvinKleinParser.js",
  "parsers/CartersParser.js",
  "parsers/TommyHilfigerParser.js",
  "parsers/HMParser.js",
  "parsers/ParserFactory.js",
  "parsers/index.js",
  "content.js"
]
```

## 🎯 Единая Система Детекции Сайтов

Система использует **`SiteDetector`** как единый источник истины для определения поддерживаемых сайтов. Это исключает дублирование кода и обеспечивает консистентность между компонентами.

### Ключевые преимущества:
- **Единый источник истины** - все данные о сайтах в одном месте
- **Нет дублирования** - ParserFactory и UI используют одну логику
- **Легко расширять** - добавление нового сайта в одном месте
- **Консистентность** - одинаковое поведение везде

### Компоненты:
- **`SiteDetector`** - центральный модуль детекции
- **`ParserFactory`** - делегирует детекцию SiteDetector'у
- **`viparser-core.js`** - использует SiteDetector для UI

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

### Шаг 2: Зарегистрировать в SiteDetector

Добавьте сайт в `shared/site-detector.js` в массив `SUPPORTED_SITES`:

```javascript
static SUPPORTED_SITES = [
  // ... существующие сайты
  {
    id: 'yoursite',
    name: 'Your Site Name',
    domain: 'yoursite.com',
    parserFactory: () => new YourSiteParser(),
    supported: true
  }
];
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

### Шаг 6: Добавить брендинг CSS

Добавьте стили для нового сайта в `popup.css` и `sidepanel.css`:

```css
/* Заголовок */
body.site-yoursite h1 {
  color: #YOUR_BRAND_COLOR;
}

/* Кнопки */
body.site-yoursite .btn-primary {
  background-color: #YOUR_BRAND_COLOR;
  border-color: #YOUR_BRAND_COLOR;
}

body.site-yoursite .btn-primary:hover {
  background-color: #DARKER_SHADE;
  border-color: #DARKER_SHADE;
}

/* Фокус textarea */
body.site-yoursite textarea:focus {
  border: 2px solid #YOUR_BRAND_COLOR;
  box-shadow: 0 0 0 1px #333;
}
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