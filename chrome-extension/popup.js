// Check current product status when popup opens
document.addEventListener('DOMContentLoaded', async () => {
  await loadProductInfo();
});

async function loadProductInfo() {
  const productInfoDiv = document.getElementById('product-info');
  
  try {
    const tabs = await new Promise((resolve) => {
      chrome.tabs.query({ active: true, currentWindow: true }, resolve);
    });

    if (!tabs || !tabs[0]) {
      productInfoDiv.innerHTML = '<div style="color: #e74c3c;">No active tab found</div>';
      return;
    }

    // Start with immediate check
    let productData = await extractProductData(tabs[0].id);
    
    if (!productData) {
      // Show waiting message and start background waiting
      productInfoDiv.innerHTML = '<div style="color: #f39c12;">Waiting for product data to load...</div>';
      
      // Background waiting logic
      productData = await waitForProductData(tabs[0].id, 15000); // Wait up to 15 seconds
    }
    
    if (productData) {
      await displayProductInfo(productData);
    } else {
      productInfoDiv.innerHTML = '<div style="color: #6c757d;">No product detected on this page</div>';
      updateStatusDisplay('NOT_PRODUCT', null);
    }
    
  } catch (e) {
    console.error('Error loading product info:', e);
    productInfoDiv.innerHTML = '<div style="color: #e74c3c;">Error loading product data</div>';
  }
}

async function extractProductData(tabId) {
  try {
    const results = await new Promise((resolve, reject) => {
      chrome.scripting.executeScript(
        {
          target: { tabId: tabId },
          func: () => {
            try {
              // Check main script first
              const jsonLdScript = document.getElementById('StructuredDataPDP-json-ld');
              if (jsonLdScript && jsonLdScript.textContent.trim()) {
                const data = JSON.parse(jsonLdScript.textContent);
                if (data.name || data.sku) {
                  return {
                    url: window.location.href,
                    name: data.name,
                    sku: data.sku,
                    brand: data.brand?.name,
                    price: data.offers?.price,
                    currency: data.offers?.priceCurrency,
                    availability: data.offers?.availability,
                    images: data.image?.length || 0,
                    source: 'main-script'
                  };
                }
              }
              
              // Fallback: check all JSON-LD scripts
              const allScripts = document.querySelectorAll('script[type="application/ld+json"]');
              for (let script of allScripts) {
                try {
                  const data = JSON.parse(script.textContent);
                  if (data['@type'] === 'Product' || (data.name && data.sku)) {
                    return {
                      url: window.location.href,
                      name: data.name,
                      sku: data.sku,
                      brand: data.brand?.name,
                      price: data.offers?.price,
                      currency: data.offers?.priceCurrency,
                      availability: data.offers?.availability,
                      images: data.image?.length || 0,
                      source: 'fallback-script'
                    };
                  }
                } catch (e) {
                  continue;
                }
              }
              
              return null;
            } catch (e) {
              return null;
            }
          }
        },
        (results) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve(results);
          }
        }
      );
    });
    
    return results?.[0]?.result;
  } catch (e) {
    return null;
  }
}

async function waitForProductData(tabId, maxWaitTime = 15000) {
  const checkInterval = 1000; // Check every second
  let waited = 0;
  
  while (waited < maxWaitTime) {
    await new Promise(resolve => setTimeout(resolve, checkInterval));
    waited += checkInterval;
    
    const productData = await extractProductData(tabId);
    if (productData) {
      return productData;
    }
    
    // Update waiting message
    const productInfoDiv = document.getElementById('product-info');
    if (productInfoDiv) {
      const remainingSeconds = Math.ceil((maxWaitTime - waited) / 1000);
      productInfoDiv.innerHTML = `<div style="color: #f39c12;">Waiting for product data... (${remainingSeconds}s remaining)</div>`;
    }
  }
  
  return null;
}

async function displayProductInfo(productData) {
  const productInfoDiv = document.getElementById('product-info');
  
  // Check backend status
  let backendStatus = 'unknown';
  try {
    const urlResponse = await fetch(`http://127.0.0.1:8000/api/v1/products/search?q=${encodeURIComponent(productData.url)}`);
    let urlExists = false;
    if (urlResponse.ok) {
      const urlResult = await urlResponse.json();
      urlExists = urlResult.data && urlResult.data.some(product => 
        product.product_url === productData.url
      );
    }

    if (urlExists) {
      backendStatus = 'URL_EXISTS';
      updateStatusDisplay('URL_EXISTS', productData);
    } else if (productData.sku) {
      const skuResponse = await fetch(`http://127.0.0.1:8000/api/v1/products/search?q=${encodeURIComponent(productData.sku)}`);
      let skuExists = false;
      if (skuResponse.ok) {
        const skuResult = await skuResponse.json();
        skuExists = skuResult.data && skuResult.data.some(product => 
          product.sku === productData.sku
        );
      }
      
      if (skuExists) {
        backendStatus = 'SKU_EXISTS';
        updateStatusDisplay('SKU_EXISTS', productData);
      } else {
        backendStatus = 'NEW_PRODUCT';
        updateStatusDisplay('NEW_PRODUCT', productData);
      }
    } else {
      backendStatus = 'NEW_PRODUCT';
      updateStatusDisplay('NEW_PRODUCT', productData);
    }
  } catch (e) {
    console.error('Error checking backend:', e);
  }
  
  // Format product info display
  let infoHtml = '<div style="font-weight: bold; margin-bottom: 6px;">Product Information:</div>';
  
  if (productData.name) {
    infoHtml += `<div><strong>Name:</strong> ${productData.name}</div>`;
  }
  
  if (productData.sku) {
    infoHtml += `<div><strong>SKU:</strong> ${productData.sku}</div>`;
  }
  
  if (productData.brand) {
    infoHtml += `<div><strong>Brand:</strong> ${productData.brand}</div>`;
  }
  
  if (productData.price) {
    const priceText = productData.currency ? `${productData.price} ${productData.currency}` : productData.price;
    infoHtml += `<div><strong>Price:</strong> ${priceText}</div>`;
  }
  
  if (productData.availability) {
    const availText = productData.availability.includes('InStock') ? 'In Stock' : 'Out of Stock';
    infoHtml += `<div><strong>Availability:</strong> ${availText}</div>`;
  }
  
  if (productData.images > 0) {
    infoHtml += `<div><strong>Images:</strong> ${productData.images}</div>`;
  }
  
  infoHtml += `<div style="margin-top: 6px; font-size: 10px; color: #6c757d;">Source: ${productData.source}</div>`;
  
  productInfoDiv.innerHTML = infoHtml;
}

function updateStatusDisplay(status, productData) {
  const statusDiv = document.getElementById('status');
  const button = document.getElementById('scrape');
  const refreshButton = document.getElementById('refresh');
  
  // Hide refresh button by default
  refreshButton.style.display = 'none';
  button.disabled = false;
  
  switch (status) {
    case 'URL_EXISTS':
      statusDiv.textContent = 'Product already saved';
      statusDiv.className = 'status-success';
      button.textContent = 'Re-scrape Product';
      break;
      
    case 'SKU_EXISTS':
      statusDiv.textContent = 'SKU exists - refresh needed for accurate data';
      statusDiv.className = 'status-info';
      button.textContent = 'Scrape Product';
      refreshButton.style.display = 'block';
      break;
      
    case 'NEW_PRODUCT':
      statusDiv.textContent = 'Ready to scrape new product';
      statusDiv.className = 'status-info';
      button.textContent = 'Scrape Product';
      break;
      
    case 'NOT_PRODUCT':
      statusDiv.textContent = 'No product detected on this page';
      statusDiv.className = 'status-error';
      button.disabled = true;
      button.textContent = 'No Product Found';
      break;
  }
}

document.getElementById('scrape').addEventListener('click', async () => {
  const button = document.getElementById('scrape');
  const status = document.getElementById('status');
  const comment = document.getElementById('comment').value.trim();
  
  // Disable button during operation
  button.disabled = true;
  button.textContent = 'Scraping...';
  status.textContent = 'Extracting product data...';
  status.className = 'status-info';

  try {
    // Get current tab
    const tabs = await new Promise((resolve) => {
      chrome.tabs.query({ active: true, currentWindow: true }, resolve);
    });

    if (!tabs || !tabs[0]) {
      throw new Error('No active tab found');
    }

    // Execute parser script
    const results = await new Promise((resolve, reject) => {
      chrome.scripting.executeScript(
        {
          target: { tabId: tabs[0].id },
          files: ['parser.js'],
        },
        (results) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve(results);
          }
        }
      );
    });

    if (!results || !results[0] || !results[0].result) {
      throw new Error('Failed to extract product data from page');
    }

    const data = results[0].result;
    
    // Validate extracted data
    if (!data.name || !data.product_url) {
      throw new Error('Incomplete product data - missing name or URL');
    }

    // Add comment to the data
    data.comment = comment;
    
    status.textContent = 'Sending to server...';
    
    // Send to API
    const response = await fetch('http://127.0.0.1:8000/api/v1/scrape', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    let result;
    try {
      result = await response.json();
    } catch (e) {
      throw new Error(`Failed to parse server response (${response.status}): ${response.statusText}`);
    }
    
    if (!response.ok) {
      // Extract message from nested error structure
      const errorMessage = result.message || 
                           result.detail || 
                           result.error?.message || 
                           `Server Error (${response.status})`;
      
      console.error('Backend error details:', result);
      throw new Error(errorMessage);
    }

    // Success
    status.textContent = 'Product saved successfully!';
    status.className = 'status-success';
    
    // Clear comment field on success
    document.getElementById('comment').value = '';
    updateCharCount();
    
    // Auto-reset after 3 seconds
    setTimeout(() => {
      resetUI();
    }, 3000);
    
  } catch (error) {
    console.error('Scraping error:', error);
    status.textContent = error.message || 'An unexpected error occurred';
    status.className = 'status-error';
    
    // Auto-reset after 5 seconds on error
    setTimeout(() => {
      resetUI();
    }, 5000);
  }
});

function resetUI() {
  const button = document.getElementById('scrape');
  const status = document.getElementById('status');
  
  button.disabled = false;
  button.textContent = 'Scrape Product';
  status.textContent = '';
  status.className = '';
}

function updateCharCount() {
  const comment = document.getElementById('comment').value;
  const charCount = document.getElementById('char-count');
  if (charCount) {
    charCount.textContent = `${comment.length}/500`;
    
    if (comment.length > 450) {
      charCount.style.color = '#e74c3c';
    } else if (comment.length > 400) {
      charCount.style.color = '#f39c12';
    } else {
      charCount.style.color = '#95a5a6';
    }
  }
}

// Character counter for comment field
document.getElementById('comment').addEventListener('input', updateCharCount);

// Initialize character count on load
document.addEventListener('DOMContentLoaded', updateCharCount);

// Refresh button handler
document.getElementById('refresh').addEventListener('click', async () => {
  try {
    const tabs = await new Promise((resolve) => {
      chrome.tabs.query({ active: true, currentWindow: true }, resolve);
    });

    if (tabs && tabs[0]) {
      chrome.tabs.reload(tabs[0].id);
      window.close(); // Close popup after refresh
    }
  } catch (e) {
    console.error('Error refreshing page:', e);
  }
});

