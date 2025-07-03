(async () => {
  async function extractSizeCombinations(sizeContainer1, sizeContainer2) {
    try {
      console.log('Starting size combination extraction...');
      
      // Get size type labels
      const size1Type = getSizeTypeLabel(sizeContainer1);
      const size2Type = getSizeTypeLabel(sizeContainer2);
      
      console.log(`Size types detected: ${size1Type} and ${size2Type}`);
      
      // Get all size1 options (both enabled and disabled)
      const size1Options = Array.from(sizeContainer1.querySelectorAll('[role="radio"]'));
      const combinations = {};
      
      console.log(`Found ${size1Options.length} size1 options to iterate through`);
      
      // Store original state to restore later
      const originallySelected1 = sizeContainer1.querySelector('[role="radio"][aria-checked="true"]');
      const originallySelected2 = sizeContainer2.querySelector('[role="radio"][aria-checked="true"]');
      
      // Iterate through each size1 option
      for (let i = 0; i < size1Options.length; i++) {
        const size1Option = size1Options[i];
        const size1Value = size1Option.getAttribute('data-value');
        
        // Skip if this size1 option is disabled
        if (size1Option.getAttribute('aria-disabled') === 'true') {
          console.log(`Skipping disabled size1 option: ${size1Value}`);
          continue;
        }
        
        console.log(`Clicking size1 option: ${size1Value}`);
        
        // Click the size1 option
        size1Option.click();
        
        // Wait for page to update
        await wait(200);
        
        // Get available size2 options after this size1 selection
        const availableSize2Options = Array.from(sizeContainer2.querySelectorAll('[role="radio"][aria-disabled="false"]'));
        const size2Values = availableSize2Options.map(opt => opt.getAttribute('data-value'));
        
        console.log(`Size1 ${size1Value} -> Available size2 options:`, size2Values);
        
        if (size2Values.length > 0) {
          combinations[size1Value] = size2Values;
        }
      }
      
      // Restore original selections
      try {
        if (originallySelected1) {
          originallySelected1.click();
          await wait(100);
        }
        if (originallySelected2) {
          originallySelected2.click();
          await wait(100);
        }
      } catch (e) {
        console.warn('Could not restore original selections:', e);
      }
      
      console.log('Final combinations extracted:', combinations);
      
      return {
        success: true,
        data: {
          size1_type: size1Type,
          size2_type: size2Type,
          combinations: combinations
        }
      };
      
    } catch (error) {
      console.error('Error extracting size combinations:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }
  
  function getSizeTypeLabel(sizeContainer) {
    try {
      // Look for the label in the parent container
      const parent = sizeContainer.closest('.sc-s4utl4-0');
      if (parent) {
        const labelElement = parent.querySelector('[data-testid]');
        if (labelElement) {
          return labelElement.getAttribute('data-testid');
        }
      }
      
      // Fallback: use aria-label from the radiogroup
      const ariaLabel = sizeContainer.getAttribute('aria-label');
      if (ariaLabel) {
        return ariaLabel;
      }
      
      // Fallback: use data-testid attribute
      const testId = sizeContainer.getAttribute('data-testid');
      if (testId) {
        return testId.replace('BoxSelector-', '');
      }
      
      return 'Unknown';
    } catch (e) {
      console.warn('Could not determine size type label:', e);
      return 'Unknown';
    }
  }
  
  function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  async function parseHtmlContent() {
    const productData = {};

    try {
      // Method 1: Try the specific script ID first
      console.log('Attempting name extraction - Method 1: Specific script ID');
      const jsonLdScript = document.getElementById('StructuredDataPDP-json-ld');
      if (jsonLdScript && jsonLdScript.textContent.trim()) {
        console.log('Found StructuredDataPDP-json-ld script');
        const data = JSON.parse(jsonLdScript.textContent);
        if (data.name) {
          console.log('Successfully extracted name from specific script:', data.name);
          productData.name = data.name;
          productData.sku = data.sku;
          productData.brand = data.brand?.name;

          const offers = data.offers || {};
          productData.price = offers.price;
          productData.currency = offers.priceCurrency;

          const availabilitySchema = offers.availability || '';
          productData.availability = availabilitySchema.includes('InStock') ? 'In Stock' : 'Out of Stock';

          const imageUrls = data.image || [];
          if (imageUrls.length > 0) {
            productData.main_image_url = imageUrls[0].startsWith('http') ? imageUrls[0] : `https://${imageUrls[0]}`;
            productData.all_image_urls = imageUrls.map(img => img.startsWith('http') ? img : `https://${img}`);
          }
        } else {
          console.log('Script found but no name field');
        }
      } else {
        console.log('StructuredDataPDP-json-ld script not found or empty');
      }

      // Method 2: If name still not found, try all JSON-LD scripts
      if (!productData.name) {
        console.log('Attempting name extraction - Method 2: All JSON-LD scripts');
        const allScripts = document.querySelectorAll('script[type="application/ld+json"]');
        console.log(`Found ${allScripts.length} JSON-LD scripts to check`);
        
        for (let i = 0; i < allScripts.length; i++) {
          const script = allScripts[i];
          try {
            const data = JSON.parse(script.textContent);
            console.log(`Checking script ${i + 1}:`, data['@type'], data.name ? 'HAS_NAME' : 'NO_NAME');
            
            if (data['@type'] === 'Product' && data.name) {
              console.log('Successfully extracted name from fallback script:', data.name);
              productData.name = data.name;
              productData.sku = data.sku || productData.sku;
              productData.brand = data.brand?.name || productData.brand;

              if (!productData.price) {
                const offers = data.offers || {};
                productData.price = offers.price;
                productData.currency = offers.priceCurrency;
                const availabilitySchema = offers.availability || '';
                productData.availability = availabilitySchema.includes('InStock') ? 'In Stock' : 'Out of Stock';
              }

              if (!productData.main_image_url) {
                const imageUrls = data.image || [];
                if (imageUrls.length > 0) {
                  productData.main_image_url = imageUrls[0].startsWith('http') ? imageUrls[0] : `https://${imageUrls[0]}`;
                  productData.all_image_urls = imageUrls.map(img => img.startsWith('http') ? img : `https://${img}`);
                }
              }
              break;
            }
          } catch (e) {
            console.log(`Error parsing script ${i + 1}:`, e.message);
            continue;
          }
        }
      }

      // Method 3: Try meta tags as fallback
      if (!productData.name) {
        console.log('Attempting name extraction - Method 3: Meta tags');
        const metaTags = [
          'meta[property="og:title"]',
          'meta[name="twitter:title"]',
          'meta[property="product:name"]',
          'title'
        ];
        
        for (const selector of metaTags) {
          const element = document.querySelector(selector);
          if (element) {
            const name = element.tagName.toLowerCase() === 'title' ? 
              element.textContent.trim() : 
              element.getAttribute('content');
            
            if (name && name.length > 0) {
              console.log(`Successfully extracted name from ${selector}:`, name);
              productData.name = name;
              break;
            }
          }
        }
      }

      // Method 4: Try common CSS selectors as last resort
      if (!productData.name) {
        console.log('Attempting name extraction - Method 4: Common CSS selectors');
        const selectors = [
          'h1[data-testid*="product"]',
          'h1[class*="product"]',
          '.product-name',
          '.product-title',
          '[data-testid="product-name"]',
          '[data-testid="ProductName"]',
          'h1'
        ];
        
        for (const selector of selectors) {
          const element = document.querySelector(selector);
          if (element && element.textContent.trim()) {
            console.log(`Successfully extracted name from ${selector}:`, element.textContent.trim());
            productData.name = element.textContent.trim();
            break;
          }
        }
      }

      // Log final result
      if (productData.name) {
        console.log('Final extracted name:', productData.name);
      } else {
        console.error('FAILED to extract product name using all methods');
      }
    } catch (e) {
      console.error('Error during name extraction:', e);
    }

    try {
      const colorElement = document.querySelector('[data-testid="SelectedChoiceLabel"]');
      if (colorElement) {
        productData.color = colorElement.textContent.replace('|', '').trim();
      }
    } catch (e) {
      console.error('Could not find color information:', e);
    }

    try {
      const sizeContainer1 = document.querySelector('[data-testid="BoxSelector-size1"]');
      const sizeContainer2 = document.querySelector('[data-testid="BoxSelector-size2"]');
      
      // Check if both containers are related (share the same parent section)
      let areContainersRelated = false;
      if (sizeContainer1 && sizeContainer2) {
        // Check if both containers share a common parent within reasonable distance
        const container1Parent = sizeContainer1.closest('.sc-s4utl4-0, .size-selection, .product-variants, .variant-selector, [class*="size"], [class*="variant"]');
        const container2Parent = sizeContainer2.closest('.sc-s4utl4-0, .size-selection, .product-variants, .variant-selector, [class*="size"], [class*="variant"]');
        
        if (container1Parent && container2Parent) {
          areContainersRelated = container1Parent === container2Parent || 
                                container1Parent.contains(sizeContainer2) || 
                                container2Parent.contains(sizeContainer1);
        }
        
        console.log(`Containers related check: ${areContainersRelated}`);
        console.log(`Container1 parent:`, container1Parent?.className);
        console.log(`Container2 parent:`, container2Parent?.className);
      }
      
      // Check if containers have meaningful content
      let hasValidSize1 = false;
      let hasValidSize2 = false;
      let size1Options = [];
      let size2Options = [];
      
      if (sizeContainer1) {
        size1Options = Array.from(sizeContainer1.querySelectorAll('[role="radio"]'));
        const enabledSize1Options = size1Options.filter(opt => opt.getAttribute('aria-disabled') !== 'true');
        hasValidSize1 = enabledSize1Options.length > 0;
        size1Options = enabledSize1Options; // Use only enabled options
      }
      
      if (sizeContainer2 && areContainersRelated) {
        size2Options = Array.from(sizeContainer2.querySelectorAll('[role="radio"]'));
        const enabledSize2Options = size2Options.filter(opt => opt.getAttribute('aria-disabled') !== 'true');
        hasValidSize2 = enabledSize2Options.length > 0;
        size2Options = enabledSize2Options; // Use only enabled options
      }
      
      console.log(`Size detection: Container1 exists: ${!!sizeContainer1}, Container2 exists: ${!!sizeContainer2}, Related: ${areContainersRelated}`);
      console.log(`Size detection: Size1 valid: ${hasValidSize1} (${size1Options.length} options), Size2 valid: ${hasValidSize2} (${size2Options.length} options)`);
      
      // Combination detection - both containers must be related and have options
      const isRealCombination = hasValidSize1 && hasValidSize2 && areContainersRelated;
      
      console.log(`Is real combination product: ${isRealCombination}`);
      
      if (isRealCombination) {
        // Both containers are related and have valid options - this is truly a combination product
        console.log('True dual size selectors detected, extracting combinations...');
        const combinationResult = await extractSizeCombinations(sizeContainer1, sizeContainer2);
        if (combinationResult.success) {
          productData.size_combinations = combinationResult.data;
          console.log('Size combinations extracted:', combinationResult.data);
        } else {
          console.error('Failed to extract size combinations:', combinationResult.error);
          productData.size_combinations = null;
        }
      } else if (hasValidSize1) {
        // Only size1 has valid options OR containers not related - treat as single size
        console.log('Single size selector detected (using size1), extracting simple sizes...');
        const availableSizes = size1Options.map(btn => btn.textContent.trim()).filter(size => size);
        productData.available_sizes = availableSizes;
        console.log('Simple sizes extracted:', availableSizes);
      } else if (hasValidSize2 && !areContainersRelated) {
        // Size2 exists but not related to size1 - treat as single size product
        console.log('Single size selector detected (using unrelated size2), extracting simple sizes...');
        const availableSizes = size2Options.map(btn => btn.textContent.trim()).filter(size => size);
        productData.available_sizes = availableSizes;
        console.log('Simple sizes extracted:', availableSizes);
      } else {
        console.log('No valid size options found');
      }
    } catch (e) {
      console.error('Could not find size information:', e);
    }

    try {
        const compositionContainer = document.querySelector('[data-testid="ProductComposition"]');
        if (compositionContainer) {
            const compositionDetails = compositionContainer.querySelector('.prism-danger-zone');
            if (compositionDetails) {
                productData.composition = Array.from(compositionDetails.querySelectorAll('p')).map(p => p.textContent.trim()).join('\n');
            }
        }
    } catch (e) {
        console.error('Could not find composition information:', e);
    }

    productData.product_url = window.location.href;
    try {
        const itemElement = document.querySelector('[data-testid="ProductInfo-genericId"]');
        if (itemElement) {
            productData.item = itemElement.textContent.trim();
        }
    } catch (e) {
        console.error('Could not find item information:', e);
    }
    productData.comment = '';

    // Final validation and debugging
    console.log('=== FINAL PRODUCT DATA VALIDATION ===');
    console.log('Name:', productData.name ? `"${productData.name}"` : 'MISSING');
    console.log('URL:', productData.product_url ? `"${productData.product_url}"` : 'MISSING');
    console.log('SKU:', productData.sku ? `"${productData.sku}"` : 'MISSING');
    console.log('Brand:', productData.brand ? `"${productData.brand}"` : 'MISSING');
    console.log('Price:', productData.price ? `"${productData.price}"` : 'MISSING');
    
    if (!productData.name) {
        console.error('CRITICAL: Product name is missing! This will cause the "Incomplete product data" error.');
        // Try one more emergency fallback
        const emergencyName = document.title || 'Unknown Product';
        console.log('Using emergency fallback name:', emergencyName);
        productData.name = emergencyName;
    }
    
    if (!productData.product_url) {
        console.error('CRITICAL: Product URL is missing! This will cause the "Incomplete product data" error.');
    }
    
    console.log('=== END VALIDATION ===');

    return productData;
  }

  return await parseHtmlContent();
})();