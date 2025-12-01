/**
 * Background Service Worker for Particles Extension
 *
 * Handles:
 * - Communicating with popup via chrome.runtime messaging
 * - Extracting page HTML via chrome.scripting
 * - Opening new tabs
 *
 * Note: Using popup (instead of side panel) means the extension
 * automatically closes when switching tabs or clicking outside.
 * No tracking or manual closing logic needed.
 */

// Handle messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'GET_CURRENT_TAB') {
    // Get the current active tab
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        sendResponse({
          url: tabs[0].url,
          title: tabs[0].title,
          tabId: tabs[0].id,
          favIconUrl: tabs[0].favIconUrl
        });
      } else {
        sendResponse({ error: 'No active tab found' });
      }
    });
    return true; // Keep channel open for async response
  }

  if (message.type === 'EXTRACT_PAGE_HTML') {
    // Extract HTML from the specified tab
    const tabId = message.tabId;

    if (!tabId) {
      sendResponse({ error: 'No tab ID provided' });
      return true;
    }

    console.log(`[EXTRACT] Extracting HTML from tab ${tabId}...`);

    // Use chrome.scripting to inject script and get HTML
    chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: () => {
        try {
          // Get the full HTML of the page
          const html = document.documentElement.outerHTML;

          // Also get some metadata
          const title = document.title;
          const contentLength = html.length;

          console.log(`[EXTRACT SCRIPT] Extracted HTML: ${contentLength} characters`);

          return {
            success: true,
            html: html,
            title: title,
            contentLength: contentLength
          };
        } catch (error) {
          console.error('[EXTRACT SCRIPT] Error:', error);
          return {
            success: false,
            error: error.message
          };
        }
      }
    }).then((results) => {
      if (results && results[0] && results[0].result) {
        const result = results[0].result;
        if (result.success) {
          console.log(`[EXTRACT] ✅ Successfully extracted ${result.contentLength} characters`);
          sendResponse(result);
        } else {
          console.error(`[EXTRACT] ❌ Script error: ${result.error}`);
          sendResponse({ error: result.error });
        }
      } else {
        console.error('[EXTRACT] ❌ No results from script execution');
        sendResponse({ error: 'Failed to extract HTML - no results' });
      }
    }).catch((error) => {
      console.error(`[EXTRACT] ❌ Error executing script: ${error.message}`);
      sendResponse({ error: `Failed to extract HTML: ${error.message}` });
    });

    return true; // Keep channel open for async response
  }

  if (message.type === 'OPEN_TAB') {
    // Open a new tab with the given URL
    chrome.tabs.create({ url: message.url });
    sendResponse({ success: true });
    return true;
  }

});

console.log('Particles extension background service worker loaded');
