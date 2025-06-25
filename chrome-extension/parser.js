(() => {
  function parseHtmlContent() {
    const productData = {};

    try {
      const jsonLdScript = document.getElementById('StructuredDataPDP-json-ld');
      if (jsonLdScript) {
        const data = JSON.parse(jsonLdScript.textContent);
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
      }
    } catch (e) {
      console.error('Error parsing JSON-LD:', e);
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
      const sizeContainer = document.querySelector('[data-testid="BoxSelector-size1"]');
      if (sizeContainer) {
        const availableSizes = Array.from(sizeContainer.querySelectorAll('[role="radio"][aria-disabled="false"]')).map(btn => btn.textContent.trim());
        productData.available_sizes = availableSizes;
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
    productData.item = ''; // New field, default empty
    productData.comment = ''; // New field, default empty

    return productData;
  }

  return parseHtmlContent();
})();
