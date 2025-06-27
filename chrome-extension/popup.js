document.getElementById('scrape').addEventListener('click', async () => {
  const button = document.getElementById('scrape');
  const status = document.getElementById('status');
  const comment = document.getElementById('comment').value.trim();
  
  // Disable button during operation
  button.disabled = true;
  button.textContent = 'Reloading...';
  status.textContent = 'Refreshing page to get latest data...';
  status.className = 'status-info';

  try {
    // Get current tab
    const tabs = await new Promise((resolve) => {
      chrome.tabs.query({ active: true, currentWindow: true }, resolve);
    });

    if (!tabs || !tabs[0]) {
      throw new Error('No active tab found');
    }

    // Reload the page to ensure fresh JSON-LD data
    await new Promise((resolve) => {
      chrome.tabs.reload(tabs[0].id, () => {
        // Wait for page to fully load
        setTimeout(resolve, 3000);
      });
    });

    status.textContent = 'Extracting product data...';
    button.textContent = 'Scraping...';

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
