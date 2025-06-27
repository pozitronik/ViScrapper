// Check current product status when popup opens
document.addEventListener('DOMContentLoaded', async () => {
  await checkCurrentStatus();
});

async function checkCurrentStatus() {
  try {
    const tabs = await new Promise((resolve) => {
      chrome.tabs.query({ active: true, currentWindow: true }, resolve);
    });

    if (!tabs || !tabs[0]) return;

    // Get current product data
    const results = await new Promise((resolve, reject) => {
      chrome.scripting.executeScript(
        {
          target: { tabId: tabs[0].id },
          func: () => {
            try {
              const jsonLdScript = document.getElementById('StructuredDataPDP-json-ld');
              if (!jsonLdScript) return null;
              const data = JSON.parse(jsonLdScript.textContent);
              return {
                url: window.location.href,
                sku: data.sku,
                name: data.name
              };
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

    const productData = results?.[0]?.result;
    if (!productData) {
      updateStatusDisplay('NOT_PRODUCT', null);
      return;
    }

    // Check backend for status
    const urlResponse = await fetch(`http://127.0.0.1:8000/api/v1/products/search?q=${encodeURIComponent(productData.url)}`);
    let urlExists = false;
    if (urlResponse.ok) {
      const urlResult = await urlResponse.json();
      urlExists = urlResult.data && urlResult.data.some(product => 
        product.product_url === productData.url
      );
    }

    if (urlExists) {
      updateStatusDisplay('URL_EXISTS', productData);
    } else if (productData.sku) {
      // Check if SKU exists (exact match)
      const skuResponse = await fetch(`http://127.0.0.1:8000/api/v1/products/search?q=${encodeURIComponent(productData.sku)}`);
      let skuExists = false;
      if (skuResponse.ok) {
        const skuResult = await skuResponse.json();
        skuExists = skuResult.data && skuResult.data.some(product => 
          product.sku === productData.sku
        );
      }
      
      if (skuExists) {
        updateStatusDisplay('SKU_EXISTS', productData);
      } else {
        updateStatusDisplay('NEW_PRODUCT', productData);
      }
    } else {
      updateStatusDisplay('NEW_PRODUCT', productData);
    }
  } catch (e) {
    console.error('Error checking status:', e);
  }
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
