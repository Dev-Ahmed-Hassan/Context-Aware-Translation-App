/**
 * Tone Shift — Frontend Application
 * ==================================
 * Handles UI interaction, API communication, and local history management.
 *
 * Architecture:
 *   - All prompt construction is delegated to the backend.
 *   - The frontend sends structured JSON payloads via fetch().
 *   - The explain-mode sends translated_text as a separate field (clean API contract).
 *   - Context hints are passed as structured data for genuine context-awareness.
 */

document.addEventListener('DOMContentLoaded', () => {

    // ── DOM Element References ───────────────────────────────────────
    const sourceText     = document.getElementById('source-text');
    const outputText     = document.getElementById('output-text');
    const charCount      = document.getElementById('char-count');
    const processBtn     = document.getElementById('process-btn');
    const clearBtn       = document.getElementById('clear-btn');
    const copyBtn        = document.getElementById('copy-btn');
    const loader         = document.getElementById('loader');
    const modeRadios     = document.querySelectorAll('input[name="mode"]');
    const targetLangWrap = document.getElementById('target-lang-wrapper');
    const toneSelect     = document.getElementById('tone');
    const explainBtn     = document.getElementById('explain-btn');
    const historyList    = document.getElementById('history-list');
    const clearHistoryBtn= document.getElementById('clear-history');
    const contextHint    = document.getElementById('context-hint');
    const contextWrap    = document.getElementById('context-hint-wrapper');

    // ── API Configuration ────────────────────────────────────────────
    const API_BASE_URL   = 'http://localhost:8000';
    const REQUEST_TIMEOUT_MS = 30000; // 30-second timeout

    // ── Tone Option Lists ────────────────────────────────────────────
    const translateOptions = [
        { value: "Normal",       text: "Normal" },
        { value: "Literal",      text: "Literal" },
        { value: "Literary",     text: "Literary (Rich/Formal)" },
        { value: "Poetic",       text: "Poetic / Lyrical" },
        { value: "Motivational", text: "Motivational" },
        { value: "Satirical",    text: "Satirical / Sarcastic" },
        { value: "Gen Z",        text: "Gen Z Slang" }
    ];

    const refineOptions = [
        { value: "Professional", text: "Professional (Business)" },
        { value: "Casual",       text: "Casual (Friendly)" },
        { value: "Scientific",   text: "Scientific / Academic" },
        { value: "Creative",     text: "Abstract Creative (Bubbling Ideas)" },
        { value: "Poetic",       text: "Poetic" },
        { value: "Motivational", text: "Motivational" },
        { value: "Old English",  text: "Old English (Shakespearean)" },
        { value: "Gen Z",        text: "Gen Z Slang" }
    ];

    // ── Application State ────────────────────────────────────────────
    let currentMode = 'translate';

    // ── Initialise ───────────────────────────────────────────────────
    loadHistory();
    updateToneDropdown('translate');


    // ==================================================================
    //  UI EVENT HANDLERS
    // ==================================================================

    // ── Mode Switch (Translate / Refine) ─────────────────────────────
    modeRadios.forEach(radio => {
        radio.addEventListener('change', (e) => {
            currentMode = e.target.value;

            if (currentMode === 'refine') {
                targetLangWrap.classList.add('hidden');
                explainBtn.classList.add('hidden');
            } else {
                targetLangWrap.classList.remove('hidden');
            }

            updateToneDropdown(currentMode);
        });
    });

    // ── Character Counter ────────────────────────────────────────────
    sourceText.addEventListener('input', () => {
        const count = sourceText.value.length;
        charCount.textContent = `${count} / 5000`;
        charCount.style.color = count > 5000 ? '#ff4757' : '#A0A0A0';
    });

    // ── Clear Button ─────────────────────────────────────────────────
    clearBtn.addEventListener('click', () => {
        sourceText.value = '';
        outputText.value = '';
        charCount.textContent = '0 / 5000';
        explainBtn.classList.add('hidden');
        if (contextHint) contextHint.value = '';
    });

    // ── Copy Button ──────────────────────────────────────────────────
    copyBtn.addEventListener('click', () => {
        if (!outputText.value) return;
        navigator.clipboard.writeText(outputText.value);
        showToast('Copied to clipboard!', 'success');
    });

    // ── Process Text (Main Action) ───────────────────────────────────
    processBtn.addEventListener('click', async () => {
        const text = sourceText.value.trim();
        if (!text) {
            showToast('Please enter some text first.', 'error');
            return;
        }

        toggleLoading(true);
        explainBtn.classList.add('hidden');

        try {
            const data = await callApi({ sourceText: text });
            outputText.value = data.result;

            // Show Explain button only after a successful translation
            if (currentMode === 'translate') {
                explainBtn.classList.remove('hidden');
            }

            addToHistory(text, data.result, toneSelect.value);

        } catch (error) {
            handleApiError(error);
        } finally {
            toggleLoading(false);
        }
    });

    // ── Explain Grammar ──────────────────────────────────────────────
    // Sends structured data (source + translated text as separate fields)
    // instead of building prompt strings on the frontend.
    if (explainBtn) {
        explainBtn.addEventListener('click', async () => {
            const text = sourceText.value.trim();
            const translated = outputText.value.trim();
            if (!text || !translated) return;

            toggleLoading(true);
            const originalOutput = outputText.value;
            outputText.value = "Analyzing grammar...\n(This might take a few seconds)";

            try {
                // Clean API contract: send translated_text as a structured field
                const data = await callApi({
                    sourceText: text,
                    modeOverride: 'explain',
                    translatedText: translated
                });

                outputText.value = `Translation:\n${translated}\n\n=== Grammar & Notes ===\n${data.result}`;

            } catch (error) {
                outputText.value = originalOutput;
                handleApiError(error);
            } finally {
                toggleLoading(false);
            }
        });
    }


    // ==================================================================
    //  HISTORY (Local Storage)
    // ==================================================================

    function addToHistory(original, result, tone) {
        const item = {
            original,
            result,
            tone,
            mode: currentMode,
            date: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };

        const history = JSON.parse(localStorage.getItem('translationHistory') || '[]');
        history.unshift(item);
        if (history.length > 10) history.pop();
        localStorage.setItem('translationHistory', JSON.stringify(history));
        renderHistory();
    }

    function loadHistory() { renderHistory(); }

    function renderHistory() {
        if (!historyList) return;

        const history = JSON.parse(localStorage.getItem('translationHistory') || '[]');
        historyList.innerHTML = '';

        if (history.length === 0) {
            historyList.innerHTML = '<li class="history-empty">No history yet.</li>';
            return;
        }

        history.forEach(item => {
            const li = document.createElement('li');
            li.className = 'history-item';
            li.innerHTML = `
                <div class="history-meta">
                    <span class="badge">${item.mode}</span>
                    <span class="badge-tone">${item.tone}</span>
                    <span class="time">${item.date}</span>
                </div>
                <div class="history-text"><strong>${item.original.substring(0, 40)}${item.original.length > 40 ? '...' : ''}</strong></div>
            `;

            li.addEventListener('click', () => {
                sourceText.value = item.original;
                outputText.value = item.result;
                if (item.mode === 'translate') {
                    explainBtn.classList.remove('hidden');
                } else {
                    explainBtn.classList.add('hidden');
                }
            });

            historyList.appendChild(li);
        });
    }

    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', () => {
            if (confirm('Clear all history?')) {
                localStorage.removeItem('translationHistory');
                renderHistory();
            }
        });
    }


    // ==================================================================
    //  API COMMUNICATION
    // ==================================================================

    /**
     * Send a structured request to the backend API.
     *
     * @param {Object} opts
     * @param {string} opts.sourceText      - The text to process
     * @param {string} [opts.modeOverride]  - Override current mode (e.g. 'explain')
     * @param {string} [opts.translatedText]- Previously translated text (explain mode)
     * @returns {Promise<Object>} Parsed JSON response
     */
    async function callApi({ sourceText: text, modeOverride = null, translatedText = null }) {
        const payload = {
            source_text:     text,
            mode:            modeOverride || currentMode,
            source_lang:     document.getElementById('source-lang').value,
            target_lang:     document.getElementById('target-lang').value,
            tone:            toneSelect.value,
            translated_text: translatedText || null,
            context_hint:    contextHint?.value?.trim() || null
        };

        // Abort controller for timeout handling
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

        try {
            const response = await fetch(`${API_BASE_URL}/process_text`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const error = new Error(errorData.detail || `Server error (${response.status})`);
                error.status = response.status;
                throw error;
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            throw error;
        }
    }


    // ==================================================================
    //  UI HELPERS
    // ==================================================================

    function updateToneDropdown(mode) {
        toneSelect.innerHTML = '';
        const options = mode === 'translate' ? translateOptions : refineOptions;
        options.forEach(opt => {
            const el = document.createElement('option');
            el.value = opt.value;
            el.textContent = opt.text;
            toneSelect.appendChild(el);
        });
    }

    function toggleLoading(isLoading) {
        if (isLoading) {
            loader.classList.remove('hidden');
            processBtn.disabled = true;
            processBtn.innerHTML = `<span>Processing...</span>`;
        } else {
            loader.classList.add('hidden');
            processBtn.disabled = false;
            processBtn.innerHTML = `<span>Process Text</span><i class="fa-solid fa-wand-magic-sparkles"></i>`;
        }
    }

    /**
     * Differentiated error handling for better UX.
     * Shows specific messages for network, timeout, and server errors.
     */
    function handleApiError(error) {
        console.error('[API Error]', error);

        if (error.name === 'AbortError') {
            showToast('Request timed out. The server took too long to respond.', 'error');
        } else if (error.message === 'Failed to fetch') {
            showToast('Cannot connect to server. Is the backend running?', 'error');
        } else if (error.status === 502) {
            showToast('AI model returned an empty response. Try again.', 'error');
        } else if (error.status === 400) {
            showToast(`Invalid request: ${error.message}`, 'error');
        } else {
            showToast(`Error: ${error.message}`, 'error');
        }
    }

    function showToast(message, type = 'success') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
});
