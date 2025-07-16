/**
 * Парсер для Calvin Klein
 * Содержит всю логику извлечения данных, специфичную для CK
 */
class CalvinKleinParser extends BaseParser {
  constructor() {
    super({
      siteName: 'Calvin Klein',
      domain: 'calvinklein.us',
      selectors: {
        buyBox: '[data-comp="BuyBox"]',
        productName: '.product-name',
        priceValue: '.value[content]',
        productImages: '[data-comp="ProductImage"]',
        colorsList: '#colorscolorCode',
        sizesList: '#sizessize',
        descriptionDetail: '.description-and-detail .content-description',
        jsonLdScript: 'script[type="application/ld+json"]'
      }
    });
    
    // Отслеживание последнего выбранного цвета (только для логирования)
    this.lastSelectedColor = null;
  }

  /**
   * Проверка, что мы на странице товара Calvin Klein
   */
  isValidProductPage() {
    const url = window.location.href;
    console.log('Checking CK page validity, URL:', url);
    
    if (!url.includes(this.config.domain)) {
      console.log('Not a Calvin Klein page');
      return false;
    }
    
    // Проверяем наличие основных элементов в первом BuyBox контейнере
    const buyBox = document.querySelector(this.config.selectors.buyBox);
    if (!buyBox) {
      console.log('No BuyBox container found');
      return false;
    }
    
    const hasProductName = buyBox.querySelector(this.config.selectors.productName);
    const hasPrice = buyBox.querySelector(this.config.selectors.priceValue);
    
    console.log('ProductName element:', hasProductName);
    console.log('Price element:', hasPrice);
    
    const isValid = !!(hasProductName && hasPrice);
    console.log('Page is valid CK product page:', isValid);
    
    return isValid;
  }

  /**
   * Извлечение названия продукта
   */
  extractName() {
    const buyBox = document.querySelector(this.config.selectors.buyBox);
    if (!buyBox) {
      console.log('CK extractName: No BuyBox found');
      return null;
    }
    
    const element = buyBox.querySelector(this.config.selectors.productName);
    const name = element?.textContent?.trim() || null;
    console.log('CK extractName result:', name);
    return name;
  }

  /**
   * Извлечение базового SKU из JSON-LD
   */
  extractSku(jsonData) {
    console.log('CK extractSku called with jsonData:', jsonData);
    
    if (jsonData && jsonData.sku) {
      console.log('CK extractSku from JSON-LD:', jsonData.sku);
      return jsonData.sku;
    }
    
    // Fallback: try to extract from URL
    const urlMatch = window.location.pathname.match(/\/([A-Z0-9]+-[0-9]+)\.html$/i);
    if (urlMatch) {
      console.log('CK extractSku from URL:', urlMatch[1]);
      return urlMatch[1];
    }
    
    console.log('CK extractSku: No SKU found');
    return null;
  }

  /**
   * Генерация уникального SKU для конкретного цвета
   * Использует постоянную уникальную часть продукта, игнорируя переменные суффиксы
   */
  generateColorSpecificSku(baseSku, colorCode) {
    if (!baseSku) {
      console.warn('CK generateColorSpecificSku: No base SKU provided');
      return null;
    }

    if (!colorCode) {
      console.log('CK generateColorSpecificSku: No color code, returning base SKU');
      return baseSku;
    }

    // Извлекаем уникальную часть продукта (первая часть до первого дефиса)
    // Пример: 47B266G-RM9 -> 47B266G, D3429-001-ABC -> D3429
    const uniqueProductId = this.extractUniqueProductId(baseSku);
    
    // Формат: 47B266G-100 или D3429-100 (уникальная часть + цветовой код)
    const colorSpecificSku = `${uniqueProductId}-${colorCode}`;
    console.log(`CK generateColorSpecificSku: Generated ${colorSpecificSku} from base ${baseSku} (unique part: ${uniqueProductId}) and color ${colorCode}`);
    
    return colorSpecificSku;
  }

  /**
   * Извлечение уникального идентификатора продукта из базового SKU
   * ПРЕДПОЛАГАЕМАЯ ЛОГИКА: Всегда используем только первую часть до первого дефиса
   * как уникальный идентификатор продукта, так как не знаем точную структуру SKU Calvin Klein.
   * 
   * ПРИМЕРЫ:
   * - 47B266G-RM9 → 47B266G (основной идентификатор)
   * - D3429-001-ABC → D3429 (основной идентификатор)
   * - PRODUCT123-VAR-COLOR → PRODUCT123 (основной идентификатор)
   * 
   * ВАЖНО: Если эта логика окажется неверной и первая часть не является уникальным
   * идентификатором, эту функцию можно легко изменить для использования другой части SKU.
   */
  extractUniqueProductId(baseSku) {
    if (!baseSku) {
      return baseSku;
    }

    // Проверяем, содержит ли SKU дефисы
    const parts = baseSku.split('-');
    
    if (parts.length < 2) {
      // Если нет дефисов, возвращаем как есть
      console.log(`CK extractUniqueProductId: No dashes in SKU, returning as-is: ${baseSku}`);
      return baseSku;
    }

    // ПРЕДПОЛАГАЕМАЯ ЛОГИКА: Всегда берем только первую часть как уникальный идентификатор
    // Это предположение основано на том, что первая часть наиболее вероятно является
    // основным идентификатором продукта, а все последующие части - переменными суффиксами
    const uniquePart = parts[0];
    console.log(`CK extractUniqueProductId: Extracted unique part "${uniquePart}" from "${baseSku}" (using first part assumption)`);
    
    return uniquePart;
  }

  /**
   * Извлечение цены из JSON-LD или элемента на странице
   */
  extractPrice(jsonData) {
    console.log('CK extractPrice: Starting price extraction...');
    
    // Приоритет 1: Проверяем актуальную цену в sales блоке (для текущего выбранного цвета)
    const salesPriceElement = document.querySelector('.sales .value[content]');
    if (salesPriceElement) {
      const salesContent = salesPriceElement.getAttribute('content');
      if (salesContent) {
        const salesPrice = parseFloat(salesContent);
        console.log('CK extractPrice: Found sales price from DOM:', salesPrice);
        return salesPrice;
      }
    }
    
    console.log('CK extractPrice: No sales price found, checking JSON-LD...');
    
    // Приоритет 2: JSON-LD цена (базовая цена продукта)
    if (jsonData && jsonData.offers && jsonData.offers.price) {
      const jsonPrice = parseFloat(jsonData.offers.price);
      console.log('CK extractPrice: Found price from JSON-LD:', jsonPrice);
      return jsonPrice;
    }
    
    // Приоритет 3: Стандартный селектор цены в BuyBox
    const buyBox = document.querySelector(this.config.selectors.buyBox);
    if (buyBox) {
      const priceElement = buyBox.querySelector(this.config.selectors.priceValue);
      console.log('CK extractPrice: priceElement found:', !!priceElement);
      if (priceElement) {
        const priceContent = priceElement.getAttribute('content');
        console.log('CK extractPrice: priceContent from element:', priceContent);
        if (priceContent) {
          const domPrice = parseFloat(priceContent);
          console.log('CK extractPrice: Found price from DOM fallback:', domPrice);
          return domPrice;
        }
      }
    }
    
    console.log('CK extractPrice: No price found in any source');
    return null;
  }

  /**
   * Извлечение изображений используя прямое построение URL из данных страницы
   */
  async extractImages() {
    console.log('CK extractImages: Starting direct image URL extraction...');
    
    // Сначала пробуем извлечь изображения напрямую из данных страницы
    const directImages = await this.extractImagesDirectly();
    if (directImages && directImages.length > 0) {
      console.log(`CK extractImages: Found ${directImages.length} images via direct extraction`);
      return directImages;
    }
    
    console.log('CK extractImages: Direct extraction failed, falling back to DOM extraction...');
    const imageUrls = [];
    
    // Fallback к старому методу извлечения из DOM
    const productImageContainer = document.querySelector(this.config.selectors.productImages);
    if (productImageContainer) {
      console.log('CK extractImages: Found ProductImage container');
      
      // Получаем текущий выбранный цвет (для логирования)
      const currentColor = this.extractColor();
      console.log(`CK extractImages: Current color: ${currentColor}, Last color: ${this.lastSelectedColor}`);
      this.lastSelectedColor = currentColor;
      
      // Проверяем, нужна ли прокрутка (есть ли пустые srcset)
      const needsScrolling = this.checkIfScrollingNeeded(productImageContainer);
      console.log('CK extractImages: Scrolling needed:', needsScrolling);
      
      // Выполняем прокрутку каждый раз, если нужно (без отслеживания флагов)
      if (needsScrolling) {
        console.log('CK extractImages: Scrolling for lazy loading...');
        await this.forceImageLoadingByScroll();
      } else {
        console.log('CK extractImages: Images already loaded, skipping scroll...');
      }
      
      // Ищем все swiper слайды с изображениями - используем более общий селектор
      const swiperSlides = productImageContainer.querySelectorAll('.swiper-slide, .product-image.swiper-slide');
      console.log(`CK extractImages: Found ${swiperSlides.length} swiper slides`);
      
      swiperSlides.forEach((slide, slideIndex) => {
        console.log(`CK extractImages: Processing slide ${slideIndex}`);
        
        // Ищем picture элемент в слайде
        const picture = slide.querySelector('picture');
        if (picture) {
          console.log(`CK extractImages: Found picture in slide ${slideIndex}`);
          
          // Ищем все source элементы с srcset
          let foundFromSource = false;
          const sources = picture.querySelectorAll('source');
          console.log(`CK extractImages: Found ${sources.length} source elements in slide ${slideIndex}`);
          
          // Проходим по всем source элементам для поиска лучшего качества
          for (const source of sources) {
            const srcset = source.getAttribute('srcset');
            if (srcset && srcset.trim()) {
              console.log(`CK extractImages: Found source with srcset in slide ${slideIndex}:`, srcset);
              
              // Извлекаем все URL из srcset и берем самый высокого качества
              const srcsetUrls = this.extractFromSrcset(srcset);
              if (srcsetUrls.length > 0) {
                // Берем последний URL из srcset (обычно самого высокого качества)
                const bestQualityUrl = srcsetUrls[srcsetUrls.length - 1];
                const cleanUrl = this.cleanImageUrl(bestQualityUrl);
                if (!imageUrls.includes(cleanUrl)) {
                  imageUrls.push(cleanUrl);
                  console.log(`CK extractImages: Added image from slide ${slideIndex}:`, cleanUrl);
                  foundFromSource = true;
                  break; // Берем только первый найденный source с srcset
                }
              } else {
                console.log(`CK extractImages: No URLs extracted from srcset in slide ${slideIndex}`);
              }
            } else {
              console.log(`CK extractImages: Empty or no srcset in source ${Array.from(sources).indexOf(source)} of slide ${slideIndex}`);
            }
          }
          
          // Если не нашли в source, пробуем img элемент
          if (!foundFromSource) {
            const img = picture.querySelector('img');
            if (img) {
              let imgSrc = img.src || img.getAttribute('data-src') || img.getAttribute('srcset');
              if (imgSrc && imgSrc.includes('http')) {
                // Если это srcset, извлекаем URL
                if (imgSrc.includes(' ')) {
                  const srcsetUrls = this.extractFromSrcset(imgSrc);
                  if (srcsetUrls.length > 0) {
                    imgSrc = srcsetUrls[srcsetUrls.length - 1]; // Берем последний (высшего качества)
                  }
                }
                const cleanUrl = this.cleanImageUrl(imgSrc);
                if (!imageUrls.includes(cleanUrl)) {
                  imageUrls.push(cleanUrl);
                  console.log(`CK extractImages: Added image from img fallback in slide ${slideIndex}:`, cleanUrl);
                }
              }
            }
          }
        } else {
          // Fallback: ищем img напрямую в слайде
          const img = slide.querySelector('img');
          if (img) {
            let imgSrc = img.src || img.getAttribute('data-src') || img.getAttribute('srcset');
            if (imgSrc && imgSrc.includes('http')) {
              // Если это srcset, извлекаем URL
              if (imgSrc.includes(' ')) {
                const srcsetUrls = this.extractFromSrcset(imgSrc);
                if (srcsetUrls.length > 0) {
                  imgSrc = srcsetUrls[srcsetUrls.length - 1]; // Берем последний (высшего качества)
                }
              }
              const cleanUrl = this.cleanImageUrl(imgSrc);
              if (!imageUrls.includes(cleanUrl)) {
                imageUrls.push(cleanUrl);
                console.log(`CK extractImages: Added image from direct img in slide ${slideIndex}:`, cleanUrl);
              }
            }
          }
        }
      });
    }
    
    // Если не нашли изображения в слайдах, используем JSON-LD как fallback
    if (imageUrls.length === 0) {
      console.log('CK extractImages: No images found in slides, trying JSON-LD...');
      const jsonData = this.getJsonLdData();
      if (jsonData && jsonData.image && Array.isArray(jsonData.image)) {
        console.log('CK extractImages: Found images in JSON-LD:', jsonData.image.length);
        jsonData.image.forEach(url => {
          if (url && typeof url === 'string') {
            const cleanUrl = this.cleanImageUrl(url);
            if (!imageUrls.includes(cleanUrl)) {
              imageUrls.push(cleanUrl);
              console.log('CK extractImages: Added image from JSON-LD:', cleanUrl);
            }
          }
        });
      }
    }
    
    
    console.log(`CK extractImages: Total ${imageUrls.length} unique images found:`, imageUrls);
    return imageUrls;
  }


  /**
   * Прямое извлечение изображений путем построения URL из данных страницы
   */
  async extractImagesDirectly() {
    console.log('CK extractImagesDirectly: Starting direct image extraction...');
    
    try {
      // Получаем базовую информацию
      const jsonData = this.getJsonLdData();
      const baseSku = this.extractSku(jsonData);
      const currentColor = this.extractColor();
      
      if (!baseSku) {
        console.log('CK extractImagesDirectly: No base SKU found');
        return [];
      }
      
      console.log(`CK extractImagesDirectly: Base SKU: ${baseSku}, Current color: ${currentColor}`);
      
      // Извлекаем код цвета из выбранного элемента
      const colorCode = this.extractColorCodeFromSelection();
      
      if (!colorCode) {
        console.log('CK extractImagesDirectly: No color code found, using JSON-LD images');
        // Fallback к изображениям из JSON-LD (обычно для дефолтного цвета)
        if (jsonData && jsonData.image && Array.isArray(jsonData.image)) {
          return jsonData.image.map(url => this.cleanImageUrl(url));
        }
        return [];
      }
      
      console.log(`CK extractImagesDirectly: Using color code: ${colorCode}`);
      
      // Строим URLs изображений для данного цвета
      const baseImageUrl = 'https://calvinklein.scene7.com/is/image/CalvinKlein';
      // Используем уникальный идентификатор продукта для построения URL изображений
      const uniqueProductId = this.extractUniqueProductId(baseSku);
      // Поскольку uniqueProductId уже является первой частью SKU, используем его напрямую
      const baseName = uniqueProductId; // 47B266G-RM9 → 47B266G, D3429-001-ABC → D3429
      const imageTypes = ['main', 'alternate1', 'alternate2', 'alternate3', 'alternate4', 'alternate5'];
      
      const candidateUrls = imageTypes.map(type => {
        return `${baseImageUrl}/${baseName}_${colorCode}_${type}`;
      });
      
      console.log(`CK extractImagesDirectly: Generated ${candidateUrls.length} candidate URLs, validating...`);
      
      // Проверяем, какие изображения реально существуют
      const validImageUrls = await this.validateImageUrls(candidateUrls);
      
      // Улучшаем качество всех найденных изображений
      const enhancedUrls = validImageUrls.map(url => this.enhanceImageQuality(url));
      
      console.log(`CK extractImagesDirectly: Found ${validImageUrls.length} valid images`);
      return enhancedUrls;
      
    } catch (error) {
      console.warn('CK extractImagesDirectly: Error in direct extraction:', error);
      return [];
    }
  }

  /**
   * Проверка существования изображений путем быстрой проверки HEAD запросов
   */
  async validateImageUrls(urls) {
    console.log(`CK validateImageUrls: Validating ${urls.length} image URLs...`);
    
    const validUrls = [];
    const maxConcurrent = 4; // Ограничиваем количество одновременных запросов
    
    // Проверяем изображения партиями
    for (let i = 0; i < urls.length; i += maxConcurrent) {
      const batch = urls.slice(i, i + maxConcurrent);
      const batchPromises = batch.map(url => this.checkImageExists(url));
      
      try {
        const results = await Promise.all(batchPromises);
        
        results.forEach((exists, index) => {
          const url = batch[index];
          if (exists) {
            validUrls.push(url);
            console.log(`CK validateImageUrls: ✓ Valid: ${url}`);
          } else {
            console.log(`CK validateImageUrls: ✗ Invalid: ${url}`);
          }
        });
      } catch (error) {
        console.warn('CK validateImageUrls: Error in batch validation:', error);
        // В случае ошибки, добавляем все URL из батча (fallback)
        batch.forEach(url => {
          if (!validUrls.includes(url)) {
            validUrls.push(url);
          }
        });
      }
    }
    
    console.log(`CK validateImageUrls: Validation complete. ${validUrls.length}/${urls.length} images valid`);
    return validUrls;
  }

  /**
   * Проверка существования одного изображения
   */
  async checkImageExists(url) {
    try {
      const response = await fetch(url, { 
        method: 'HEAD',
        cache: 'no-cache'
      });
      
      return response.ok && response.status === 200;
    } catch (error) {
      console.warn(`CK checkImageExists: Error checking ${url}:`, error);
      return false; // Считаем несуществующим в случае ошибки
    }
  }

  /**
   * Извлечение кода цвета из выбранного цветового элемента
   */
  extractColorCodeFromSelection() {
    console.log('CK extractColorCodeFromSelection: Looking for color code...');
    
    try {
      // Метод 1: Ищем выбранный цвет по aria-checked="true"
      const checkedColorSpan = document.querySelector('#colorscolorCode span[aria-checked="true"]');
      if (checkedColorSpan) {
        console.log('CK extractColorCodeFromSelection: Found aria-checked span:', checkedColorSpan);
        
        // Пробуем извлечь из style (background-image)
        const style = checkedColorSpan.getAttribute('style');
        if (style && style.includes('scene7.com')) {
          console.log('CK extractColorCodeFromSelection: Found style with scene7:', style);
          
          // Более универсальный regex для извлечения кода цвета
          const match = style.match(/\/([A-Z0-9]+_[A-Z0-9]+)_pattern/);
          if (match) {
            const fullCode = match[1]; // QF7900_100
            const colorCode = fullCode.split('_').pop(); // 100
            console.log(`CK extractColorCodeFromSelection: Found color code from aria-checked style: ${colorCode}`);
            return colorCode;
          }
        }
        
        // Пробуем извлечь из связанного input через label
        const labelFor = checkedColorSpan.closest('label');
        if (labelFor) {
          const forAttr = labelFor.getAttribute('for');
          if (forAttr) {
            console.log('CK extractColorCodeFromSelection: Found label for:', forAttr);
            
            // Извлекаем код из ID: QF7900-UB1_colorCodeitem-100 -> 100
            const match = forAttr.match(/_colorCodeitem-([A-Z0-9]+)$/);
            if (match) {
              const colorCode = match[1];
              console.log(`CK extractColorCodeFromSelection: Found color code from label for: ${colorCode}`);
              return colorCode;
            }
          }
        }
      }
      
      // Метод 2: Ищем checked input
      const checkedInput = document.querySelector('#colorscolorCode input:checked');
      if (checkedInput) {
        console.log('CK extractColorCodeFromSelection: Found checked input:', checkedInput);
        
        const id = checkedInput.getAttribute('id');
        if (id) {
          console.log('CK extractColorCodeFromSelection: Input ID:', id);
          
          // Извлекаем код из ID: QF7900-UB1_colorCodeitem-100 -> 100
          const match = id.match(/_colorCodeitem-([A-Z0-9]+)$/);
          if (match) {
            const colorCode = match[1];
            console.log(`CK extractColorCodeFromSelection: Found color code from input ID: ${colorCode}`);
            return colorCode;
          }
        }
        
        const value = checkedInput.getAttribute('data-attr-value');
        if (value) {
          console.log('CK extractColorCodeFromSelection: Input data-attr-value:', value);
          
          // data-attr-value может содержать полный код цвета
          const colorCode = value.split('-').pop(); // QF7900-100 -> 100
          console.log(`CK extractColorCodeFromSelection: Found color code from data-attr-value: ${colorCode}`);
          return colorCode;
        }
      }
      
      // Метод 3: Ищем активный элемент по табиндексу 0
      const activeColorSpan = document.querySelector('#colorscolorCode span[tabindex="0"]');
      if (activeColorSpan) {
        console.log('CK extractColorCodeFromSelection: Found active tabindex span:', activeColorSpan);
        
        const style = activeColorSpan.getAttribute('style');
        if (style && style.includes('scene7.com')) {
          console.log('CK extractColorCodeFromSelection: Active span style:', style);
          
          const match = style.match(/\/([A-Z0-9]+_[A-Z0-9]+)_pattern/);
          if (match) {
            const fullCode = match[1]; // QF7900_100
            const colorCode = fullCode.split('_').pop(); // 100
            console.log(`CK extractColorCodeFromSelection: Found color code from active tabindex: ${colorCode}`);
            return colorCode;
          }
        }
      }
      
      console.log('CK extractColorCodeFromSelection: No color code found');
      return null;
      
    } catch (error) {
      console.warn('CK extractColorCodeFromSelection: Error extracting color code:', error);
      return null;
    }
  }

  /**
   * Очистка URL изображения от параметров размера
   */
  cleanImageUrl(url) {
    try {
      // Calvin Klein использует scene7 CDN с параметрами размера
      // Вместо удаления параметров, улучшаем качество изображения
      const urlObj = new URL(url);
      urlObj.search = ''; // Сначала очищаем старые параметры
      const cleanUrl = urlObj.toString();
      
      // Применяем улучшение качества
      return this.enhanceImageQuality(cleanUrl);
    } catch (error) {
      console.warn('CK cleanImageUrl: Error processing URL:', url, error);
      return url;
    }
  }

  /**
   * Извлечение URL из srcset атрибута
   */
  extractFromSrcset(srcset) {
    const urls = [];
    const srcsetParts = srcset.split(',');
    
    srcsetParts.forEach(part => {
      const trimmed = part.trim();
      const spaceIndex = trimmed.indexOf(' ');
      const url = spaceIndex > -1 ? trimmed.substring(0, spaceIndex) : trimmed;
      
      if (url && (url.startsWith('http') || url.startsWith('//'))) {
        // Конвертируем протокол-относительные URL в HTTPS
        const finalUrl = url.startsWith('//') ? `https:${url}` : url;
        urls.push(finalUrl);
      }
    });
    
    // Сортируем по размеру (если есть дескрипторы размера) или просто возвращаем как есть
    return urls;
  }

  /**
   * Принудительная загрузка изображений через агрессивную прокрутку страницы
   */
  async forceImageLoadingByScroll() {
    console.log('CK forceImageLoadingByScroll: Starting aggressive page scroll to trigger lazy loading...');
    
    try {
      // Сначала подсчитываем сколько source элементов без srcset у нас есть
      const productImageContainer = document.querySelector(this.config.selectors.productImages);
      if (!productImageContainer) {
        console.log('CK forceImageLoadingByScroll: No product image container found');
        return;
      }
      
      const initialEmptySources = this.countEmptySourceElements(productImageContainer);
      console.log('CK forceImageLoadingByScroll: Initial empty sources:', initialEmptySources);
      
      // Получаем полную высоту документа
      const documentHeight = Math.max(
        document.body.scrollHeight,
        document.body.offsetHeight,
        document.documentElement.clientHeight,
        document.documentElement.scrollHeight,
        document.documentElement.offsetHeight
      );
      
      console.log('CK forceImageLoadingByScroll: Document height:', documentHeight);
      
      // Делаем несколько циклов прокрутки для более надежной загрузки
      for (let cycle = 0; cycle < 3; cycle++) {
        console.log(`CK forceImageLoadingByScroll: Scroll cycle ${cycle + 1}/3`);
        
        // Прокручиваем к низу
        console.log('CK forceImageLoadingByScroll: Scrolling to bottom...');
        window.scrollTo({
          top: documentHeight,
          left: 0,
          behavior: 'instant'
        });
        
        // Ждем дольше в первом цикле, и вообще дольше
        await this.wait(cycle === 0 ? 2000 : 1000);
        
        // Прокручиваем к середине
        console.log('CK forceImageLoadingByScroll: Scrolling to middle...');
        window.scrollTo({
          top: documentHeight / 2,
          left: 0,
          behavior: 'instant'
        });
        
        await this.wait(800);
        
        // Возвращаемся к верху
        console.log('CK forceImageLoadingByScroll: Scrolling back to top...');
        window.scrollTo({
          top: 0,
          left: 0,
          behavior: 'instant'
        });
        
        await this.wait(600);
        
        // Проверяем прогресс после каждого цикла
        const currentEmptyCount = this.countEmptySourceElements(productImageContainer);
        console.log(`CK forceImageLoadingByScroll: After cycle ${cycle + 1}: ${currentEmptyCount} empty sources (was ${initialEmptySources})`);
        
        // Если достигли хорошего результата, можем остановиться раньше
        if (currentEmptyCount <= Math.max(1, initialEmptySources * 0.2)) {
          console.log('CK forceImageLoadingByScroll: Good progress achieved, stopping cycles early');
          break;
        }
      }
      
      // Дополнительное ожидание после всех циклов прокрутки
      console.log('CK forceImageLoadingByScroll: Additional wait after all scroll cycles...');
      await this.wait(3000); // Ждем еще 3 секунды после прокрутки
      
      // Финальное ожидание загрузки изображений
      console.log('CK forceImageLoadingByScroll: Final wait for images to load...');
      await this.waitForImageLoading(productImageContainer, initialEmptySources);
      
      console.log('CK forceImageLoadingByScroll: Aggressive scroll completed');
      
    } catch (error) {
      console.warn('CK forceImageLoadingByScroll: Error during aggressive scroll:', error);
    }
  }

  /**
   * Проверка, нужна ли прокрутка для загрузки изображений
   */
  checkIfScrollingNeeded(container) {
    const sources = container.querySelectorAll('.swiper-slide picture source');
    let emptyCount = 0;
    let totalCount = 0;
    
    sources.forEach(source => {
      totalCount++;
      const srcset = source.getAttribute('srcset');
      if (!srcset || srcset.trim() === '') {
        emptyCount++;
      }
    });
    
    console.log(`CK checkIfScrollingNeeded: ${emptyCount} empty sources out of ${totalCount} total`);
    
    // Если больше 50% source элементов пустые, нужна прокрутка
    if (totalCount === 0) return false; // Нет source элементов вообще
    return (emptyCount / totalCount) > 0.5;
  }

  /**
   * Подсчет source элементов без srcset
   */
  countEmptySourceElements(container) {
    const sources = container.querySelectorAll('.swiper-slide picture source');
    let emptyCount = 0;
    
    sources.forEach(source => {
      const srcset = source.getAttribute('srcset');
      if (!srcset || srcset.trim() === '') {
        emptyCount++;
      }
    });
    
    return emptyCount;
  }

  /**
   * Ожидание загрузки изображений с мониторингом прогресса (100% требование)
   */
  async waitForImageLoading(container, initialEmptyCount) {
    console.log('CK waitForImageLoading: Starting to monitor image loading (waiting for 100%)...');
    
    const maxWaitTime = 15000; // Увеличиваем до 15 секунд
    const checkInterval = 500; // Проверяем каждые 500мс (дольше между проверками)
    const startTime = Date.now();
    let lastEmptyCount = initialEmptyCount;
    let noProgressCount = 0;
    
    while (Date.now() - startTime < maxWaitTime) {
      const currentEmptyCount = this.countEmptySourceElements(container);
      console.log(`CK waitForImageLoading: Empty sources: ${currentEmptyCount} (was ${initialEmptyCount})`);
      
      // Проверяем прогресс
      if (currentEmptyCount < lastEmptyCount) {
        console.log('CK waitForImageLoading: Progress detected, resetting no-progress counter...');
        noProgressCount = 0;
        lastEmptyCount = currentEmptyCount;
      } else {
        noProgressCount++;
      }
      
      // Если все изображения загружены (0 пустых source элементов)
      if (currentEmptyCount === 0) {
        console.log('CK waitForImageLoading: All images loaded (100%)!');
        await this.wait(1000); // Дополнительная пауза для стабилизации
        break;
      }
      
      // Если нет прогресса в течение 12 проверок (6 секунд)
      if (noProgressCount >= 12) {
        console.log('CK waitForImageLoading: No progress for too long, giving up...');
        break;
      }
      
      await this.wait(checkInterval);
    }
    
    const finalEmptyCount = this.countEmptySourceElements(container);
    const loadedCount = initialEmptyCount - finalEmptyCount;
    const loadedPercentage = initialEmptyCount > 0 ? Math.round((loadedCount / initialEmptyCount) * 100) : 100;
    
    console.log(`CK waitForImageLoading: Finished. Loaded ${loadedCount}/${initialEmptyCount} images (${loadedPercentage}%)`);
    console.log(`CK waitForImageLoading: Final empty sources: ${finalEmptyCount}`);
  }

  /**
   * Извлечение изображений для конкретного цвета
   */
  async extractImagesForColor(colorCode) {
    console.log(`CK extractImagesForColor: Extracting images for color ${colorCode}`);
    
    // Кликаем на цвет если он не выбран
    const colorInput = document.querySelector(`#colorscolorCode input[data-attr-value="${colorCode}"]`);
    if (colorInput && !colorInput.checked) {
      console.log(`CK extractImagesForColor: Clicking on color ${colorCode}`);
      colorInput.click();
      await this.wait(1000); // Ждем загрузки изображений
    }
    
    // Извлекаем изображения для выбранного цвета (scrolling logic is inside extractImages)
    return await this.extractImages();
  }

  /**
   * Извлечение цвета из выбранного элемента
   */
  extractColor() {
    console.log('CK extractColor: Starting color extraction...');
    
    const colorsList = document.querySelector(this.config.selectors.colorsList);
    if (!colorsList) {
      console.log('CK extractColor: No colors list found with selector:', this.config.selectors.colorsList);
      return null;
    }
    
    console.log('CK extractColor: Colors list found:', colorsList);
    
    // Ищем все input элементы для отладки
    const allInputs = colorsList.querySelectorAll('input[type="radio"]');
    console.log(`CK extractColor: Found ${allInputs.length} color inputs`);
    
    // Ищем выбранный (checked) цвет
    const selectedColor = colorsList.querySelector('input[type="radio"]:checked');
    if (!selectedColor) {
      console.log('CK extractColor: No checked color input found');
      
      // Попробуем найти по aria-checked="true"
      const ariaCheckedColor = colorsList.querySelector('input[type="radio"][aria-checked="true"]');
      if (ariaCheckedColor) {
        console.log('CK extractColor: Found color with aria-checked="true"');
        const inputId = ariaCheckedColor.getAttribute('id');
        
        // Находим соответствующий label
        const label = colorsList.querySelector(`label[for="${inputId}"]`);
        if (label) {
          console.log('CK extractColor: Found label for aria-checked color:', label);
          
          // Ищем span с aria-label (содержит название цвета)
          const colorSpan = label.querySelector('span[aria-label]');
          if (colorSpan) {
            const colorName = colorSpan.getAttribute('aria-label');
            console.log('CK extractColor from aria-label (aria-checked):', colorName);
            return colorName;
          }
          
          // Альтернативно ищем скрытый span с текстом
          const hiddenSpan = label.querySelector('span.d-none');
          if (hiddenSpan) {
            const colorName = hiddenSpan.textContent.trim();
            console.log('CK extractColor from hidden span (aria-checked):', colorName);
            return colorName;
          }
        }
        
        // Fallback на data-attr-value
        const colorValue = ariaCheckedColor.getAttribute('data-attr-value');
        console.log('CK extractColor fallback to data-attr-value (aria-checked):', colorValue);
        return colorValue;
      }
      
      return null;
    }
    
    console.log('CK extractColor: Found checked color input:', selectedColor);
    const inputId = selectedColor.getAttribute('id');
    console.log('CK extractColor: Input ID:', inputId);
    
    // Находим соответствующий label
    const label = colorsList.querySelector(`label[for="${inputId}"]`);
    if (label) {
      console.log('CK extractColor: Found label:', label);
      
      // Ищем span с aria-label (содержит название цвета)
      const colorSpan = label.querySelector('span[aria-label]');
      if (colorSpan) {
        const colorName = colorSpan.getAttribute('aria-label');
        console.log('CK extractColor from aria-label:', colorName);
        return colorName;
      }
      
      // Альтернативно ищем скрытый span с текстом
      const hiddenSpan = label.querySelector('span.d-none');
      if (hiddenSpan) {
        const colorName = hiddenSpan.textContent.trim();
        console.log('CK extractColor from hidden span:', colorName);
        return colorName;
      }
      
      console.log('CK extractColor: No color spans found in label');
    } else {
      console.log('CK extractColor: No label found for input ID:', inputId);
    }
    
    // Fallback на data-attr-value
    const colorValue = selectedColor.getAttribute('data-attr-value');
    console.log('CK extractColor fallback to data-attr-value:', colorValue);
    return colorValue;
  }

  /**
   * Извлечение описания товара
   */
  extractDescription() {
    const descElement = document.querySelector(this.config.selectors.descriptionDetail);
    return descElement?.textContent?.trim() || null;
  }

  /**
   * Извлечение состава материала (переопределение базового метода)
   */
  extractComposition() {
    // Ищем контейнер description-and-detail
    const descriptionContainer = document.querySelector('.description-and-detail');
    if (!descriptionContainer) {
      console.log('CK extractComposition: No description container found');
      return null;
    }
    
    // Ищем таблицу контента
    const contentTable = descriptionContainer.querySelector('.content-table');
    if (!contentTable) {
      console.log('CK extractComposition: No content table found');
      return null;
    }
    
    // Ищем строку с "Composition"
    const rows = contentTable.querySelectorAll('.content-row');
    for (const row of rows) {
      const columns = row.querySelectorAll('.content-column');
      if (columns.length >= 2) {
        const label = columns[0].textContent.trim();
        if (label.toLowerCase() === 'composition') {
          const composition = columns[1].textContent.trim();
          console.log('CK extractComposition found:', composition);
          return composition;
        }
      }
    }
    
    console.log('CK extractComposition: No composition found in content table');
    return null;
  }

  /**
   * Извлечение артикула (переопределение базового метода)
   * Используем уникальную часть SKU как артикул
   */
  extractItem() {
    // Получаем JSON-LD данные для извлечения SKU
    const jsonData = this.getJsonLdData();
    const baseSku = this.extractSku(jsonData);
    
    if (!baseSku) {
      console.log('CK extractItem: No base SKU found');
      return null;
    }
    
    // Используем уникальную часть SKU как артикул
    const uniqueProductId = this.extractUniqueProductId(baseSku);
    console.log(`CK extractItem: Using unique product ID as item: ${uniqueProductId} (from base SKU: ${baseSku})`);
    return uniqueProductId;
  }

  /**
   * Ожидание появления JSON-LD скрипта
   */
  async waitForJsonLd(timeout = 10000) {
    console.log('CK waitForJsonLd: Starting to wait for JSON-LD...');
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      const jsonLdScripts = document.querySelectorAll(this.config.selectors.jsonLdScript);
      console.log(`CK waitForJsonLd: Found ${jsonLdScripts.length} script tags`);
      
      for (let script of jsonLdScripts) {
        if (script.textContent.trim() && script.textContent.includes('@type')) {
          const jsonData = this.parseJsonLd(script.textContent);
          if (jsonData && jsonData['@type'] === 'Product') {
            console.log('CK waitForJsonLd: Found Product JSON-LD script');
            return script;
          }
        }
      }
      
      await this.wait(100);
    }
    
    console.log('CK waitForJsonLd: Timeout reached, no Product JSON-LD found');
    return null;
  }

  /**
   * Получение JSON-LD данных продукта
   */
  getJsonLdData() {
    try {
      const jsonLdScripts = document.querySelectorAll(this.config.selectors.jsonLdScript);
      
      for (let script of jsonLdScripts) {
        if (script.textContent.trim() && script.textContent.includes('@type')) {
          const jsonData = this.parseJsonLd(script.textContent);
          if (jsonData && jsonData['@type'] === 'Product') {
            console.log('Found product JSON-LD data:', jsonData);
            return jsonData;
          }
        }
      }
      
      console.log('No product JSON-LD found');
      return null;
    } catch (error) {
      console.error('Error getting JSON-LD data:', error);
      return null;
    }
  }

  /**
   * Извлечение всех доступных цветов
   */
  extractAllColors() {
    const colors = [];
    const colorsList = document.querySelector(this.config.selectors.colorsList);
    
    if (!colorsList) {
      console.log('No colors list found');
      return colors;
    }
    
    const colorInputs = colorsList.querySelectorAll('input[type="radio"]');
    colorInputs.forEach(input => {
      const colorCode = input.getAttribute('data-attr-value');
      const colorLabel = input.closest('li')?.querySelector('label')?.getAttribute('aria-label');
      
      if (colorCode || colorLabel) {
        colors.push({
          code: colorCode,
          name: colorLabel || colorCode,
          isSelected: input.checked
        });
      }
    });
    
    console.log(`Found ${colors.length} colors:`, colors);
    return colors;
  }

  /**
   * Извлечение размеров для текущего выбранного цвета
   */
  async extractSizes() {
    try {
      console.log('Starting CK size extraction...');
      
      const sizesList = document.querySelector(this.config.selectors.sizesList);
      if (!sizesList) {
        console.log('No sizes list found');
        return [];
      }
      
      const sizeInputs = sizesList.querySelectorAll('input[type="radio"]');
      const availableSizes = [];
      
      sizeInputs.forEach(input => {
        const sizeValue = input.getAttribute('data-attr-value');
        const inputId = input.getAttribute('id');
        
        // Находим соответствующий label по for attribute
        const label = sizesList.querySelector(`label[for="${inputId}"]`);
        const sizeLabel = label?.textContent?.trim();
        
        // Проверяем, что размер доступен (не disabled и не aria-disabled)
        const isDisabled = input.disabled || input.getAttribute('aria-disabled') === 'true';
        
        if (!isDisabled && (sizeValue || sizeLabel)) {
          availableSizes.push(sizeLabel || sizeValue);
        }
      });
      
      console.log(`Found ${availableSizes.length} available sizes:`, availableSizes);
      return availableSizes;
      
    } catch (error) {
      console.error('Error in CK extractSizes:', error);
      return [];
    }
  }

  /**
   * Извлечение всех вариантов (цвет + размеры) для создания отдельных продуктов
   */
  async extractAllVariants() {
    try {
      console.log('Starting CK variant extraction...');
      
      const baseJsonData = this.getJsonLdData();
      const baseSku = this.extractSku(baseJsonData);
      const baseName = this.extractName();
      const basePrice = this.extractPrice(baseJsonData);
      const baseCurrency = this.extractCurrency(baseJsonData);
      const baseAvailability = this.extractAvailability(baseJsonData);
      const baseImages = await this.extractImages();
      const baseDescription = this.extractDescription();
      
      if (!baseSku) {
        console.error('No base SKU found, cannot create variants');
        return [];
      }
      
      const colors = this.extractAllColors();
      if (colors.length === 0) {
        console.log('No colors found, creating single variant with current state');
        const sizes = await this.extractSizes();
        const currentColor = this.extractColor();
        
        return sizes.map(size => {
          const uniqueProductId = this.extractUniqueProductId(baseSku);
          const variantSku = `${uniqueProductId}-${currentColor || 'default'}-${size}`;
          
          return {
            sku: variantSku,
            name: baseName,
            price: basePrice,
            currency: baseCurrency,
            availability: baseAvailability,
            color: currentColor,
            size: size,
            all_image_urls: baseImages,
            description: baseDescription,
            product_url: this.sanitizeUrl(window.location.href)
          };
        });
      }
      
      const variants = [];
      
      // Для каждого цвета извлекаем размеры и изображения
      for (const color of colors) {
        console.log(`Processing color: ${color.name} (${color.code})`);
        
        // Кликаем на цвет если он не выбран
        if (!color.isSelected) {
          const colorInput = document.querySelector(`input[data-attr-value="${color.code}"]`);
          if (colorInput) {
            colorInput.click();
            await this.wait(500); // Ждем обновления размеров и изображений
          }
        }
        
        const sizes = await this.extractSizes();
        console.log(`Color ${color.name} has ${sizes.length} sizes:`, sizes);
        
        // Извлекаем изображения для данного цвета
        const colorImages = await this.extractImagesForColor(color.code);
        console.log(`Color ${color.name} has ${colorImages.length} images:`, colorImages);
        
        // Создаем вариант для каждого размера
        sizes.forEach(size => {
          // Используем тот же подход для получения уникального идентификатора
          const uniqueProductId = this.extractUniqueProductId(baseSku);
          const variantSku = `${uniqueProductId}-${color.code}-${size}`;
          
          variants.push({
            sku: variantSku,
            name: baseName,
            price: basePrice,
            currency: baseCurrency,
            availability: baseAvailability,
            color: color.name,
            size: size,
            all_image_urls: colorImages, // Используем изображения для конкретного цвета
            description: baseDescription,
            product_url: this.sanitizeUrl(window.location.href)
          });
        });
      }
      
      console.log(`Created ${variants.length} variants total`);
      return variants;
      
    } catch (error) {
      console.error('Error extracting CK variants:', error);
      return [];
    }
  }

  /**
   * Основной метод парсинга - создает отдельные продукты для каждого варианта
   */
  async parseProduct() {
    try {
      console.log('Starting CK product parsing...');
      
      // Ждем загрузки JSON-LD
      const jsonLdScript = await this.waitForJsonLd();
      if (!jsonLdScript) {
        console.warn('No JSON-LD found, parsing without it');
      }
      
      const variants = await this.extractAllVariants();
      
      if (variants.length === 0) {
        console.error('No variants extracted');
        return [];
      }
      
      // Валидируем каждый вариант
      const validVariants = variants.filter(variant => {
        const validation = this.validateProductData(variant);
        if (!validation.isValid) {
          console.warn(`Invalid variant for ${variant.sku}:`, validation.warnings);
          return false;
        }
        if (validation.warnings.length > 0) {
          console.warn(`Warnings for variant ${variant.sku}:`, validation.warnings);
        }
        return true;
      });
      
      console.log(`Returning ${validVariants.length} valid variants out of ${variants.length} total`);
      return validVariants;
      
    } catch (error) {
      console.error('Error in CK parseProduct:', error);
      return [];
    }
  }
}

// Экспортируем для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CalvinKleinParser;
}