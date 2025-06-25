document.getElementById('scrape').addEventListener('click', () => {
  const status = document.getElementById('status');
  status.textContent = 'Scraping...';

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    chrome.scripting.executeScript(
      {
        target: { tabId: tabs[0].id },
        files: ['parser.js'],
      },
      (results) => {
        if (chrome.runtime.lastError) {
          status.textContent = `Error: ${chrome.runtime.lastError.message}`;
          return;
        }
        if (results && results[0]) {
          const data = results[0].result;
          status.textContent = 'Sending...';
          fetch('http://127.0.0.1:8000/api/v1/scrape', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
          })
            .then((response) => response.json())
            .then((result) => {
              if (result.status === 'success') {
                status.textContent = 'Success!';
              } else {
                status.textContent = 'Error sending data.';
              }
            })
            .catch((error) => {
              status.textContent = 'Error sending data.';
              console.error('Error:', error);
            });
        }
      }
    );
  });
});
