/**
 * PlacidWay Knowledge Chatbot — Frontend Application Logic
 */

(function () {
  'use strict';

  // DOM Elements
  const chatFeed = document.getElementById('chatFeed');
  const chatForm = document.getElementById('chatForm');
  const messageInput = document.getElementById('messageInput');
  const sendBtn = document.getElementById('sendBtn');
  const starterSection = document.getElementById('starterSection');

  // Conversation state
  const chatHistory = [];
  let isRequestPending = false;

  // Auto-resize textarea
  function resizeTextarea() {
    messageInput.style.height = 'auto';
    const newHeight = Math.min(messageInput.scrollHeight, 120);
    messageInput.style.height = newHeight + 'px';
    sendBtn.disabled = !messageInput.value.trim() || isRequestPending;
  }

  messageInput.addEventListener('input', resizeTextarea);

  // Keydown: Enter sends, Shift+Enter new line
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled) {
        chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
      }
    }
  });

  // Starter pills click handlers
  if (starterSection) {
    starterSection.querySelectorAll('.pill-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const query = btn.getAttribute('data-query');
        if (query && !isRequestPending) {
          messageInput.value = query;
          resizeTextarea();
          chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
        }
      });
    });
  }

  // Smooth scroll to bottom
  function scrollToBottom() {
    chatFeed.scrollTo({
      top: chatFeed.scrollHeight,
      behavior: 'smooth',
    });
  }

  // Helper to escape HTML except converted markdown links
  function formatMarkdown(text) {
    if (!text) return '';
    
    // First escape HTML
    let escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Convert markdown links: [text](url)
    escaped = escaped.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer" class="source-link">$1</a>'
    );

    // Convert bold: **text**
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    return escaped;
  }

  // Append user message
  function appendUserMessage(text) {
    const row = document.createElement('div');
    row.className = 'message-row user-row';
    const bubble = document.createElement('div');
    bubble.className = 'bubble user-bubble';
    bubble.textContent = text;
    row.appendChild(bubble);
    chatFeed.appendChild(row);
    scrollToBottom();
  }

  // Show typing indicator
  function showTypingIndicator() {
    const row = document.createElement('div');
    row.className = 'message-row bot-row typing-row';
    row.id = 'typingIndicator';

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.setAttribute('aria-label', 'PlacidWay assistant is typing');
    indicator.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';

    row.appendChild(indicator);
    chatFeed.appendChild(row);
    scrollToBottom();
  }

  // Remove typing indicator
  function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
      indicator.remove();
    }
  }

  // Append bot response
  function appendBotResponse(data) {
    const row = document.createElement('div');
    row.className = 'message-row bot-row';

    const bubble = document.createElement('div');
    bubble.className = 'bubble bot-bubble';

    // If unanswered, use neutral notice styling
    if (data.answered === false) {
      bubble.classList.add('neutral-notice');
    }

    bubble.innerHTML = formatMarkdown(data.answer);

    // If unanswered, offer direct quote link if not already in text
    if (data.answered === false && !data.answer.includes('placidway.com')) {
      const quotePrompt = document.createElement('p');
      quotePrompt.style.marginTop = '8px';
      quotePrompt.innerHTML = '<a href="https://www.placidway.com" target="_blank" rel="noopener" class="source-link">Request a free quote on PlacidWay</a>';
      bubble.appendChild(quotePrompt);
    }

    row.appendChild(bubble);

    // Sources pills
    if (data.sources && data.sources.length > 0) {
      const sourcesDiv = document.createElement('div');
      sourcesDiv.className = 'sources-container';
      data.sources.forEach((s) => {
        const link = document.createElement('a');
        link.className = 'source-pill';
        link.href = s.url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        // Clean short title
        const shortTitle = s.title.split('|')[0].replace('Alternative', '').trim();
        link.textContent = shortTitle || 'Source Page';
        sourcesDiv.appendChild(link);
      });
      row.appendChild(sourcesDiv);
    }

    // Lead capture card (if cost/treatment answered)
    if (data.suggest_lead_capture) {
      const leadCard = createLeadCaptureCard();
      row.appendChild(leadCard);
    }

    chatFeed.appendChild(row);
    scrollToBottom();
  }

  // Create optional lead capture card
  function createLeadCaptureCard() {
    const card = document.createElement('div');
    card.className = 'lead-card';
    card.innerHTML = `
      <div class="lead-header">Receive a personalized quote</div>
      <div class="lead-desc">Share your details and a medical coordinator will send clinic pricing to your email.</div>
      <div class="lead-inputs">
        <input type="text" class="lead-input" placeholder="Your name" id="leadName">
        <input type="email" class="lead-input" placeholder="Email address" id="leadEmail">
      </div>
      <div class="lead-actions">
        <button type="button" class="lead-submit-btn">Get Free Quote</button>
        <button type="button" class="lead-dismiss-btn">Not now</button>
      </div>
      <div class="lead-status" id="leadStatus"></div>
    `;

    const submitBtn = card.querySelector('.lead-submit-btn');
    const dismissBtn = card.querySelector('.lead-dismiss-btn');
    const nameInput = card.querySelector('#leadName');
    const emailInput = card.querySelector('#leadEmail');
    const statusDiv = card.querySelector('#leadStatus');

    submitBtn.addEventListener('click', async () => {
      const name = nameInput.value.trim();
      const email = emailInput.value.trim();
      if (!name || !email || !email.includes('@')) {
        statusDiv.textContent = 'Please enter a valid name and email address.';
        statusDiv.style.color = '#c93b2b';
        return;
      }
      submitBtn.disabled = true;
      submitBtn.textContent = 'Submitting...';

      try {
        const res = await fetch('/api/lead', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email }),
        });
        if (res.ok) {
          card.innerHTML = '<div class="lead-success">Thank you! Your quote request has been received. A coordinator will be in touch shortly.</div>';
        } else {
          statusDiv.textContent = 'Unable to submit right now. Please try again.';
          submitBtn.disabled = false;
        }
      } catch (err) {
        statusDiv.textContent = 'Network error. Please try again.';
        submitBtn.disabled = false;
      }
    });

    dismissBtn.addEventListener('click', () => {
      card.remove();
    });

    return card;
  }

  // Handle Form Submission
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = messageInput.value.trim();
    if (!query || isRequestPending) return;

    // Remove starter pills on first message
    if (starterSection && starterSection.parentNode) {
      starterSection.remove();
    }

    // Append user bubble
    appendUserMessage(query);

    // Record in history
    chatHistory.push({ role: 'user', content: query });

    // Clear input
    messageInput.value = '';
    resizeTextarea();

    // Disable input while waiting
    isRequestPending = true;
    sendBtn.disabled = true;
    showTypingIndicator();

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: query,
          history: chatHistory.slice(-8), // Send recent turns
        }),
      });

      removeTypingIndicator();

      if (!res.ok) {
        throw new Error('Server returned HTTP ' + res.status);
      }

      const data = await res.json();

      // Record model response in history
      chatHistory.push({ role: 'model', content: data.answer });

      appendBotResponse(data);
    } catch (err) {
      console.error('Chat error:', err);
      removeTypingIndicator();
      appendBotResponse({
        answer: "I'm a bit busy, please try again in a moment.",
        sources: [],
        answered: false,
        suggest_lead_capture: false,
      });
    } finally {
      isRequestPending = false;
      resizeTextarea();
      messageInput.focus();
    }
  });

  // Initial focus
  messageInput.focus();
})();
