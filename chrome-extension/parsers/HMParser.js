/**
 * Парсер для H&M
 * Содержит всю логику извлечения данных, специфичную для H&M
 */
class HMParser extends BaseParser {
  constructor() {
    super({
      siteName: 'H&M',
      domain: 'hm.com',
      selectors: {
        // JSON-LD script tag (for stable data)
        jsonLdScript: 'script[type="application/ld+json"]',

        // Core product container - first div in main content
        productContainer: '#main-content > div:first-child',

        // Product info selectors (prioritize stable data-testid)
        productTitle: 'h1, [data-testid="product-title"]',
        productPrice: '[data-testid="product-price"], .price, [class*="price"], [class*="Price"], span[class*="price"]',

        // Size selectors - use data-testid for stability
        sizeContainer: '[data-testid="size-selector"]',
        sizeButtons: '[data-testid="size-selector"] button, [data-testid="size-selector"] input[type="radio"]',
        sizeButtonActive: '[aria-selected="true"], [checked], .selected, .active',

        // Color selectors - use data-testid for stability
        colorContainer: '[data-testid="color-selector-wrapper"], [data-testid="color-selector"]',
        colorButtons: '[data-testid="color-selector-wrapper"] button, [data-testid="color-selector"] button',
        colorButtonActive: '[aria-selected="true"], [checked], .selected, .active',

        // Image selectors - specific grid-gallery pattern
        imageGallery: 'ul[data-testid="grid-gallery"]',
        productImages: 'ul[data-testid="grid-gallery"] img',

        // Product details
        productDescription: '[data-testid="product-description"], .product-description',
        productDetails: '[data-testid="product-details"], .product-details',
        productComposition: '[data-testid="composition"], .composition, .material-info',

        // Availability
        addToCartButton: '[data-testid="add-to-cart"], .add-to-cart, button[type="submit"]',
        outOfStockMessage: '[data-testid="out-of-stock"], .out-of-stock, .sold-out',

        // Product ID / SKU
        productCode: '[data-testid="product-code"], .product-code, .article-number'
      }
    });
  }

  /**
   * Проверка, что мы на странице товара H&M
   */
  isValidProductPage() {
    const url = window.location.href;

    if (!url.includes(this.config.domain)) {
      console.log('Not an H&M page');
      return false;
    }

    // H&M URL pattern: contains /productpage. or /product/
    const urlPattern = /\/(productpage\.|product\/)/i;
    const hasValidUrlPattern = urlPattern.test(url);

    if (!hasValidUrlPattern) {
      console.log('URL does not match H&M product page pattern');
      return false;
    }

    // Проверяем наличие JSON-LD или основных элементов продукта
    const hasJsonLd = !!document.querySelector(this.config.selectors.jsonLdScript);
    const hasProductTitle = !!document.querySelector(this.config.selectors.productTitle);
    const hasProductPrice = !!document.querySelector(this.config.selectors.productPrice);


    const isValid = hasValidUrlPattern && (hasJsonLd || hasProductTitle || hasProductPrice);

    return isValid;
  }

  /**
   * Извлечение названия продукта
   */
  extractName() {
    // Приоритет 1: Из JSON-LD (стабильные данные)
    const jsonData = this.getJsonLdData();
    if (jsonData && jsonData.name) {
      return jsonData.name;
    }

    // Приоритет 2: Из DOM элементов (fallback)
    const titleElement = document.querySelector(this.config.selectors.productTitle);
    if (titleElement) {
      const name = titleElement.textContent?.trim();
      return name;
    }

    return null;
  }

  /**
   * Извлечение SKU
   */
  extractSku(jsonData = null) {
    // Приоритет 1: Из URL (наиболее надежный при смене цвета)
    const urlMatch = window.location.href.match(/\.(\d+)\.html$/);
    if (urlMatch && urlMatch[1]) {
      const urlSku = urlMatch[1];

      // URL SKU is most reliable during color changes
      if (!jsonData) {
        jsonData = this.getJsonLdData();
      }

      return urlSku;
    }

    // Приоритет 2: Альтернативный паттерн URL
    const urlMatch2 = window.location.href.match(/\/(\d+)$/);
    if (urlMatch2 && urlMatch2[1]) {
      const urlSku = urlMatch2[1];
      return urlSku;
    }

    // Приоритет 3: Из JSON-LD (fallback)
    if (!jsonData) {
      jsonData = this.getJsonLdData();
    }

    if (jsonData && jsonData.sku) {
      return jsonData.sku;
    }

    // Приоритет 4: Из DOM элементов (product code)
    const productCodeElement = document.querySelector(this.config.selectors.productCode);
    if (productCodeElement) {
      const productCode = productCodeElement.textContent?.trim();
      if (productCode) {
        return productCode;
      }
    }

    return null;
  }

  /**
   * Извлечение цены
   */
  extractPrice(jsonData = null) {
    // Приоритет 1: Из JSON-LD (стабильная цена)
    if (!jsonData) {
      jsonData = this.getJsonLdData();
    }

    if (jsonData && jsonData.offers) {
      if (jsonData.offers.price) {
        const price = parseFloat(jsonData.offers.price);
        return price;
      }

      // Handle offers array
      if (Array.isArray(jsonData.offers) && jsonData.offers.length > 0) {
        const firstOffer = jsonData.offers[0];
        if (firstOffer.price) {
          const price = parseFloat(firstOffer.price);
          return price;
        }
      }
    }

    // Приоритет 2: Из DOM элементов (fallback для текущего варианта)
    const priceElement = document.querySelector(this.config.selectors.productPrice);
    if (priceElement) {
      const priceText = priceElement.textContent?.trim();
      if (priceText) {
        // Extract numeric price from text (handle various formats)
        const priceMatch = priceText.match(/[\d.,]+/);
        if (priceMatch) {
          const price = parseFloat(priceMatch[0].replace(',', '.'));
          return price;
        }
      }
    }

    return null;
  }

  /**
   * Извлечение изображений с поддержкой lazy loading
   */
  async extractImages() {
    try {
      const imageGallery = document.querySelector(this.config.selectors.imageGallery);
      if (!imageGallery) {
        return await this.extractImagesFromJsonLd();
      }

      // Check if scrolling is needed for lazy loading
      const needsScrolling = this.checkIfScrollingNeeded(imageGallery);

      // Force image loading by scrolling if needed
      if (needsScrolling) {
        await this.forceImageLoadingByScroll();
      }

      // Extract images after potential lazy loading
      const images = imageGallery.querySelectorAll(this.config.selectors.productImages);
      const extractedUrls = this.extractImageUrlsFromElements(images);

      if (extractedUrls.length === 0) {
        return await this.extractImagesFromJsonLd();
      }

      return extractedUrls;

    } catch (error) {
      console.error('H&M extractImages: Error during image extraction:', error);
      return await this.extractImagesFromJsonLd();
    }
  }

  /**
   * Check if scrolling is needed to trigger lazy loading
   */
  checkIfScrollingNeeded(imageGallery) {
    const images = imageGallery.querySelectorAll(this.config.selectors.productImages);
    if (images.length === 0) return false;

    let emptyCount = 0;
    let totalCount = images.length;

    images.forEach(img => {
      const src = img.getAttribute('src');
      const srcset = img.getAttribute('srcset');

      // Check if image is not loaded (data URLs, empty src, etc.)
      if (!src ||
          src.startsWith('data:image') ||
          src.includes('placeholder') ||
          (!srcset || srcset.trim() === '')) {
        emptyCount++;
      }
    });

    // If more than 30% of images are not loaded, trigger scrolling
    return totalCount > 0 && (emptyCount / totalCount) > 0.3;
  }

  /**
   * Force image loading by invisible scrolling (no page twitching)
   */
  async forceImageLoadingByScroll() {
    try {
      const imageGallery = document.querySelector(this.config.selectors.imageGallery);
      if (!imageGallery) return;

      // Save current scroll position
      const originalScrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const originalScrollLeft = window.pageXOffset || document.documentElement.scrollLeft;

      // Get document height
      const documentHeight = Math.max(
        document.body.scrollHeight,
        document.body.offsetHeight,
        document.documentElement.clientHeight,
        document.documentElement.scrollHeight,
        document.documentElement.offsetHeight
      );

      // Perform ultra-fast invisible scroll operations
      imageGallery.scrollIntoView({ behavior: 'instant', block: 'center' });
      await this.wait(100);

      window.scrollTo({ top: documentHeight, left: 0, behavior: 'instant' });
      await this.wait(150);

      window.scrollTo({ top: documentHeight / 2, left: 0, behavior: 'instant' });
      await this.wait(100);

      imageGallery.scrollIntoView({ behavior: 'instant', block: 'center' });
      await this.wait(150);

      window.scrollTo({ top: documentHeight, left: 0, behavior: 'instant' });
      await this.wait(100);

      // Restore original scroll position
      window.scrollTo({
        top: originalScrollTop,
        left: originalScrollLeft,
        behavior: 'instant'
      });

      // Final wait for images to finish loading
      await this.wait(800);

    } catch (error) {
      console.warn('H&M forceImageLoadingByScroll: Error during scroll:', error);
      // Try to restore position even if there was an error
      try {
        const originalScrollTop = window.pageYOffset || document.documentElement.scrollTop;
        if (originalScrollTop !== 0) {
          window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
        }
      } catch (restoreError) {
        // Silent fail on restore error
      }
    }
  }

  /**
   * Extract images from JSON-LD (fallback)
   */
  async extractImagesFromJsonLd() {
    const imageUrls = [];
    const jsonData = this.getJsonLdData();

    if (jsonData && jsonData.image) {
      if (Array.isArray(jsonData.image)) {
        jsonData.image.forEach(url => {
          if (url && typeof url === 'string') {
            const enhancedUrl = this.enhanceHMImageQuality(url);
            imageUrls.push(enhancedUrl);
          }
        });
      } else if (typeof jsonData.image === 'string') {
        const enhancedUrl = this.enhanceHMImageQuality(jsonData.image);
        imageUrls.push(enhancedUrl);
      }
    }

    return imageUrls;
  }

  /**
   * Wait helper method
   */
  async wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }


  /**
   * Extract image URL from a single img element
   */
  extractImageUrlFromElement(img) {
    let imageUrl = null;

    // Priority 1: Extract highest quality URL from srcset
    const srcset = img.getAttribute('srcset');
    if (srcset) {
      // Find highest resolution URL (typically 2160w)
      const srcsetMatches = srcset.match(/https?:\/\/[^\s]+\?imwidth=2160/);
      if (srcsetMatches) {
        imageUrl = srcsetMatches[0];
      } else {
        // Fallback to any high-quality URL
        const allMatches = srcset.match(/https?:\/\/[^\s]+\?imwidth=\d+/g);
        if (allMatches && allMatches.length > 0) {
          // Sort by resolution and pick highest
          allMatches.sort((a, b) => {
            const aRes = parseInt(a.match(/imwidth=(\d+)/)[1]);
            const bRes = parseInt(b.match(/imwidth=(\d+)/)[1]);
            return bRes - aRes;
          });
          imageUrl = allMatches[0];
        }
      }
    }

    // Priority 2: Use src attribute
    if (!imageUrl) {
      const src = img.getAttribute('src');
      if (src && src.startsWith('http')) {
        imageUrl = src;
      }
    }

    // Priority 3: Try data-src
    if (!imageUrl) {
      const dataSrc = img.getAttribute('data-src');
      if (dataSrc && dataSrc.startsWith('http')) {
        imageUrl = dataSrc;
      }
    }

    if (imageUrl) {
      // Ensure highest quality for H&M images
      return this.enhanceHMImageQuality(imageUrl);
    }

    return null;
  }

  /**
   * Extract image URLs from image elements (immediate, no waiting)
   */
  extractImageUrlsFromElements(images) {
    const imageUrls = [];

    images.forEach((img) => {
      const imageUrl = this.extractImageUrlFromElement(img);
      if (imageUrl) {
        imageUrls.push(imageUrl);
      }
    });

    return imageUrls;
  }


  /**
   * Enhance H&M image quality specifically
   */
  enhanceHMImageQuality(imageUrl) {
    if (!imageUrl || !imageUrl.includes('image.hm.com')) {
      return imageUrl;
    }

    // For H&M CDN, ensure we get highest quality
    if (imageUrl.includes('?imwidth=')) {
      // Replace with highest quality
      return imageUrl.replace(/\?imwidth=\d+/, '?imwidth=2160');
    } else {
      // Add quality parameter
      return imageUrl + '?imwidth=2160';
    }
  }

  /**
   * Извлечение размеров
   */
  async extractSizes() {
    try {
      const availableSizes = [];

      // Find the specific H&M size selector structure
      const sizeSelector = document.querySelector('[data-testid="size-selector"]');
      if (!sizeSelector) {
        return availableSizes;
      }


      // Find the size list within the size selector
      const sizeList = sizeSelector.querySelector('ul[aria-labelledby="sizeSelector"]');
      if (!sizeList) {
        return availableSizes;
      }


      // Get all size items (li elements)
      const sizeItems = sizeList.querySelectorAll('li');

      sizeItems.forEach((item, index) => {
        const sizeButton = item.querySelector('[data-testid^="sizeButton-"]');
        if (!sizeButton) {
          return;
        }

        const ariaLabel = sizeButton.getAttribute('aria-label');
        if (!ariaLabel) {
          return;
        }

        const sizeMatch = ariaLabel.match(/Size\s+([^:]+):/i);
        if (!sizeMatch) {
          return;
        }

        const sizeName = sizeMatch[1].trim();
        const isOutOfStock = ariaLabel.toLowerCase().includes('out of stock');

        if (!isOutOfStock) {
          if (!availableSizes.includes(sizeName)) {
            availableSizes.push(sizeName);
          }
        }
      });

      return availableSizes;

    } catch (error) {
      console.error('Error in H&M extractSizes:', error);
      return [];
    }
  }


  /**
   * Извлечение цвета
   */
  extractColor() {
    // Method 1: Extract from visible color text (most reliable)
    const colorSelector = document.querySelector('[data-testid="color-selector-wrapper"]');
    if (colorSelector) {
      const colorText = colorSelector.querySelector('p');
      if (colorText) {
        const visibleColor = colorText.textContent?.trim();
        if (visibleColor && visibleColor.length > 0) {
          return visibleColor;
        }
      }
    }

    // Method 2: Check URL for color parameter
    const urlColor = this.extractColorFromUrl();
    if (urlColor) {
      return urlColor;
    }

    // Method 3: Fallback to button analysis
    if (colorSelector) {
      const selectedButton = colorSelector.querySelector('[aria-checked="true"]');
      if (selectedButton) {
        const colorName = this.extractColorNameFromElement(selectedButton);
        if (colorName) {
          return colorName;
        }
      }
    }

    // Method 4: Extract from product title
    const titleElement = document.querySelector(this.config.selectors.productTitle);
    if (titleElement) {
      const title = titleElement.textContent?.trim();
      if (title) {
        const colorMatch = title.match(/[-–]\s*([^-–]+)$/);
        if (colorMatch) {
          return colorMatch[1].trim();
        }
      }
    }

    return null;
  }

  /**
   * Extract color from URL parameters
   */
  extractColorFromUrl() {
    const url = window.location.href;

    // H&M URL patterns for color
    const urlPatterns = [
      /[?&]color[=:]([^&\/]+)/i,
      /[?&]colour[=:]([^&\/]+)/i,
      /\/color\/([^\/]+)/i,
      /\/colour\/([^\/]+)/i,
      /[?&]c[=:]([^&\/]+)/i
    ];

    for (const pattern of urlPatterns) {
      const match = url.match(pattern);
      if (match) {
        return decodeURIComponent(match[1])
          .replace(/[-_]/g, ' ')
          .replace(/\+/g, ' ');
      }
    }

    return null;
  }

  /**
   * Extract color from JSON-LD data
   */
  extractColorFromJsonLd() {
    const jsonData = this.getJsonLdData();
    if (!jsonData) return null;

    // Check color field
    if (jsonData.color) {
      return jsonData.color;
    }

    // Check additionalProperty for color info
    if (jsonData.additionalProperty && Array.isArray(jsonData.additionalProperty)) {
      for (const prop of jsonData.additionalProperty) {
        if (prop.name && prop.value) {
          const name = prop.name.toLowerCase();
          if (name.includes('color') || name.includes('colour')) {
            return prop.value;
          }
        }
      }
    }

    return null;
  }

  /**
   * Extract color from product title
   */
  extractColorFromTitle() {
    const titleElement = document.querySelector(this.config.selectors.productTitle);
    if (!titleElement) return null;

    const title = titleElement.textContent?.trim();
    if (!title) return null;

    // Common color patterns in titles
    const colorPatterns = [
      /[-–]\s*([^-–]+)$/,           // "Product Name - Color"
      /,\s*([^,]+)$/,               // "Product Name, Color"
      /\(\s*([^)]+)\s*\)$/,         // "Product Name (Color)"
      /in\s+([^-–,]+)$/i            // "Product Name in Color"
    ];

    for (const pattern of colorPatterns) {
      const match = title.match(pattern);
      if (match) {
        const potentialColor = match[1].trim();
        if (this.isValidColorName(potentialColor)) {
          return potentialColor;
        }
      }
    }

    return null;
  }

  /**
   * Extract color from URL
   */
  extractColorFromUrl() {
    const url = window.location.href;

    // H&M URL patterns for color
    const urlPatterns = [
      /[?&]color[=:]([^&\/]+)/i,
      /[?&]colour[=:]([^&\/]+)/i,
      /\/color\/([^\/]+)/i,
      /\/colour\/([^\/]+)/i
    ];

    for (const pattern of urlPatterns) {
      const match = url.match(pattern);
      if (match) {
        const urlColor = decodeURIComponent(match[1])
          .replace(/[-_]/g, ' ')
          .replace(/\+/g, ' ');
        if (this.isValidColorName(urlColor)) {
          return urlColor;
        }
      }
    }

    return null;
  }

  /**
   * Extract color from page content
   */
  extractColorFromPageContent() {
    // Look for color information in product details or description
    const textContainers = [
      this.config.selectors.productDetails,
      this.config.selectors.productDescription,
      '.product-info',
      '.product-detail',
      '[class*="detail"]',
      '[class*="description"]'
    ];

    for (const selector of textContainers) {
      const element = document.querySelector(selector);
      if (element) {
        const text = element.textContent;
        const colorMatch = text.match(/(?:Color|Colour):\s*([^.;\n]+)/i);
        if (colorMatch) {
          const color = colorMatch[1].trim();
          if (this.isValidColorName(color)) {
            return color;
          }
        }
      }
    }

    return null;
  }

  /**
   * Check if a string is a valid color name
   */
  isValidColorName(text) {
    if (!text || text.length === 0) return false;

    // Filter out common non-color terms
    const invalidTerms = [
      'select', 'choose', 'pick', 'color', 'colour', 'guide', 'chart',
      'size', 'one size', 'available', 'unavailable', 'sold out'
    ];

    const lowerText = text.toLowerCase();
    for (const term of invalidTerms) {
      if (lowerText === term || lowerText.includes('select ' + term)) {
        return false;
      }
    }

    // Valid if contains common color words or patterns
    const colorKeywords = [
      'white', 'black', 'red', 'blue', 'green', 'yellow', 'pink', 'purple',
      'orange', 'brown', 'grey', 'gray', 'beige', 'navy', 'cream', 'gold',
      'silver', 'tan', 'khaki', 'olive', 'maroon', 'coral', 'turquoise',
      'ivory', 'charcoal', 'burgundy', 'teal', 'mint', 'rose', 'sage'
    ];

    // Check for color keywords or reasonable length
    return colorKeywords.some(keyword => lowerText.includes(keyword)) ||
           (text.length >= 3 && text.length <= 50 && !/^\d+$/.test(text));
  }

  /**
   * Extract color name from a color element
   */
  extractColorNameFromElement(element) {
    if (!element) return null;

    // Try different attributes to get color name
    const ariaLabel = element.getAttribute('aria-label');
    if (ariaLabel) {
      // Clean up aria-label (often contains "Select color: ColorName")
      const colorMatch = ariaLabel.match(/(?:select color|color):\s*(.+)/i);
      if (colorMatch) {
        return colorMatch[1].trim();
      }
      return ariaLabel.trim();
    }

    const dataColor = element.getAttribute('data-color');
    if (dataColor) {
      return dataColor.trim();
    }

    const title = element.getAttribute('title');
    if (title) {
      return title.trim();
    }

    const textContent = element.textContent?.trim();
    if (textContent && textContent.length > 0 && textContent.length < 50) {
      return textContent;
    }

    return null;
  }

  /**
   * Извлечение артикула продукта
   */
  extractItem() {
    // For H&M, use SKU as item/article number
    const sku = this.extractSku();
    if (sku) {
      return sku;
    }

    return null;
  }

  /**
   * Извлечение состава продукта
   */
  extractComposition() {
    try {

      // Method 1: Look for composition in specific H&M DOM structure
      const compositionSelectors = [
        '[data-testid="composition"]',
        '[data-testid="material-content"]',
        '.composition',
        '.material-info'
      ];

      for (const selector of compositionSelectors) {
        const element = document.querySelector(selector);
        if (element) {
          const text = element.textContent?.trim();
          if (text && this.containsCompositionInfo(text)) {
            return this.formatComposition(text);
          }
        }
      }

      // Method 2: Search in product details section
      const productDetails = document.querySelector(this.config.selectors.productDetails);
      if (productDetails) {
        const allParagraphs = productDetails.querySelectorAll('p, div, span');

        for (const element of allParagraphs) {
          const text = element.textContent?.trim();
          if (text && this.containsCompositionInfo(text)) {
            return this.formatComposition(text);
          }
        }
      }

      // Method 3: Search all elements containing composition keywords
      const allElements = document.querySelectorAll('*');
      let searchCount = 0;
      for (const element of allElements) {
        if (element.children.length === 0) { // Only leaf elements
          const text = element.textContent?.trim();
          if (text && text.length > 10 && text.length < 200 && this.containsCompositionInfo(text)) {
            return this.formatComposition(text);
          }
          searchCount++;
          if (searchCount > 1000) break; // Prevent infinite loops
        }
      }

      return null;

    } catch (error) {
      console.error('H&M extractComposition: Error during composition extraction:', error);
      return null;
    }
  }

  /**
   * Check if text contains composition information
   */
  containsCompositionInfo(text) {
    if (!text || text.length < 5) return false;

    const compositionKeywords = ['cotton', 'polyester', 'polyamide', 'spandex', 'elastane', 'wool', 'silk', 'linen', 'viscose', 'acrylic', 'nylon'];
    const lowerText = text.toLowerCase();

    // Must contain at least one material keyword and a percentage
    const hasMaterial = compositionKeywords.some(keyword => lowerText.includes(keyword));
    const hasPercentage = text.includes('%');

    return hasMaterial && hasPercentage;
  }

  /**
   * Format composition text to standard format
   */
  formatComposition(text) {
    if (!text) return null;

    // Simple formatting: extract materials with percentages
    const materialPattern = /([A-Za-z]+)\s*(\d+%)/g;
    const matches = [];
    let match;

    while ((match = materialPattern.exec(text)) !== null) {
      const material = match[1].charAt(0).toUpperCase() + match[1].slice(1).toLowerCase();
      const percentage = match[2];
      matches.push(`${material} ${percentage}`);
    }

    if (matches.length > 0) {
      return matches.join(', ');
    }

    // Fallback: return cleaned text
    return text.trim();
  }

  /**
   * Извлечение валюты
   */
  extractCurrency(jsonData = null) {
    // Try to extract from price element
    const priceElement = document.querySelector(this.config.selectors.productPrice);
    if (priceElement) {
      const priceText = priceElement.textContent?.trim();
      if (priceText) {
        // Look for currency symbols
        if (priceText.includes('$')) return 'USD';
        if (priceText.includes('€')) return 'EUR';
        if (priceText.includes('£')) return 'GBP';
        if (priceText.includes('¥')) return 'JPY';
        if (priceText.includes('kr')) return 'SEK'; // Swedish krona (H&M is Swedish)
      }
    }

    // Fallback to JSON-LD
    if (!jsonData) {
      jsonData = this.getJsonLdData();
    }

    if (jsonData && jsonData.offers) {
      if (jsonData.offers.priceCurrency) {
        return jsonData.offers.priceCurrency;
      }

      if (Array.isArray(jsonData.offers) && jsonData.offers.length > 0) {
        const firstOffer = jsonData.offers[0];
        if (firstOffer.priceCurrency) {
          return firstOffer.priceCurrency;
        }
      }
    }

    // Default fallback based on domain
    if (window.location.href.includes('hm.com/en_us/')) {
      return 'USD';
    }

    return 'USD'; // Default
  }

  /**
   * Извлечение доступности товара
   */
  async extractAvailability(jsonData = null) {

    // Priority 1: Check actual size availability (most reliable)
    const availableSizes = await this.extractSizes();
    if (availableSizes && availableSizes.length > 0) {
      return BaseParser.AVAILABILITY.IN_STOCK;
    }

    // Priority 2: Check for explicit out of stock message
    const outOfStockElement = document.querySelector(this.config.selectors.outOfStockMessage);
    if (outOfStockElement) {
      return BaseParser.AVAILABILITY.OUT_OF_STOCK;
    }

    // Priority 3: Check add to cart button state
    const addToCartButton = document.querySelector(this.config.selectors.addToCartButton);
    if (addToCartButton) {
      if (addToCartButton.disabled || addToCartButton.classList.contains('disabled')) {
        return BaseParser.AVAILABILITY.OUT_OF_STOCK;
      }

      const buttonText = addToCartButton.textContent?.toLowerCase();
      if (buttonText && (buttonText.includes('out of stock') || buttonText.includes('sold out'))) {
        return BaseParser.AVAILABILITY.OUT_OF_STOCK;
      }
    }

    // Priority 4: Check JSON-LD availability (least reliable for H&M)
    if (!jsonData) {
      jsonData = this.getJsonLdData();
    }

    if (jsonData && jsonData.offers) {
      let availability = null;

      if (jsonData.offers.availability) {
        availability = jsonData.offers.availability;
      } else if (Array.isArray(jsonData.offers) && jsonData.offers.length > 0) {
        availability = jsonData.offers[0].availability;
      }

      if (availability) {
        if (availability.includes('OutOfStock') || availability.includes('SoldOut')) {
          return BaseParser.AVAILABILITY.OUT_OF_STOCK;
        }
        if (availability.includes('InStock')) {
          return BaseParser.AVAILABILITY.IN_STOCK;
        }
      }
    }

    // Default to in stock if product page is accessible
    return BaseParser.AVAILABILITY.IN_STOCK;
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
            return jsonData;
          }
        }
      }

      return null;
    } catch (error) {
      console.error('H&M getJsonLdData: Error getting JSON-LD data:', error);
      return null;
    }
  }

  /**
   * Основной метод парсинга
   */
  async parseProduct() {
    try {

      // Проверяем валидность страницы
      if (!this.isValidProductPage()) {
        console.error('H&M parseProduct: Page validation failed');
        return [];
      }


      // Извлекаем данные продукта
      const jsonData = this.getJsonLdData();

      const name = this.extractName();

      const sku = this.extractSku(jsonData);

      const price = this.extractPrice(jsonData);

      const currency = this.extractCurrency(jsonData);

      const availability = await this.extractAvailability(jsonData);

      const color = this.extractColor();

      const composition = this.extractComposition();

      const item = this.extractItem();

      const images = await this.extractImages();

      const sizes = await this.extractSizes();

      if (!sku) {
        console.error('H&M parseProduct: No SKU found, cannot create product');
        return [];
      }

      const product = {
        sku: sku,
        name: name,
        price: price,
        currency: currency,
        availability: availability,
        color: color,
        composition: composition,
        item: item,
        available_sizes: sizes,
        all_image_urls: images,
        main_image_url: images.length > 0 ? images[0] : null,
        product_url: this.sanitizeUrl(window.location.href),
        store: this.config.siteName,
        comment: ''
      };


      // Валидируем данные продукта
      const validation = this.validateProductData(product);

      if (!validation.isValid) {
        console.error('H&M parseProduct: Product validation failed:', validation.warnings);
        return [];
      }

      if (validation.warnings.length > 0) {
        console.warn('H&M parseProduct: Product warnings:', validation.warnings);
      }


      return [product];

    } catch (error) {
      console.error('H&M parseProduct: Error occurred:', error);
      return [];
    }
  }
}

// Экспортируем для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
  module.exports = HMParser;
}