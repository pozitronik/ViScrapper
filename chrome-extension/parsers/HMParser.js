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
    console.log('Checking H&M page validity, URL:', url);

    if (!url.includes(this.config.domain)) {
      console.log('Not an H&M page');
      return false;
    }

    // H&M URL pattern: contains /productpage. or /product/
    const urlPattern = /\/(productpage\.|product\/)/i;
    const hasValidUrlPattern = urlPattern.test(url);
    console.log('Valid H&M URL pattern:', hasValidUrlPattern);

    if (!hasValidUrlPattern) {
      console.log('URL does not match H&M product page pattern');
      return false;
    }

    // Проверяем наличие JSON-LD или основных элементов продукта
    const hasJsonLd = !!document.querySelector(this.config.selectors.jsonLdScript);
    const hasProductTitle = !!document.querySelector(this.config.selectors.productTitle);
    const hasProductPrice = !!document.querySelector(this.config.selectors.productPrice);

    console.log('H&M validation checks:');
    console.log('- JSON-LD found:', hasJsonLd);
    console.log('- Product title found:', hasProductTitle);
    console.log('- Product price found:', hasProductPrice);

    const isValid = hasValidUrlPattern && (hasJsonLd || hasProductTitle || hasProductPrice);
    console.log('Page is valid H&M product page:', isValid);

    return isValid;
  }

  /**
   * Извлечение названия продукта
   */
  extractName() {
    // Приоритет 1: Из JSON-LD (стабильные данные)
    const jsonData = this.getJsonLdData();
    if (jsonData && jsonData.name) {
      console.log('H&M name from JSON-LD:', jsonData.name);
      return jsonData.name;
    }

    // Приоритет 2: Из DOM элементов (fallback)
    const titleElement = document.querySelector(this.config.selectors.productTitle);
    if (titleElement) {
      const name = titleElement.textContent?.trim();
      console.log('H&M name from DOM:', name);
      return name;
    }

    console.log('H&M name not found');
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
      console.log('H&M SKU from URL:', urlSku);

      // Проверяем, совпадает ли с JSON-LD
      if (!jsonData) {
        jsonData = this.getJsonLdData();
      }

      if (jsonData && jsonData.sku && jsonData.sku !== urlSku) {
        console.log('H&M SKU: URL and JSON-LD mismatch. URL:', urlSku, 'JSON-LD:', jsonData.sku, '- using URL');
      }

      return urlSku;
    }

    // Приоритет 2: Альтернативный паттерн URL
    const urlMatch2 = window.location.href.match(/\/(\d+)$/);
    if (urlMatch2 && urlMatch2[1]) {
      const urlSku = urlMatch2[1];
      console.log('H&M SKU from URL (alternative pattern):', urlSku);
      return urlSku;
    }

    // Приоритет 3: Из JSON-LD (fallback)
    if (!jsonData) {
      jsonData = this.getJsonLdData();
    }

    if (jsonData && jsonData.sku) {
      console.log('H&M SKU from JSON-LD (fallback):', jsonData.sku);
      return jsonData.sku;
    }

    // Приоритет 4: Из DOM элементов (product code)
    const productCodeElement = document.querySelector(this.config.selectors.productCode);
    if (productCodeElement) {
      const productCode = productCodeElement.textContent?.trim();
      if (productCode) {
        console.log('H&M SKU from product code element:', productCode);
        return productCode;
      }
    }

    console.log('H&M SKU not found');
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
        console.log('H&M price from JSON-LD:', price);
        return price;
      }

      // Handle offers array
      if (Array.isArray(jsonData.offers) && jsonData.offers.length > 0) {
        const firstOffer = jsonData.offers[0];
        if (firstOffer.price) {
          const price = parseFloat(firstOffer.price);
          console.log('H&M price from JSON-LD offers array:', price);
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
          console.log('H&M price from DOM:', price);
          return price;
        }
      }
    }

    console.log('H&M price not found');
    return null;
  }

  /**
   * Извлечение изображений с поддержкой lazy loading
   */
  async extractImages() {
    console.log('H&M extractImages: Starting image extraction with lazy loading support...');

    try {
      const imageGallery = document.querySelector(this.config.selectors.imageGallery);
      if (!imageGallery) {
        console.log('H&M extractImages: No image gallery found, trying JSON-LD fallback...');
        return await this.extractImagesFromJsonLd();
      }

      // Check if scrolling is needed for lazy loading
      const needsScrolling = this.checkIfScrollingNeeded(imageGallery);
      console.log('H&M extractImages: Scrolling needed:', needsScrolling);

      // Force image loading by scrolling if needed
      if (needsScrolling) {
        console.log('H&M extractImages: Triggering lazy loading with scroll...');
        await this.forceImageLoadingByScroll();
      } else {
        console.log('H&M extractImages: Images already loaded, proceeding...');
      }

      // Extract images after potential lazy loading
      const images = imageGallery.querySelectorAll(this.config.selectors.productImages);
      console.log(`H&M extractImages: Found ${images.length} images after processing`);

      const extractedUrls = this.extractImageUrlsFromElements(images);
      console.log(`H&M extractImages: Extracted ${extractedUrls.length} URLs from gallery`);

      if (extractedUrls.length === 0) {
        console.log('H&M extractImages: No gallery images found, trying JSON-LD fallback...');
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

    console.log(`H&M checkIfScrollingNeeded: ${emptyCount} empty/placeholder images out of ${totalCount} total`);

    // If more than 30% of images are not loaded, trigger scrolling
    return totalCount > 0 && (emptyCount / totalCount) > 0.3;
  }

  /**
   * Force image loading by invisible scrolling (no page twitching)
   */
  async forceImageLoadingByScroll() {
    console.log('H&M forceImageLoadingByScroll: Starting invisible scroll to trigger lazy loading...');

    try {
      const imageGallery = document.querySelector(this.config.selectors.imageGallery);
      if (!imageGallery) {
        console.log('H&M forceImageLoadingByScroll: No image gallery found');
        return;
      }

      // Save current scroll position
      const originalScrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const originalScrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
      console.log(`H&M forceImageLoadingByScroll: Saved original position: ${originalScrollTop}px top, ${originalScrollLeft}px left`);

      // Get document height
      const documentHeight = Math.max(
        document.body.scrollHeight,
        document.body.offsetHeight,
        document.documentElement.clientHeight,
        document.documentElement.scrollHeight,
        document.documentElement.offsetHeight
      );

      console.log('H&M forceImageLoadingByScroll: Document height:', documentHeight);

      // Perform ultra-fast invisible scroll operations
      console.log('H&M forceImageLoadingByScroll: Starting ultra-fast invisible scroll sequence...');

      // 1. Scroll to image gallery
      imageGallery.scrollIntoView({ behavior: 'instant', block: 'center' });
      await this.wait(100);

      // 2. Quick scroll to bottom
      window.scrollTo({ top: documentHeight, left: 0, behavior: 'instant' });
      await this.wait(150);

      // 3. Quick scroll to middle
      window.scrollTo({ top: documentHeight / 2, left: 0, behavior: 'instant' });
      await this.wait(100);

      // 4. Scroll back to gallery area
      imageGallery.scrollIntoView({ behavior: 'instant', block: 'center' });
      await this.wait(150);

      // 5. One more bottom scroll for good measure
      window.scrollTo({ top: documentHeight, left: 0, behavior: 'instant' });
      await this.wait(100);

      // Restore original scroll position (invisible restoration)
      console.log(`H&M forceImageLoadingByScroll: Restoring original position: ${originalScrollTop}px top`);
      window.scrollTo({
        top: originalScrollTop,
        left: originalScrollLeft,
        behavior: 'instant'
      });

      // Final wait for images to finish loading
      console.log('H&M forceImageLoadingByScroll: Final wait for images to load...');
      await this.wait(800);

      console.log('H&M forceImageLoadingByScroll: Invisible scroll completed');

    } catch (error) {
      console.warn('H&M forceImageLoadingByScroll: Error during invisible scroll:', error);

      // Try to restore position even if there was an error
      try {
        const originalScrollTop = window.pageYOffset || document.documentElement.scrollTop;
        if (originalScrollTop !== 0) {
          window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
        }
      } catch (restoreError) {
        console.warn('H&M forceImageLoadingByScroll: Could not restore scroll position');
      }
    }
  }

  /**
   * Extract images from JSON-LD (fallback)
   */
  async extractImagesFromJsonLd() {
    console.log('H&M extractImagesFromJsonLd: Starting JSON-LD fallback...');

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

    console.log(`H&M extractImagesFromJsonLd: Extracted ${imageUrls.length} images from JSON-LD`);
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

    images.forEach((img, index) => {
      const imageUrl = this.extractImageUrlFromElement(img);
      if (imageUrl) {
        imageUrls.push(imageUrl);
        console.log(`H&M extractImageUrlsFromElements: Added image ${index + 1}: ${imageUrl}`);
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
      console.log('H&M extractSizes: Starting size extraction...');
      const availableSizes = [];

      // Find the specific H&M size selector structure
      const sizeSelector = document.querySelector('[data-testid="size-selector"]');
      if (!sizeSelector) {
        console.log('H&M extractSizes: No size-selector found');
        return availableSizes;
      }

      console.log('H&M extractSizes: Found size-selector container');

      // Find the size list within the size selector
      const sizeList = sizeSelector.querySelector('ul[aria-labelledby="sizeSelector"]');
      if (!sizeList) {
        console.log('H&M extractSizes: No size list found with aria-labelledby="sizeSelector"');
        return availableSizes;
      }

      console.log('H&M extractSizes: Found size list container');

      // Get all size items (li elements)
      const sizeItems = sizeList.querySelectorAll('li');
      console.log(`H&M extractSizes: Found ${sizeItems.length} size items`);

      sizeItems.forEach((item, index) => {
        console.log(`H&M extractSizes: Processing size item ${index + 1}`);

        // Find the size button/div within each li
        const sizeButton = item.querySelector('[data-testid^="sizeButton-"]');
        if (!sizeButton) {
          console.log(`H&M extractSizes: No size button found in item ${index + 1}`);
          return;
        }

        // Extract size info from aria-label
        const ariaLabel = sizeButton.getAttribute('aria-label');
        if (!ariaLabel) {
          console.log(`H&M extractSizes: No aria-label found for item ${index + 1}`);
          return;
        }

        console.log(`H&M extractSizes: Item ${index + 1} aria-label: "${ariaLabel}"`);

        // Parse the aria-label to extract size and availability
        // Format: "Size 5-7: Available. Select the size." or "Size XS: Out of stock. Select to see similar products or for notify if back."
        const sizeMatch = ariaLabel.match(/Size\s+([^:]+):/i);
        if (!sizeMatch) {
          console.log(`H&M extractSizes: Could not parse size from aria-label: "${ariaLabel}"`);
          return;
        }

        const sizeName = sizeMatch[1].trim();
        const isOutOfStock = ariaLabel.toLowerCase().includes('out of stock');

        console.log(`H&M extractSizes: Extracted size: "${sizeName}", out of stock: ${isOutOfStock}`);

        // Only include available sizes (you might want to include out of stock sizes too)
        if (!isOutOfStock) {
          if (!availableSizes.includes(sizeName)) {
            availableSizes.push(sizeName);
            console.log(`H&M extractSizes: Added available size: ${sizeName}`);
          } else {
            console.log(`H&M extractSizes: Size ${sizeName} already added`);
          }
        } else {
          console.log(`H&M extractSizes: Skipping out of stock size: ${sizeName}`);
        }
      });

      console.log(`H&M extractSizes: Final result - ${availableSizes.length} available sizes:`, availableSizes);
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
    console.log('H&M extractColor: Starting color extraction...');

    // Method 1: Extract from visible color text (most reliable)
    const colorSelector = document.querySelector('[data-testid="color-selector-wrapper"]');
    if (colorSelector) {
      const colorText = colorSelector.querySelector('p');
      if (colorText) {
        const visibleColor = colorText.textContent?.trim();
        if (visibleColor && visibleColor.length > 0) {
          console.log('H&M extractColor: Found color from visible text:', visibleColor);
          return visibleColor;
        }
      }
    }

    // Method 2: Check URL for color parameter
    const urlColor = this.extractColorFromUrl();
    if (urlColor) {
      console.log('H&M extractColor: Found color in URL:', urlColor);
      return urlColor;
    }

    // Method 3: Fallback to button analysis if visible text not found
    if (colorSelector) {
      console.log('H&M extractColor: Fallback to button analysis...');
      const selectedButton = colorSelector.querySelector('[aria-checked="true"]');
      if (selectedButton) {
        const colorName = this.extractColorNameFromElement(selectedButton);
        if (colorName) {
          console.log('H&M extractColor: Found color from selected button:', colorName);
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
          const color = colorMatch[1].trim();
          console.log('H&M extractColor: Found color in title:', color);
          return color;
        }
      }
    }

    console.log('H&M extractColor: No color found');
    return null;
  }

  /**
   * Extract color from URL parameters
   */
  extractColorFromUrl() {
    const url = window.location.href;
    console.log('H&M extractColorFromUrl: Checking URL:', url);

    // H&M URL patterns for color
    const urlPatterns = [
      /[?&]color[=:]([^&\/]+)/i,
      /[?&]colour[=:]([^&\/]+)/i,
      /\/color\/([^\/]+)/i,
      /\/colour\/([^\/]+)/i,
      /[?&]c[=:]([^&\/]+)/i, // Sometimes H&M uses 'c' parameter
    ];

    for (const pattern of urlPatterns) {
      const match = url.match(pattern);
      if (match) {
        const urlColor = decodeURIComponent(match[1])
          .replace(/[-_]/g, ' ')
          .replace(/\+/g, ' ');
        console.log('H&M extractColorFromUrl: Found color in URL:', urlColor);
        return urlColor;
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
      console.log('H&M extractItem: Using SKU as item:', sku);
      return sku;
    }

    console.log('H&M extractItem: No item found');
    return null;
  }

  /**
   * Извлечение состава продукта
   */
  extractComposition() {
    try {
      console.log('H&M extractComposition: Starting composition extraction...');

      // Method 1: Look for composition in specific H&M DOM structure
      const compositionSelectors = [
        '[data-testid="composition"]',
        '[data-testid="material-content"]',
        '.composition',
        '.material-info'
      ];

      for (const selector of compositionSelectors) {
        console.log(`H&M extractComposition: Trying selector: ${selector}`);
        const element = document.querySelector(selector);
        if (element) {
          const text = element.textContent?.trim();
          console.log(`H&M extractComposition: Found element with text: "${text}"`);
          if (text && this.containsCompositionInfo(text)) {
            console.log('H&M extractComposition: Found composition in DOM:', text);
            return this.formatComposition(text);
          }
        }
      }

      // Method 2: Search in product details section
      console.log('H&M extractComposition: Searching product details section...');
      const productDetails = document.querySelector(this.config.selectors.productDetails);
      if (productDetails) {
        console.log('H&M extractComposition: Found product details container');
        const allParagraphs = productDetails.querySelectorAll('p, div, span');
        console.log(`H&M extractComposition: Found ${allParagraphs.length} elements in product details`);

        for (const element of allParagraphs) {
          const text = element.textContent?.trim();
          if (text && this.containsCompositionInfo(text)) {
            console.log('H&M extractComposition: Found composition in product details:', text);
            return this.formatComposition(text);
          }
        }
      } else {
        console.log('H&M extractComposition: No product details container found');
      }

      // Method 3: Search all elements containing composition keywords
      console.log('H&M extractComposition: Performing broad search...');
      const allElements = document.querySelectorAll('*');
      let searchCount = 0;
      for (const element of allElements) {
        if (element.children.length === 0) { // Only leaf elements
          const text = element.textContent?.trim();
          if (text && text.length > 10 && text.length < 200 && this.containsCompositionInfo(text)) {
            console.log('H&M extractComposition: Found composition in page element:', text);
            return this.formatComposition(text);
          }
          searchCount++;
          if (searchCount > 1000) break; // Prevent infinite loops
        }
      }

      console.log('H&M extractComposition: No composition found after broad search');
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
    console.log('H&M extractAvailability: Starting availability check...');

    // Priority 1: Check actual size availability (most reliable)
    console.log('H&M extractAvailability: Checking size availability...');
    const availableSizes = await this.extractSizes();
    if (availableSizes && availableSizes.length > 0) {
      console.log(`H&M extractAvailability: Found ${availableSizes.length} available sizes, product is in stock`);
      return BaseParser.AVAILABILITY.IN_STOCK;
    }

    // Priority 2: Check for explicit out of stock message
    const outOfStockElement = document.querySelector(this.config.selectors.outOfStockMessage);
    if (outOfStockElement) {
      console.log('H&M extractAvailability: Found out of stock element');
      return BaseParser.AVAILABILITY.OUT_OF_STOCK;
    }

    // Priority 3: Check add to cart button state
    const addToCartButton = document.querySelector(this.config.selectors.addToCartButton);
    if (addToCartButton) {
      if (addToCartButton.disabled || addToCartButton.classList.contains('disabled')) {
        console.log('H&M extractAvailability: Add to cart button is disabled');
        return BaseParser.AVAILABILITY.OUT_OF_STOCK;
      }

      const buttonText = addToCartButton.textContent?.toLowerCase();
      if (buttonText && (buttonText.includes('out of stock') || buttonText.includes('sold out'))) {
        console.log('H&M extractAvailability: Add to cart button indicates out of stock');
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
        console.log('H&M extractAvailability: JSON-LD availability (fallback):', availability);
        if (availability.includes('OutOfStock') || availability.includes('SoldOut')) {
          console.log('H&M extractAvailability: JSON-LD indicates out of stock, but no sizes checked yet');
          return BaseParser.AVAILABILITY.OUT_OF_STOCK;
        }
        if (availability.includes('InStock')) {
          console.log('H&M extractAvailability: JSON-LD indicates in stock');
          return BaseParser.AVAILABILITY.IN_STOCK;
        }
      }
    }

    // Default to in stock if product page is accessible
    console.log('H&M extractAvailability: Defaulting to in stock');
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
            console.log('H&M getJsonLdData: Found Product JSON-LD');
            return jsonData;
          }
        }
      }

      console.log('H&M getJsonLdData: No Product JSON-LD found');
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
      console.log('Starting H&M product parsing...');

      // Проверяем валидность страницы
      if (!this.isValidProductPage()) {
        console.error('H&M parseProduct: Page validation failed');
        return [];
      }

      console.log('H&M parseProduct: Page validation passed, extracting data...');

      // Извлекаем данные продукта
      const jsonData = this.getJsonLdData();
      console.log('H&M parseProduct: JSON-LD data:', jsonData ? 'found' : 'not found');

      const name = this.extractName();
      console.log('H&M parseProduct: Name extracted:', name);

      const sku = this.extractSku(jsonData);
      console.log('H&M parseProduct: SKU extracted:', sku);

      const price = this.extractPrice(jsonData);
      console.log('H&M parseProduct: Price extracted:', price);

      const currency = this.extractCurrency(jsonData);
      console.log('H&M parseProduct: Currency extracted:', currency);

      const availability = await this.extractAvailability(jsonData);
      console.log('H&M parseProduct: Availability extracted:', availability);

      const color = this.extractColor();
      console.log('H&M parseProduct: Color extracted:', color);

      const composition = this.extractComposition();
      console.log('H&M parseProduct: Composition extracted:', composition);

      const item = this.extractItem();
      console.log('H&M parseProduct: Item extracted:', item);

      console.log('H&M parseProduct: Starting image extraction...');
      const images = await this.extractImages();
      console.log('H&M parseProduct: Images extracted:', images.length);

      console.log('H&M parseProduct: Starting size extraction...');
      const sizes = await this.extractSizes();
      console.log('H&M parseProduct: Sizes extracted:', sizes.length);

      if (!sku) {
        console.error('H&M parseProduct: No SKU found, cannot create product');
        return [];
      }

      console.log('H&M parseProduct: Creating product object...');
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

      console.log('H&M parseProduct: Product object created, validating...');

      // Валидируем данные продукта
      const validation = this.validateProductData(product);
      console.log('H&M parseProduct: Validation result:', validation);

      if (!validation.isValid) {
        console.error('H&M parseProduct: Product validation failed:', validation.warnings);
        return [];
      }

      if (validation.warnings.length > 0) {
        console.warn('H&M parseProduct: Product warnings:', validation.warnings);
      }

      console.log('H&M parseProduct: Successfully parsed product:', {
        sku: product.sku,
        name: product.name,
        price: product.price,
        currency: product.currency,
        color: product.color,
        sizesCount: product.available_sizes.length,
        imagesCount: product.all_image_urls.length
      });

      console.log('H&M parseProduct: Returning successful result');
      return [product];

    } catch (error) {
      console.error('H&M parseProduct: Error occurred:', error);
      console.error('H&M parseProduct: Stack trace:', error.stack);
      return [];
    }
  }
}

// Экспортируем для использования в других файлах
if (typeof module !== 'undefined' && module.exports) {
  module.exports = HMParser;
}