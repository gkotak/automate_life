/**
 * Particles Extension - Popup Controller
 *
 * Handles:
 * - Authentication state management
 * - Current page detection
 * - SSE streaming from backend
 * - Real-time progress updates
 * - Duplicate detection and reprocessing
 *
 * Note: Using popup instead of side panel ensures the extension
 * automatically closes when switching tabs or clicking outside.
 */

import { getSupabaseToken, isAuthenticated, openLoginPage, clearToken } from '../lib/auth.js';
import { API_URL, WEB_APP_URL, ENVIRONMENT } from '../config.js';

// Log active environment
console.log(`[CONFIG] Running in ${ENVIRONMENT} mode`);
console.log(`[CONFIG] API_URL: ${API_URL}`);
console.log(`[CONFIG] WEB_APP_URL: ${WEB_APP_URL}`);

// State
let currentUrl = null;
let currentTitle = null;
let currentTabId = null;
let eventSource = null;
let startTime = null;
let elapsedInterval = null;
let duplicateArticleUrl = null;

// DOM Elements
const authSection = document.getElementById('auth-section');
const mainContent = document.getElementById('main-content');
const loginBtn = document.getElementById('login-btn');
const checkAuthBtn = document.getElementById('check-auth-btn');
const pageTitle = document.getElementById('page-title');
const pageUrl = document.getElementById('page-url');
const refreshBtn = document.getElementById('refresh-btn');
const demoVideoCheckbox = document.getElementById('demo-video-checkbox');
const privateCheckbox = document.getElementById('private-checkbox');
const processBtn = document.getElementById('process-btn');
const duplicateWarning = document.getElementById('duplicate-warning');
const duplicateMessage = document.getElementById('duplicate-message');
const viewExistingBtn = document.getElementById('view-existing-btn');
const reprocessBtn = document.getElementById('reprocess-btn');
const processingSection = document.getElementById('processing-section');
const processingStatus = document.getElementById('processing-status');
const processingElapsed = document.getElementById('processing-elapsed');
const stepsContainer = document.getElementById('steps-container');
const resultSection = document.getElementById('result-section');
const resultCard = document.getElementById('result-card');
const resultIcon = document.getElementById('result-icon');
const resultTitle = document.getElementById('result-title');
const resultMessage = document.getElementById('result-message');
const viewArticleBtn = document.getElementById('view-article-btn');

// Initialize
// Note: Popup automatically closes when user clicks outside or switches tabs
async function init() {
  console.log('Initializing Particles extension...');

  // Check authentication status
  const authenticated = await isAuthenticated();

  if (authenticated) {
    console.log('User is authenticated');
    showMainContent();
    await loadCurrentPage();

    // Check for duplicates after loading page info
    await checkForExistingArticle();
  } else {
    console.log('User is not authenticated');
    showAuthSection();
  }

  // Setup event listeners
  setupEventListeners();
}

// Reset all state to fresh values
function resetState() {
  console.log('[RESET] Resetting extension state...');

  currentUrl = null;
  currentTitle = null;
  currentTabId = null;
  duplicateArticleUrl = null;

  // Stop any ongoing processing
  stopProcessing();

  // Reset UI elements
  hideElement(duplicateWarning);
  hideElement(processingSection);
  hideElement(resultSection);

  // Reset checkboxes
  if (demoVideoCheckbox) demoVideoCheckbox.checked = false;
  if (privateCheckbox) privateCheckbox.checked = false;

  // Reset processing status
  if (processingStatus) processingStatus.textContent = 'Processing...';
  if (processingElapsed) processingElapsed.textContent = '0s';
  if (stepsContainer) stepsContainer.innerHTML = '';

  // Enable process button
  if (processBtn) processBtn.disabled = false;
}

// Check if current URL has already been processed
async function checkForExistingArticle() {
  if (!currentUrl) return;

  console.log('[DUPLICATE CHECK] Checking if article already exists...');

  try {
    const token = await getSupabaseToken();
    if (!token) return;

    // Call backend to check if article exists
    const checkUrl = `${API_URL}/api/check-article?url=${encodeURIComponent(currentUrl)}&token=${encodeURIComponent(token)}`;

    const response = await fetch(checkUrl);
    if (!response.ok) {
      console.log('[DUPLICATE CHECK] Backend check failed, proceeding normally');
      return;
    }

    const data = await response.json();

    if (data.exists) {
      console.log('[DUPLICATE CHECK] Article already exists!', data);
      duplicateArticleUrl = data.article_url;
      duplicateMessage.textContent = `This article was already processed on ${new Date(data.created_at).toLocaleDateString()}.`;
      showElement(duplicateWarning);
    } else {
      console.log('[DUPLICATE CHECK] Article not found, ready to process');
    }
  } catch (error) {
    console.error('[DUPLICATE CHECK] Error checking for existing article:', error);
    // Don't block processing if check fails
  }
}

function setupEventListeners() {
  loginBtn.addEventListener('click', async () => {
    console.log('[LOGIN] Opening login page...');
    openLoginPage();

    // Show a loading message
    loginBtn.textContent = 'Waiting for sign in...';
    loginBtn.disabled = true;

    // Poll for authentication every 2 seconds for up to 2 minutes
    let attempts = 0;
    const maxAttempts = 60; // 2 minutes

    const checkAuth = async () => {
      attempts++;
      console.log(`[LOGIN] Checking authentication (attempt ${attempts}/${maxAttempts})...`);

      const authenticated = await isAuthenticated();
      if (authenticated) {
        console.log('[LOGIN] ✅ User authenticated!');
        loginBtn.textContent = 'Sign In to Particles';
        loginBtn.disabled = false;
        showMainContent();
        await loadCurrentPage();
        return;
      }

      if (attempts < maxAttempts) {
        setTimeout(checkAuth, 2000);
      } else {
        console.log('[LOGIN] ⏱️ Timeout waiting for authentication');
        loginBtn.textContent = 'Sign In to Particles';
        loginBtn.disabled = false;
      }
    };

    // Start checking after 3 seconds (give user time to log in)
    setTimeout(checkAuth, 3000);
  });

  checkAuthBtn.addEventListener('click', async () => {
    console.log('[CHECK AUTH] Manually checking authentication...');
    checkAuthBtn.textContent = 'Checking...';
    checkAuthBtn.disabled = true;

    const authenticated = await isAuthenticated();

    if (authenticated) {
      console.log('[CHECK AUTH] ✅ User is authenticated!');
      showMainContent();
      await loadCurrentPage();
    } else {
      console.log('[CHECK AUTH] ❌ Not authenticated yet');
      checkAuthBtn.textContent = 'Check Auth Status';
      checkAuthBtn.disabled = false;
      alert(`Not signed in yet. Please sign in to ${WEB_APP_URL} in another tab first, then click "Check Auth Status" again.`);
    }
  });

  refreshBtn.addEventListener('click', loadCurrentPage);
  processBtn.addEventListener('click', () => processArticle(false));
  viewExistingBtn.addEventListener('click', () => {
    if (duplicateArticleUrl) {
      openArticleAndClose(WEB_APP_URL + duplicateArticleUrl);
    }
  });
  reprocessBtn.addEventListener('click', () => {
    hideElement(duplicateWarning);
    processArticle(true); // Force reprocess
  });
  viewArticleBtn.addEventListener('click', () => {
    if (duplicateArticleUrl) {
      openArticleAndClose(WEB_APP_URL + duplicateArticleUrl);
    }
  });
}

// UI State Management
function showAuthSection() {
  hideElement(mainContent);
  showElement(authSection);
}

function showMainContent() {
  hideElement(authSection);
  showElement(mainContent);
}

function showElement(element) {
  element.classList.remove('hidden');
}

function hideElement(element) {
  element.classList.add('hidden');
}

// Load current page info
async function loadCurrentPage() {
  try {
    const response = await new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: 'GET_CURRENT_TAB' }, resolve);
    });

    if (response.error) {
      throw new Error(response.error);
    }

    currentUrl = response.url;
    currentTitle = response.title;
    currentTabId = response.tabId;

    pageTitle.textContent = currentTitle || 'Untitled Page';
    pageUrl.textContent = currentUrl;

    // Enable process button
    processBtn.disabled = false;
  } catch (error) {
    console.error('Error loading current page:', error);
    pageTitle.textContent = 'Error loading page';
    pageUrl.textContent = error.message;
    processBtn.disabled = true;
  }
}

// Process article
async function processArticle(forceReprocess = false) {
  if (!currentUrl) {
    showError('No URL detected. Please refresh and try again.');
    return;
  }

  if (!currentTabId) {
    showError('No tab ID detected. Please refresh and try again.');
    return;
  }

  // Get auth token
  const token = await getSupabaseToken();
  if (!token) {
    showError('Authentication required. Please sign in.');
    showAuthSection();
    return;
  }

  // Reset UI
  hideElement(resultSection);
  hideElement(duplicateWarning);
  showElement(processingSection);
  processBtn.disabled = true;

  // Initialize steps
  initializeSteps();

  // Start elapsed timer
  startTime = Date.now();
  startElapsedTimer();

  processingStatus.textContent = 'Extracting page content...';

  // Step 1: Extract HTML from the active tab
  console.log(`[PROCESS] Extracting HTML from tab ${currentTabId}...`);
  let pageHtml = null;

  try {
    const extractResult = await new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: 'EXTRACT_PAGE_HTML', tabId: currentTabId }, resolve);
    });

    if (extractResult.error) {
      console.error(`[PROCESS] ❌ Failed to extract HTML: ${extractResult.error}`);
      showError(`Could not extract page content: ${extractResult.error}. This page may not be accessible to the extension.`);
      return;
    }

    pageHtml = extractResult.html;
    console.log(`[PROCESS] ✅ Extracted ${extractResult.contentLength} characters of HTML`);
  } catch (error) {
    console.error(`[PROCESS] ❌ Error extracting HTML: ${error.message}`);
    showError(`Could not extract page content: ${error.message}. This page may not be accessible to the extension.`);
    return;
  }

  // Step 2: Build SSE URL with POST body
  const isDemoVideo = demoVideoCheckbox.checked;
  const isPrivate = privateCheckbox.checked;

  // Use the new extension-specific endpoint that accepts HTML via POST
  let streamUrl = `${API_URL}/api/process-extension?url=${encodeURIComponent(currentUrl)}&token=${encodeURIComponent(token)}`;
  if (forceReprocess) {
    streamUrl += '&force_reprocess=true';
  }
  if (isDemoVideo) {
    streamUrl += '&demo_video=true';
  }
  if (isPrivate) {
    streamUrl += '&is_private=true';
  }

  console.log('[PROCESS] Starting SSE connection with HTML payload...');
  processingStatus.textContent = 'Processing...';

  // Step 3: Use fetch with POST to send HTML, then read SSE stream
  try {
    const response = await fetch(streamUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        html: pageHtml,
        title: currentTitle
      })
    });

    if (!response.ok) {
      const errorText = await response.text();

      // If we get a 401, clear the cached token and prompt re-auth
      if (response.status === 401) {
        console.log('[PROCESS] 401 error - clearing cached token');
        await clearToken();
        showError('Your session has expired. Please sign in again.');
        showAuthSection();
        return;
      }

      throw new Error(`Server error: ${response.status} - ${errorText}`);
    }

    // Read the SSE stream from the response body
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    readSSEStream(reader, decoder);
  } catch (error) {
    console.error(`[PROCESS] ❌ Error starting processing: ${error.message}`);
    handleError(`Failed to process article: ${error.message}`);
  }
}

// Read SSE stream from fetch response
async function readSSEStream(reader, decoder) {
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        console.log('[SSE] Stream ended');
        break;
      }

      // Decode the chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE messages (lines ending with \n\n)
      const messages = buffer.split('\n\n');
      buffer = messages.pop() || ''; // Keep incomplete message in buffer

      for (const message of messages) {
        if (!message.trim()) continue;

        // Parse SSE message
        const lines = message.split('\n');
        let eventType = 'message';
        let data = '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            eventType = line.substring(6).trim();
          } else if (line.startsWith('data:')) {
            data = line.substring(5).trim();
          }
        }

        // Handle the event
        handleSSEEvent(eventType, data);
      }
    }
  } catch (error) {
    console.error('[SSE] Stream reading error:', error);
    handleError('Connection lost. Please try again.');
  }
}

// Handle individual SSE events
function handleSSEEvent(eventType, data) {
  console.log(`[SSE] Event: ${eventType}`, data ? data.substring(0, 100) : '');

  let parsedData = null;
  if (data) {
    try {
      parsedData = JSON.parse(data);
    } catch (e) {
      // Data is not JSON, use as-is
      parsedData = data;
    }
  }

  switch (eventType) {
    case 'ping':
      console.log('Received ping');
      break;

    case 'started':
      processingStatus.textContent = 'Processing article...';
      break;

    case 'duplicate_detected':
      handleDuplicate(parsedData);
      break;

    case 'fetch_start':
      updateStep('fetch', { status: 'processing' });
      break;

    case 'fetch_complete':
      updateStep('fetch', { status: 'complete', detail: 'Content received from browser' });
      break;

    case 'html_received':
      updateStep('fetch', { status: 'complete', detail: `Received ${parsedData?.content_length || 'N/A'} characters from browser` });
      break;

    case 'detecting_audio':
      updateStep('content', {
        status: 'processing',
        detail: `Content type: Audio (${parsedData?.audio_count || 1} file${(parsedData?.audio_count || 1) > 1 ? 's' : ''})`
      });
      break;

    case 'detecting_video':
      updateStep('content', {
        status: 'processing',
        detail: `Content type: Video (${parsedData?.video_count || 1} video${(parsedData?.video_count || 1) > 1 ? 's' : ''})`
      });
      break;

    case 'detecting_text_only':
      updateStep('content', { status: 'complete', detail: 'Content type: Text-only' });
      break;

    case 'content_extract_start':
      updateStep('content', { status: 'processing' });
      break;

    case 'content_extracted':
      updateStep('content', { status: 'complete', detail: 'Content extracted successfully' });
      break;

    case 'processing_audio':
      updateStep('content', { status: 'complete', detail: 'Media type: Audio' });
      updateStep('transcript', {
        status: 'processing',
        detail: `Processing audio ${parsedData?.audio_index || 1} of ${parsedData?.total_audios || 1}...`
      });
      break;

    case 'downloading_audio':
      updateStep('transcript', {
        status: 'processing',
        detail: `Downloading audio... (${parsedData?.file_size_mb || 'N/A'} MB)`
      });
      break;

    case 'audio_downloaded':
      updateStep('transcript', { status: 'processing', detail: 'Audio downloaded, starting transcription...' });
      break;

    case 'transcribing_audio':
      updateStep('transcript', {
        status: 'processing',
        detail: `Transcribing audio... (${parsedData?.duration_minutes || 'N/A'} min)`
      });
      break;

    case 'transcribing_chunk':
      if (parsedData) {
        const substeps = [];
        for (let i = 1; i <= parsedData.total_chunks; i++) {
          if (i < parsedData.chunk_number) {
            substeps.push(`✓ Chunk ${i} of ${parsedData.total_chunks} complete`);
          } else if (i === parsedData.chunk_number) {
            substeps.push(`⏳ Processing chunk ${i} of ${parsedData.total_chunks}...`);
          } else {
            substeps.push(`○ Chunk ${i} of ${parsedData.total_chunks} pending`);
          }
        }
        updateStep('transcript', { substeps });
      }
      break;

    case 'transcript_complete':
      updateStep('transcript', { status: 'complete', detail: 'Transcription complete' });
      break;

    case 'transcript_skipped':
      updateStep('transcript', { status: 'skipped', detail: parsedData?.reason || 'Skipped' });
      break;

    case 'extracting_youtube_transcript':
      updateStep('transcript', { status: 'processing', detail: 'Extracting YouTube transcript...' });
      break;

    case 'youtube_transcript_extracted':
      updateStep('transcript', { status: 'complete', detail: 'YouTube transcript extracted' });
      break;

    case 'ai_start':
      updateStep('ai', { status: 'processing', detail: 'Generating summary with Claude AI...' });
      break;

    case 'ai_complete':
      updateStep('ai', { status: 'complete', detail: 'AI summary generated' });
      break;

    case 'save_start':
      updateStep('save', { status: 'processing', detail: 'Saving to database...' });
      break;

    case 'save_complete':
      updateStep('save', { status: 'complete', detail: 'Saved to database' });
      break;

    case 'completed':
      handleSuccess(parsedData);
      break;

    case 'error':
      handleError(parsedData?.message || 'Unknown error occurred');
      break;

    default:
      console.log(`[SSE] Unhandled event type: ${eventType}`);
  }
}

function initializeSteps() {
  const steps = [
    { id: 'fetch', label: 'Receiving content', status: 'pending' },
    { id: 'content', label: 'Extracting content', status: 'pending' },
    { id: 'transcript', label: 'Processing transcript', status: 'pending' },
    { id: 'ai', label: 'Generating AI summary', status: 'pending' },
    { id: 'save', label: 'Saving to database', status: 'pending' }
  ];

  stepsContainer.innerHTML = '';
  steps.forEach(step => {
    const stepEl = createStepElement(step);
    stepsContainer.appendChild(stepEl);
  });
}

function createStepElement(step) {
  const stepEl = document.createElement('div');
  stepEl.className = 'step';
  stepEl.dataset.stepId = step.id;

  stepEl.innerHTML = `
    <div class="step-icon ${step.status}" data-status="${step.status}">
      ${getStepIcon(step.status)}
    </div>
    <div class="step-content">
      <div class="step-label">${step.label}</div>
      <div class="step-detail"></div>
      <div class="step-duration" style="display: none;"></div>
      <div class="substeps"></div>
    </div>
  `;

  return stepEl;
}

function getStepIcon(status) {
  switch (status) {
    case 'pending': return '○';
    case 'processing': return '◉';
    case 'complete': return '✓';
    case 'skipped': return '○';
    default: return '○';
  }
}

function updateStep(stepId, updates) {
  const stepEl = stepsContainer.querySelector(`[data-step-id="${stepId}"]`);
  if (!stepEl) return;

  const iconEl = stepEl.querySelector('.step-icon');
  const detailEl = stepEl.querySelector('.step-detail');
  const durationEl = stepEl.querySelector('.step-duration');
  const substepsEl = stepEl.querySelector('.substeps');

  if (updates.status) {
    iconEl.className = `step-icon ${updates.status}`;
    iconEl.dataset.status = updates.status;
    iconEl.textContent = getStepIcon(updates.status);

    // Record start time for processing status
    if (updates.status === 'processing' && !stepEl.dataset.startTime) {
      stepEl.dataset.startTime = Date.now();
    }

    // Calculate duration for complete/skipped status
    if ((updates.status === 'complete' || updates.status === 'skipped') && stepEl.dataset.startTime) {
      const duration = Math.floor((Date.now() - stepEl.dataset.startTime) / 1000);
      durationEl.textContent = `${duration}s`;
      durationEl.style.display = 'block';
    }
  }

  if (updates.detail) {
    detailEl.textContent = updates.detail;
  }

  if (updates.substeps && Array.isArray(updates.substeps)) {
    substepsEl.innerHTML = updates.substeps.map(sub =>
      `<div class="substep">${sub}</div>`
    ).join('');
  }
}

function handleDuplicate(data) {
  stopProcessing();

  duplicateArticleUrl = data.url;
  duplicateMessage.textContent = `This article was already processed on ${new Date(data.created_at).toLocaleDateString()}.`;

  hideElement(processingSection);
  showElement(duplicateWarning);
  processBtn.disabled = false;
}

function handleSuccess(data) {
  stopProcessing();

  duplicateArticleUrl = data.url;

  resultCard.className = 'result-card success';
  resultIcon.textContent = '✅';
  resultTitle.textContent = data.already_processed ? 'Article Added!' : 'Success!';
  resultMessage.textContent = data.already_processed
    ? 'This article was already processed and has been added to your library.'
    : 'Article successfully summarized and added to your library!';

  hideElement(processingSection);
  showElement(resultSection);
  processBtn.disabled = false;
}

function handleError(message) {
  stopProcessing();

  resultCard.className = 'result-card error';
  resultIcon.textContent = '❌';
  resultTitle.textContent = 'Error';
  resultMessage.textContent = message;

  hideElement(processingSection);
  showElement(resultSection);
  processBtn.disabled = false;
}

function showError(message) {
  resultCard.className = 'result-card error';
  resultIcon.textContent = '❌';
  resultTitle.textContent = 'Error';
  resultMessage.textContent = message;

  hideElement(processingSection);
  hideElement(duplicateWarning);
  showElement(resultSection);
}

function stopProcessing() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }

  if (elapsedInterval) {
    clearInterval(elapsedInterval);
    elapsedInterval = null;
  }
}

function startElapsedTimer() {
  if (elapsedInterval) {
    clearInterval(elapsedInterval);
  }

  elapsedInterval = setInterval(() => {
    if (!startTime) return;

    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    processingElapsed.textContent = `${elapsed}s`;
  }, 1000);
}

function openInNewTab(url) {
  chrome.runtime.sendMessage({ type: 'OPEN_TAB', url });
}

// Close the popup
function closePopup() {
  window.close();
}

// Open URL in new tab and close the popup
function openArticleAndClose(url) {
  openInNewTab(url);
  // Small delay before closing to ensure tab opens
  setTimeout(() => {
    closePopup();
  }, 200);
}

// Initialize on load
init();
