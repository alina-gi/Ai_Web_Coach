(() => {
  const chatWindow = document.getElementById('chatWindow');
  const chatForm = document.getElementById('chatForm');
  const messageInput = document.getElementById('messageInput');
  const moodBar = document.getElementById('moodBar');

  const STORAGE_KEY = 'chat_history_v1';
  let history = []; // Declare history variable

  function loadHistory() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : [];
      if (Array.isArray(parsed)) history = parsed;
    } catch (_) {
      history = [];
    }
  }

  function saveHistory() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    } catch (_) {}
  }

  function moodEmoji(mood) {
    if (!mood) return '🤖';
    const m = (mood + '').toLowerCase();
    if (m.includes('positive') || m.includes('happy') || m.includes('optim')) return '😊';
    if (m.includes('negative') || m.includes('sad') || m.includes('anger')) return '😕';
    if (m.includes('neutral') || m.includes('calm') || m.includes('balanced')) return '😐';
    if (m.includes('excited') || m.includes('energetic')) return '😄';
    if (m.includes('stressed') || m.includes('anxious')) return '😟';
    return '🤖';
  }

  function updateMoodBar(mood) {
    if (!moodBar) return;
    if (!mood) {
      moodBar.textContent = '';
      return;
    }
    const emoji = moodEmoji(mood);
    moodBar.textContent = `Mood detected: ${mood} ${emoji}`;
  }

  function appendMessage(text, role = 'user', options = {}) {
    const wrapper = document.createElement('div');
    wrapper.className = `message ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;
    wrapper.appendChild(bubble);

    // Feedback actions for AI messages
    if (role === 'ai') {
      const actions = document.createElement('div');
      actions.className = 'actions';

      const up = document.createElement('span');
      up.className = 'btn-icon';
      up.title = 'Positive feedback';
      up.textContent = '👍';

      const down = document.createElement('span');
      down.className = 'btn-icon';
      down.title = 'Negative feedback';
      down.textContent = '👎';

      const thanks = document.createElement('span');
      thanks.className = 'thank-you';
      thanks.style.display = 'none';
      thanks.textContent = 'Thanks for your feedback';

      actions.appendChild(up);
      actions.appendChild(down);
      actions.appendChild(thanks);
      wrapper.appendChild(actions);

      const userTextForFeedback = options.userText || '';
      const detectedMood = options.mood || '';
      const aiTextForFeedback = text;

      async function sendFeedback(kind) {
        try {
          const res = await fetch('/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              message: userTextForFeedback,
              response: aiTextForFeedback,
              feedback: kind,
              mood: detectedMood
            })
          });
          if (!res.ok) throw new Error('feedback failed');
          thanks.style.display = '';
        } catch (e) {
          console.error('Feedback error', e);
        }
      }

      up.addEventListener('click', () => sendFeedback('positive'));
      down.addEventListener('click', () => sendFeedback('negative'));
    }

    chatWindow.appendChild(wrapper);
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  async function sendMessage(message) {
    appendMessage(message, 'user');
    history.push({ role: 'user', text: message });
    saveHistory();

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message })
      });

      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}`);
      }

      const data = await response.json();
      const aiText = data && typeof data.response === 'string' ? data.response : 'Sorry, I had trouble responding.';
      appendMessage(aiText, 'ai', { userText: message, mood: data && data.detected_mood });

      // Store AI message with mood
      history.push({ role: 'ai', text: aiText, meta: { mood: data && data.detected_mood, userText: message } });
      saveHistory();

      // Update mood bar and border color based on detected mood
      updateMoodBar(data && data.detected_mood);
      
      // Update border color based on mood (moved here after data is defined)
      if (data && data.detected_mood) {
        if (data.detected_mood === "positive") chatWindow.style.borderColor = "limegreen";
        else if (data.detected_mood === "negative") chatWindow.style.borderColor = "red";
        else chatWindow.style.borderColor = "gray";
      }
    } catch (err) {
      appendMessage('Network error. Please try again.', 'ai');
      console.error(err);
    }
  }

  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = (messageInput.value || '').trim();
    if (!text) return;
    messageInput.value = '';
    sendMessage(text);
  });

  // Optional: submit on Enter without adding a newline
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      chatForm.dispatchEvent(new Event('submit'));
    }
  });

  // Initial load: render history and last mood
  loadHistory();
  if (Array.isArray(history) && history.length) {
    for (const item of history) {
      if (!item || !item.role) continue;
      if (item.role === 'user') {
        appendMessage(item.text, 'user');
      } else if (item.role === 'ai') {
        appendMessage(item.text, 'ai', { userText: item.meta && item.meta.userText, mood: item.meta && item.meta.mood });
      }
    }
    // find last mood in history
    for (let i = history.length - 1; i >= 0; i--) {
      const it = history[i];
      if (it.role === 'ai' && it.meta && it.meta.mood) {
        updateMoodBar(it.meta.mood);
        break;
      }
    }
  }
})();


