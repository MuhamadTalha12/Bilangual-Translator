/**
 * Bilangual AI - English ⇄ Urdu Neural Translator & Compliance Engine
 * Frontend Application Controller strictly implementing the Architecture Flowchart
 */

(function () {
  'use strict';

  // --- Application State ---
  const state = {
    sourceLang: 'en',
    targetLang: 'ur',
    inputText: '',
    translatedText: '',
    pronunciation: '',
    riskLevel: 'LOW_RISK_APPROVED',
    riskDetails: '',
    needsHumanReview: false,
    sessionId: 'session_' + Math.random().toString(36).substring(2, 9),
    isTranslating: false,
    mismatchDetected: false,
    mismatchType: null,
    debounceTimer: null,
    history: [],
    isListening: false,
    theme: localStorage.getItem('bilangual_theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),
    archVisualizerOpen: false
  };

  const URDU_REGEX = /[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]/g;
  const ENGLISH_REGEX = /[a-zA-Z]/g;

  // --- DOM Elements ---
  const elements = {
    html: document.documentElement,
    themeToggleBtn: document.getElementById('themeToggleBtn'),
    themeIconSun: document.getElementById('themeIconSun'),
    themeIconMoon: document.getElementById('themeIconMoon'),
    toggleArchBtn: document.getElementById('toggleArchBtn'),
    archVisualizer: document.getElementById('archVisualizer'),

    // Flowchart Steps
    stepA: document.getElementById('stepA'),
    stepB: document.getElementById('stepB'),
    stepC: document.getElementById('stepC'),
    stepE: document.getElementById('stepE'),
    stepF: document.getElementById('stepF'),
    stepJ: document.getElementById('stepJ'),
    stepK: document.getElementById('stepK'),
    stepBranch: document.getElementById('stepBranch'),
    branchLabel: document.getElementById('branchLabel'),
    stepP: document.getElementById('stepP'),

    // CRAWL, WALK, RUN Risk Framework Elements
    cwrPillCrawl: document.getElementById('cwrPillCrawl'),
    cwrPillWalk: document.getElementById('cwrPillWalk'),
    cwrPillRun: document.getElementById('cwrPillRun'),
    cwrCrawlBadge: document.getElementById('cwrCrawlBadge'),
    cwrWalkBadge: document.getElementById('cwrWalkBadge'),
    cwrRunBadge: document.getElementById('cwrRunBadge'),

    // Direction Controls
    modeEnToUrBtn: document.getElementById('modeEnToUrBtn'),
    modeUrToEnBtn: document.getElementById('modeUrToEnBtn'),
    swapDirectionBtn: document.getElementById('swapDirectionBtn'),
    sourceLangBadge: document.getElementById('sourceLangBadge'),
    sourceLangName: document.getElementById('sourceLangName'),
    targetLangBadge: document.getElementById('targetLangBadge'),
    targetLangName: document.getElementById('targetLangName'),

    // Mismatch Banner
    mismatchBanner: document.getElementById('mismatchBanner'),
    mismatchMessage: document.getElementById('mismatchMessage'),
    autoSwitchActionBtn: document.getElementById('autoSwitchActionBtn'),
    autoSwitchBtnText: document.getElementById('autoSwitchBtnText'),

    // Panes
    sourceInput: document.getElementById('sourceInput'),
    clearInputBtn: document.getElementById('clearInputBtn'),
    charCount: document.getElementById('charCount'),
    manualTranslateBtn: document.getElementById('manualTranslateBtn'),

    targetOutput: document.getElementById('targetOutput'),
    targetLoading: document.getElementById('targetLoading'),
    pronunciationWrap: document.getElementById('pronunciationWrap'),
    pronunciationText: document.getElementById('pronunciationText'),
    latencyBadge: document.getElementById('latencyBadge'),
    confidenceBadge: document.getElementById('confidenceBadge'),
    targetStatusText: document.getElementById('targetStatusText'),
    riskStatusBadge: document.getElementById('riskStatusBadge'),
    riskBadgeText: document.getElementById('riskBadgeText'),

    // Node N: Human-in-the-Loop Review Box
    hitlReviewBox: document.getElementById('hitlReviewBox'),
    hitlReasonText: document.getElementById('hitlReasonText'),
    hitlEditText: document.getElementById('hitlEditText'),
    hitlNotesInput: document.getElementById('hitlNotesInput'),
    hitlAcceptBtn: document.getElementById('hitlAcceptBtn'),
    hitlCorrectBtn: document.getElementById('hitlCorrectBtn'),
    hitlRejectBtn: document.getElementById('hitlRejectBtn'),

    // Toolbar Tools
    micBtn: document.getElementById('micBtn'),
    copyBtn: document.getElementById('copyBtn'),
    starBtn: document.getElementById('starBtn'),

    // Telemetry & Monitoring Deck (Nodes Q, R, S)
    refreshMetricsBtn: document.getElementById('refreshMetricsBtn'),
    metricCostVal: document.getElementById('metricCostVal'),
    metricTokensInOut: document.getElementById('metricTokensInOut'),
    metricCacheHitRate: document.getElementById('metricCacheHitRate'),
    metricLatencyVal: document.getElementById('metricLatencyVal'),
    metricPrepDetect: document.getElementById('metricPrepDetect'),
    metricLlmRisk: document.getElementById('metricLlmRisk'),
    metricQualityPassRate: document.getElementById('metricQualityPassRate'),
    metricRiskCounts: document.getElementById('metricRiskCounts'),
    metricHumanReviewCount: document.getElementById('metricHumanReviewCount'),

    // Dictionary Section
    dictionaryCard: document.getElementById('dictionaryCard'),
    synonymsChips: document.getElementById('synonymsChips'),
    definitionsList: document.getElementById('definitionsList'),

    // History Drawer
    historyToggleBtn: document.getElementById('historyToggleBtn'),
    historyBadge: document.getElementById('historyBadge'),
    historyDrawer: document.getElementById('historyDrawer'),
    drawerBackdrop: document.getElementById('drawerBackdrop'),
    closeDrawerBtn: document.getElementById('closeDrawerBtn'),
    clearHistoryBtn: document.getElementById('clearHistoryBtn'),
    refreshHistoryBtn: document.getElementById('refreshHistoryBtn'),
    historyTabDb: document.getElementById('historyTabDb'),
    historyTabContext: document.getElementById('historyTabContext'),
    historyList: document.getElementById('historyList'),

    // Toast
    toast: document.getElementById('toast')
  };

  let speechRecognition = null;

  // ==========================================================================
  // Initialization
  // ==========================================================================

  function init() {
    applyTheme(state.theme);
    loadHistory();
    refreshTelemetryMetrics();
    setupSpeechRecognition();
    setupEventListeners();
    updateDirectionUI();
  }

  // ==========================================================================
  // Telemetry Metrics (Nodes Q, R, S)
  // ==========================================================================

  async function refreshTelemetryMetrics() {
    try {
      const res = await fetch('/api/v1/metrics');
      if (!res.ok) return;
      const m = await res.json();

      // Node Q: Cost
      if (elements.metricCostVal) elements.metricCostVal.textContent = `$${m.cumulative_cost_usd.toFixed(6)}`;
      if (elements.metricTokensInOut) elements.metricTokensInOut.textContent = `${m.total_input_tokens} / ${m.total_output_tokens}`;
      if (elements.metricCacheHitRate) elements.metricCacheHitRate.textContent = `${m.cache_hit_rate_pct}%`;

      // Node R: Latency
      if (elements.metricLatencyVal) elements.metricLatencyVal.textContent = `${Math.round(m.rolling_avg_latency_ms)} ms`;

      // Node S: Quality
      if (elements.metricQualityPassRate) elements.metricQualityPassRate.textContent = `${m.quality_pass_rate_pct}%`;
      if (elements.metricRiskCounts) elements.metricRiskCounts.textContent = `${m.low_risk_count} / ${m.high_risk_count}`;
      if (elements.metricHumanReviewCount) elements.metricHumanReviewCount.textContent = `${m.human_review_count}`;
    } catch (e) {
      console.warn('Telemetry refresh failed:', e);
    }
  }

  // ==========================================================================
  // Theme Management
  // ==========================================================================

  function applyTheme(theme) {
    state.theme = theme;
    elements.html.setAttribute('data-theme', theme);
    localStorage.setItem('bilangual_theme', theme);

    if (theme === 'dark') {
      elements.themeIconSun.classList.add('hidden');
      elements.themeIconMoon.classList.remove('hidden');
    } else {
      elements.themeIconSun.classList.remove('hidden');
      elements.themeIconMoon.classList.add('hidden');
    }
  }

  function toggleTheme() {
    applyTheme(state.theme === 'dark' ? 'light' : 'dark');
  }

  // ==========================================================================
  // Translation Direction Management
  // ==========================================================================

  function setTranslationDirection(source, target) {
    if (state.sourceLang === source && state.targetLang === target) return;

    state.sourceLang = source;
    state.targetLang = target;
    updateDirectionUI();
    validateInputScript();
  }

  function swapDirection() {
    const newSource = state.targetLang;
    const newTarget = state.sourceLang;
    const currentInput = elements.sourceInput.value.trim();
    const currentOutput = state.translatedText.trim();

    elements.swapDirectionBtn.classList.add('rotated');
    setTimeout(() => elements.swapDirectionBtn.classList.remove('rotated'), 350);

    state.sourceLang = newSource;
    state.targetLang = newTarget;
    updateDirectionUI();

    if (currentOutput && !currentOutput.includes('error') && !currentOutput.includes('termed')) {
      elements.sourceInput.value = currentOutput;
    } else if (currentInput) {
      elements.sourceInput.value = currentInput;
    }

    validateInputScript();
  }

  function updateDirectionUI() {
    const isEnToUr = state.sourceLang === 'en';

    if (isEnToUr) {
      elements.modeEnToUrBtn.classList.add('active');
      elements.modeEnToUrBtn.setAttribute('aria-selected', 'true');
      elements.modeUrToEnBtn.classList.remove('active');
      elements.modeUrToEnBtn.setAttribute('aria-selected', 'false');

      elements.sourceLangName.textContent = 'English';
      elements.sourceLangName.classList.remove('urdu-font');
      elements.targetLangName.textContent = 'اردو';
      elements.targetLangName.classList.add('urdu-font');

      elements.sourceInput.placeholder = "Type or paste text in English...";
      elements.sourceInput.classList.remove('urdu-mode');
      elements.targetOutput.classList.add('urdu-script');
    } else {
      elements.modeUrToEnBtn.classList.add('active');
      elements.modeUrToEnBtn.setAttribute('aria-selected', 'true');
      elements.modeEnToUrBtn.classList.remove('active');
      elements.modeEnToUrBtn.setAttribute('aria-selected', 'false');

      elements.sourceLangName.textContent = 'اردو';
      elements.sourceLangName.classList.add('urdu-font');
      elements.targetLangName.textContent = 'English';
      elements.targetLangName.classList.remove('urdu-font');

      elements.sourceInput.placeholder = "متن یہاں اردو میں ٹائپ یا پیسٹ کریں...";
      elements.sourceInput.classList.add('urdu-mode');
      elements.targetOutput.classList.remove('urdu-script');
    }
  }

  // ==========================================================================
  // Script Validation
  // ==========================================================================

  function validateInputScript() {
    const text = elements.sourceInput.value.trim();
    if (!text) {
      hideMismatchBanner();
      return true;
    }

    const urduMatches = text.match(URDU_REGEX) || [];
    const englishMatches = text.match(ENGLISH_REGEX) || [];
    const urduCount = urduMatches.length;
    const englishCount = englishMatches.length;
    const totalChars = Math.max(1, text.replace(/\s+/g, '').length);

    if (state.sourceLang === 'en' && urduCount > 2 && (urduCount / totalChars) > 0.3) {
      showMismatchBanner('ur_in_en');
      return false;
    }

    if (state.sourceLang === 'ur' && urduCount === 0 && englishCount > 10) {
      const romanKeywords = ['hai', 'hain', 'tha', 'thi', 'the', 'kya', 'kiya', 'gaya', 'gayi', 'gaye',
        'nahi', 'nahin', 'aur', 'par', 'pe', 'mein', 'me', 'se', 'mera', 'meri',
        'mere', 'mujhe', 'hum', 'humein', 'bhai', 'bhaiya', 'kal', 'aj', 'aaj',
        'kat', 'cut', 'pese', 'paise', 'karo', 'karein', 'apke', 'aapke', 'hua', 'hui'];
      const words = text.toLowerCase().split(/\W+/);
      const isRomanUrdu = words.some(w => romanKeywords.includes(w));

      if (!isRomanUrdu) {
        showMismatchBanner('en_in_ur');
        return false;
      }
    }

    hideMismatchBanner();
    return true;
  }

  function showMismatchBanner(type) {
    state.mismatchDetected = true;
    state.mismatchType = type;

    if (type === 'ur_in_en') {
      elements.mismatchMessage.innerHTML = 'You are in <strong>English → Urdu</strong> mode, but entered text in Urdu script (اردو).';
      elements.autoSwitchBtnText.textContent = 'Switch to Urdu → English & Translate';
    } else {
      elements.mismatchMessage.innerHTML = 'You are in <strong>Urdu → English</strong> mode, but entered text in English.';
      elements.autoSwitchBtnText.textContent = 'Switch to English → Urdu & Translate';
    }

    elements.mismatchBanner.classList.remove('hidden');
    elements.manualTranslateBtn.disabled = true;
    elements.manualTranslateBtn.style.opacity = '0.5';
  }

  function hideMismatchBanner() {
    state.mismatchDetected = false;
    state.mismatchType = null;
    elements.mismatchBanner.classList.add('hidden');
    elements.manualTranslateBtn.disabled = false;
    elements.manualTranslateBtn.style.opacity = '1';
  }

  function resolveMismatchAutoSwitch() {
    if (state.mismatchType === 'ur_in_en') {
      setTranslationDirection('ur', 'en');
    } else if (state.mismatchType === 'en_in_ur') {
      setTranslationDirection('en', 'ur');
    }
    executeTranslation();
  }

  // ==========================================================================
  // Translation Core & Flowchart Step Highlighting
  // ==========================================================================

  function handleInputChange() {
    const text = elements.sourceInput.value;
    state.inputText = text;

    elements.charCount.textContent = `${text.length.toLocaleString()} / 5,000`;

    if (text.length > 0) {
      elements.clearInputBtn.classList.remove('hidden');
    } else {
      elements.clearInputBtn.classList.add('hidden');
      clearOutput();
      hideMismatchBanner();
      return;
    }

    validateInputScript();
  }

  function highlightFlowchart(step) {
    const steps = [elements.stepA, elements.stepB, elements.stepC, elements.stepE, elements.stepF, elements.stepJ, elements.stepK, elements.stepBranch, elements.stepP];
    steps.forEach(s => s && s.classList && s.classList.remove('active'));

    if (step && elements[step] && elements[step].classList) {
      elements[step].classList.add('active');
    }
  }

  async function executeTranslation() {
    const text = elements.sourceInput.value.trim();
    if (!text) {
      clearOutput();
      return;
    }

    if (!validateInputScript()) return;

    setLoading(true);
    highlightFlowchart('stepA');

    try {
      highlightFlowchart('stepB');

      const payload = {
        text: text,
        source_lang: state.sourceLang,
        target_lang: state.targetLang,
        session_id: state.sessionId
      };

      const res = await fetch('/api/v1/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();
      renderTranslationResult(data);

      saveToHistory({
        sourceText: text,
        targetText: data.translation,
        sourceLang: state.sourceLang,
        targetLang: state.targetLang,
        timestamp: Date.now()
      });

    } catch (err) {
      console.error('Translation error:', err);
      elements.targetOutput.textContent = err.message || 'Translation unavailable. Please check connection.';
      elements.targetOutput.classList.remove('empty');
      elements.targetStatusText.textContent = 'Error';
    } finally {
      setLoading(false);
      refreshTelemetryMetrics();
    }
  }

  function renderTranslationResult(data) {
    state.translatedText = data.translation || '';
    state.pronunciation = data.pronunciation || '';
    state.riskLevel = data.risk_level || 'LOW_RISK_APPROVED';
    state.riskDetails = data.risk_details || '';
    state.needsHumanReview = Boolean(data.needs_human_review);

    elements.targetOutput.textContent = state.translatedText;
    elements.targetOutput.classList.remove('empty');
    elements.targetStatusText.textContent = 'Translated';

    // Confidence Score Display
    const confVal = (data.confidence_score !== undefined && data.confidence_score !== null)
      ? data.confidence_score
      : (data.confidence !== undefined ? data.confidence : 1.0);
    if (elements.confidenceBadge) {
      elements.confidenceBadge.textContent = `Score: ${(confVal * 100).toFixed(1)}%`;
      elements.confidenceBadge.title = `Model Output Confidence: ${(confVal * 100).toFixed(1)}%`;
    }

    // Pronunciation
    if (state.pronunciation && state.pronunciation.trim()) {
      elements.pronunciationText.textContent = state.pronunciation;
      elements.pronunciationWrap.classList.remove('hidden');
    } else {
      elements.pronunciationWrap.classList.add('hidden');
    }

    // Latency
    if (data.processing_time_ms && elements.latencyBadge) {
      elements.latencyBadge.textContent = `⚡ ${Math.round(data.processing_time_ms)}ms`;
      elements.latencyBadge.classList.remove('hidden');
    }

    // Telemetry Breakdown
    if (data.latency_breakdown) {
      if (elements.metricPrepDetect) elements.metricPrepDetect.textContent = `${data.latency_breakdown.preprocessing_ms}ms / ${data.latency_breakdown.detection_ms}ms`;
      if (elements.metricLlmRisk) elements.metricLlmRisk.textContent = `${data.latency_breakdown.llm_ms}ms / ${data.latency_breakdown.risk_eval_ms}ms`;
    }

    // Risk / Quality Status
    if (state.needsHumanReview) {
      if (elements.riskStatusBadge) {
        elements.riskStatusBadge.className = 'risk-badge badge-flagged';
        elements.riskBadgeText.textContent = '⚠️ Review Needed';
      }

      if (elements.branchLabel) elements.branchLabel.textContent = 'Review Needed';
      if (elements.stepBranch && elements.stepBranch.classList) elements.stepBranch.className = 'flow-step step-branch active high-risk';

      // Show Human-in-the-Loop Review Box
      elements.hitlReasonText.textContent = state.riskDetails || 'Flagged by verification engine: Mismatch detected.';
      elements.hitlEditText.value = state.translatedText;
      elements.hitlNotesInput.value = '';
      elements.hitlReviewBox.classList.remove('hidden');

      showToast('⚠️ Review Needed');
    } else {
      if (elements.riskStatusBadge) {
        elements.riskStatusBadge.className = 'risk-badge badge-approved';
        elements.riskBadgeText.textContent = '✓ Verified';
      }

      if (elements.branchLabel) elements.branchLabel.textContent = 'Verified';
      if (elements.stepBranch && elements.stepBranch.classList) elements.stepBranch.className = 'flow-step step-branch active low-risk';

      elements.hitlReviewBox.classList.add('hidden');
    }

    // Dynamic CRAWL, WALK, RUN Risk Framework Badges
    const cwr = data.crawl_walk_run;
    if (cwr) {
      if (elements.cwrCrawlBadge) {
        if (cwr.crawl && cwr.crawl.passed) {
          elements.cwrCrawlBadge.className = 'cwr-badge badge-pass';
          elements.cwrCrawlBadge.textContent = 'CRAWL: ✓';
          elements.cwrCrawlBadge.title = 'CRAWL: Deterministic checks passed (0 flags)';
        } else {
          elements.cwrCrawlBadge.className = 'cwr-badge badge-warn';
          elements.cwrCrawlBadge.textContent = 'CRAWL: ⚠️';
          elements.cwrCrawlBadge.title = 'CRAWL: Deterministic rule flag triggered';
        }
      }

      if (elements.cwrWalkBadge) {
        if (cwr.walk && cwr.walk.human_review_required) {
          elements.cwrWalkBadge.className = 'cwr-badge badge-warn';
          elements.cwrWalkBadge.textContent = 'WALK: Review';
          elements.cwrWalkBadge.title = 'WALK: Escalated to human operator (Node N)';
        } else {
          elements.cwrWalkBadge.className = 'cwr-badge badge-pass';
          elements.cwrWalkBadge.textContent = 'WALK: Auto';
          elements.cwrWalkBadge.title = 'WALK: Auto-approved release';
        }
      }

      if (elements.cwrRunBadge) {
        elements.cwrRunBadge.className = 'cwr-badge badge-info';
        elements.cwrRunBadge.textContent = 'RUN: ⚡';
        elements.cwrRunBadge.title = `RUN: Production telemetry active ($${cwr.run ? cwr.run.cost_usd.toFixed(5) : '0'})`;
      }

      // Visualizer Progression Strip
      if (elements.cwrPillCrawl) elements.cwrPillCrawl.classList.add('active');
      if (elements.cwrPillWalk) elements.cwrPillWalk.classList.toggle('active', Boolean(cwr.walk && cwr.walk.human_review_required));
      if (elements.cwrPillRun) elements.cwrPillRun.classList.add('active');
    }

    highlightFlowchart('stepP');

    renderDictionary(data.synonyms || [], data.definitions || []);
  }

  // ==========================================================================
  // Node N: Human-in-the-Loop Review Handlers
  // ==========================================================================

  async function submitHumanReviewAction(action) {
    const originalText = elements.sourceInput.value.trim();
    const aiTranslation = state.translatedText;
    let finalTranslation = aiTranslation;

    if (action === 'correct') {
      finalTranslation = elements.hitlEditText.value.trim();
      if (!finalTranslation) {
        showToast('Please enter corrected translation text');
        return;
      }
    } else if (action === 'reject') {
      finalTranslation = `[REJECTED & ESCALATED TO FRAUD/COMPLIANCE] Original complaint: "${originalText}"`;
    }

    try {
      const payload = {
        session_id: state.sessionId,
        original_text: originalText,
        ai_translation: aiTranslation,
        action: action,
        final_translation: finalTranslation,
        risk_level: state.riskLevel,
        reviewer_notes: elements.hitlNotesInput.value.trim()
      };

      const res = await fetch('/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error('Human review feedback submission failed');

      const data = await res.json();

      // Node N -> Node M -> Node P
      state.translatedText = finalTranslation;
      elements.targetOutput.textContent = finalTranslation;
      elements.hitlReviewBox.classList.add('hidden');

      elements.riskStatusBadge.className = 'risk-badge badge-approved';
      elements.riskBadgeText.textContent = `✓ Human Reviewed (${action.toUpperCase()})`;

      elements.branchLabel.textContent = 'Approved by Human (Node M)';
      elements.stepBranch.className = 'flow-step step-branch active low-risk';

      showToast(`Feedback action '${action.toUpperCase()}' stored in SQLite & Evaluation Dataset`);
      refreshTelemetryMetrics();
    } catch (err) {
      console.error(err);
      showToast('Error saving human review');
    }
  }

  function renderDictionary(synonyms, definitions) {
    if ((synonyms && synonyms.length > 0) || (definitions && definitions.length > 0)) {
      elements.synonymsChips.innerHTML = '';
      synonyms.forEach(syn => {
        const chip = document.createElement('span');
        chip.className = 'synonym-chip';
        chip.textContent = syn;
        chip.title = 'Click to use this phrasing';
        chip.onclick = () => {
          elements.targetOutput.textContent = syn;
          state.translatedText = syn;
          showToast(`Selected "${syn}"`);
        };
        elements.synonymsChips.appendChild(chip);
      });

      elements.definitionsList.innerHTML = '';
      definitions.forEach(def => {
        const item = document.createElement('div');
        item.textContent = `• ${def}`;
        elements.definitionsList.appendChild(item);
      });

      elements.dictionaryCard.classList.remove('hidden');
    } else {
      elements.dictionaryCard.classList.add('hidden');
    }
  }

  function setLoading(isLoading) {
    state.isTranslating = isLoading;
    if (isLoading) {
      elements.targetLoading.classList.remove('hidden');
      elements.targetOutput.style.opacity = '0.3';
      elements.targetStatusText.textContent = 'Translating...';
    } else {
      elements.targetLoading.classList.add('hidden');
      elements.targetOutput.style.opacity = '1';
    }
  }

  function clearOutput() {
    const isEnToUr = state.sourceLang === 'en';
    elements.targetOutput.innerHTML = `<span class="placeholder-text">${isEnToUr ? 'ترجمہ (Translation)' : 'Translation'}</span>`;
    elements.targetOutput.classList.add('empty');
    elements.pronunciationWrap.classList.add('hidden');
    elements.dictionaryCard.classList.add('hidden');
    elements.latencyBadge.classList.add('hidden');
    elements.hitlReviewBox.classList.add('hidden');
    elements.targetStatusText.textContent = 'Ready';
    state.translatedText = '';
    state.pronunciation = '';
  }

  function clearInput() {
    elements.sourceInput.value = '';
    handleInputChange();
    elements.sourceInput.focus();
  }

  // ==========================================================================
  // Speech Recognition (Voice Input)
  // ==========================================================================

  function setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      elements.micBtn.title = 'Voice input not supported in this browser';
      elements.micBtn.style.opacity = '0.5';
      return;
    }

    speechRecognition = new SpeechRecognition();
    speechRecognition.continuous = false;
    speechRecognition.interimResults = true;

    speechRecognition.onstart = () => {
      state.isListening = true;
      elements.micBtn.classList.add('listening');
      showToast('Listening... Speak now');
    };

    speechRecognition.onresult = (event) => {
      let transcript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      elements.sourceInput.value = transcript;
      handleInputChange();
    };

    speechRecognition.onerror = (event) => {
      console.warn('Speech error:', event.error);
      stopListening();
    };

    speechRecognition.onend = () => {
      stopListening();
      if (elements.sourceInput.value.trim() && !state.mismatchDetected) {
        executeTranslation();
      }
    };
  }

  function toggleVoiceInput() {
    if (!speechRecognition) {
      showToast('Voice input is not supported in this browser');
      return;
    }

    if (state.isListening) {
      speechRecognition.stop();
      stopListening();
    } else {
      speechRecognition.lang = state.sourceLang === 'en' ? 'en-US' : 'ur-PK';
      try {
        speechRecognition.start();
      } catch (e) {
        console.warn(e);
      }
    }
  }

  function stopListening() {
    state.isListening = false;
    elements.micBtn.classList.remove('listening');
  }



  // ==========================================================================
  // Clipboard Copy & Star
  // ==========================================================================

  function copyTranslation() {
    if (!state.translatedText) return;
    navigator.clipboard.writeText(state.translatedText).then(() => {
      showToast('Translation copied to clipboard');
    }).catch(() => {
      const temp = document.createElement('textarea');
      temp.value = state.translatedText;
      document.body.appendChild(temp);
      temp.select();
      document.execCommand('copy');
      document.body.removeChild(temp);
      showToast('Translation copied to clipboard');
    });
  }

  function toggleStar() {
    if (!state.translatedText) return;
    elements.starBtn.classList.toggle('active');
    const isStarred = elements.starBtn.classList.contains('active');
    showToast(isStarred ? 'Saved to starred' : 'Removed from starred');
  }

  // ==========================================================================
  // History Drawer
  // ==========================================================================

  // ==========================================================================
  // History & SQLite Usage Logs Drawer
  // ==========================================================================

  let currentHistoryTab = 'db'; // 'db' or 'context'

  async function loadHistory() {
    await refreshHistoryList();
  }

  function saveToHistory(item) {
    if (!item.sourceText || !item.targetText) return;

    state.history = state.history.filter(h => h.sourceText !== item.sourceText);
    state.history.unshift(item);
    if (state.history.length > 25) {
      state.history = state.history.slice(0, 25);
    }
    localStorage.setItem('bilangual_history', JSON.stringify(state.history));
    updateHistoryBadge();
  }

  function updateHistoryBadge() {
    if (elements.historyBadge) {
      elements.historyBadge.textContent = state.history.length;
    }
  }

  function openHistoryDrawer() {
    refreshHistoryList();
    elements.historyDrawer.classList.add('open');
    elements.drawerBackdrop.classList.add('active');
  }

  function closeHistoryDrawer() {
    elements.historyDrawer.classList.remove('open');
    elements.drawerBackdrop.classList.remove('active');
  }

  function clearHistory() {
    state.history = [];
    localStorage.removeItem('bilangual_history');
    updateHistoryBadge();
    renderHistoryList([]);
    showToast('Local history cleared');
  }

  async function refreshHistoryList() {
    if (currentHistoryTab === 'db') {
      await fetchHistoryFromDb();
    } else {
      await fetchSessionContext();
    }
  }

  async function fetchHistoryFromDb() {
    elements.historyList.innerHTML = `
      <div class="empty-history">
        <p>Loading SQLite Usage Logs...</p>
      </div>
    `;

    try {
      const res = await fetch('/api/v1/history?limit=50');
      if (!res.ok) throw new Error('Failed to fetch history');
      const logs = await res.json();
      
      if (elements.historyBadge) {
        elements.historyBadge.textContent = logs.length;
      }
      
      renderDbLogsList(logs);
    } catch (err) {
      console.warn('Failed to load SQLite history logs:', err);
      renderHistoryList(state.history);
    }
  }

  async function fetchSessionContext() {
    elements.historyList.innerHTML = `
      <div class="empty-history">
        <p>Loading Session Context...</p>
      </div>
    `;

    try {
      const res = await fetch(`/api/v1/context/${state.sessionId}`);
      if (!res.ok) throw new Error('Failed to fetch context');
      const ctx = await res.json();
      renderContextList(ctx.messages || []);
    } catch (err) {
      console.warn('Failed to load context:', err);
      elements.historyList.innerHTML = `
        <div class="empty-history">
          <p>No active session context turns.</p>
        </div>
      `;
    }
  }

  function renderDbLogsList(logs) {
    elements.historyList.innerHTML = '';
    if (!logs || logs.length === 0) {
      elements.historyList.innerHTML = `
        <div class="empty-history">
          <p>No SQLite usage logs recorded yet.</p>
          <span>Logs from every API request will appear here.</span>
        </div>
      `;
      return;
    }

    logs.forEach(log => {
      const isLowRisk = (log.final_risk_status === 'LOW_RISK_APPROVED');
      const confScore = log.confidence_score !== undefined ? (log.confidence_score * 100).toFixed(1) + '%' : 'N/A';
      const timeMs = log.processing_time_ms ? `${Math.round(log.processing_time_ms)}ms` : '';
      const scriptBadge = (log.detected_script || 'EN').toUpperCase();
      const dateStr = log.created_at ? new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

      const el = document.createElement('div');
      el.className = 'history-item';
      el.innerHTML = `
        <div class="history-item-header">
          <span class="history-item-langs">${scriptBadge}</span>
          <span class="history-badge-small ${isLowRisk ? 'history-badge-approved' : 'history-badge-flagged'}">
            ${isLowRisk ? '✓ Verified' : '⚠️ Flagged'} (${confScore})
          </span>
        </div>
        <div class="history-item-source">${escapeHtml(log.source_text)}</div>
        <div class="history-item-target">${escapeHtml(log.target_text)}</div>
        <div class="history-item-footer">
          <span>Sess: ${escapeHtml(log.session_id || 'default')}</span>
          <span>${timeMs} • ${dateStr}</span>
        </div>
      `;

      el.addEventListener('click', () => {
        elements.sourceInput.value = log.source_text;
        elements.targetOutput.textContent = log.target_text;
        elements.targetOutput.classList.remove('empty');
        state.translatedText = log.target_text;
        handleInputChange();
        closeHistoryDrawer();
        showToast('Loaded recorded log into workbench');
      });

      elements.historyList.appendChild(el);
    });
  }

  function renderContextList(messages) {
    elements.historyList.innerHTML = '';
    if (!messages || messages.length === 0) {
      elements.historyList.innerHTML = `
        <div class="empty-history">
          <p>Session context is empty.</p>
          <span>Multi-turn chat context will appear here as you translate.</span>
        </div>
      `;
      return;
    }

    messages.forEach((msg, idx) => {
      const el = document.createElement('div');
      el.className = 'history-item';
      const isUser = msg.role === 'user';
      el.innerHTML = `
        <div class="history-item-header">
          <span class="history-item-langs">${isUser ? '👤 USER INPUT' : '🤖 ASSISTANT TICKET'}</span>
          <span class="history-item-time">Turn #${Math.floor(idx / 2) + 1}</span>
        </div>
        <div class="history-item-source">${escapeHtml(msg.content)}</div>
      `;
      elements.historyList.appendChild(el);
    });
  }

  function renderHistoryList(items) {
    renderDbLogsList(items || []);
  }

  // ==========================================================================
  // Toast Helper
  // ==========================================================================

  let toastTimer = null;
  function showToast(message) {
    clearTimeout(toastTimer);
    elements.toast.textContent = message;
    elements.toast.classList.add('show');
    toastTimer = setTimeout(() => {
      elements.toast.classList.remove('show');
    }, 2400);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag));
  }

  // ==========================================================================
  // Event Listeners
  // ==========================================================================

  function setupEventListeners() {
    // Theme toggle
    if (elements.themeToggleBtn) elements.themeToggleBtn.addEventListener('click', toggleTheme);

    // Architecture visualizer toggle
    if (elements.toggleArchBtn && elements.archVisualizer) {
      elements.toggleArchBtn.addEventListener('click', () => {
        state.archVisualizerOpen = !state.archVisualizerOpen;
        elements.archVisualizer.classList.toggle('hidden', !state.archVisualizerOpen);
      });
    }

    // Direction switches
    if (elements.modeEnToUrBtn) elements.modeEnToUrBtn.addEventListener('click', () => setTranslationDirection('en', 'ur'));
    if (elements.modeUrToEnBtn) elements.modeUrToEnBtn.addEventListener('click', () => setTranslationDirection('ur', 'en'));
    if (elements.swapDirectionBtn) elements.swapDirectionBtn.addEventListener('click', swapDirection);
    if (elements.autoSwitchActionBtn) elements.autoSwitchActionBtn.addEventListener('click', resolveMismatchAutoSwitch);

    // Input actions
    if (elements.sourceInput) elements.sourceInput.addEventListener('input', handleInputChange);
    if (elements.clearInputBtn) elements.clearInputBtn.addEventListener('click', clearInput);
    if (elements.manualTranslateBtn) elements.manualTranslateBtn.addEventListener('click', executeTranslation);

    // Node N: Human-in-the-Loop Action Buttons
    if (elements.hitlAcceptBtn) elements.hitlAcceptBtn.addEventListener('click', () => submitHumanReviewAction('accept'));
    if (elements.hitlCorrectBtn) elements.hitlCorrectBtn.addEventListener('click', () => submitHumanReviewAction('correct'));
    if (elements.hitlRejectBtn) elements.hitlRejectBtn.addEventListener('click', () => submitHumanReviewAction('reject'));

    // Telemetry refresh button
    if (elements.refreshMetricsBtn) elements.refreshMetricsBtn.addEventListener('click', refreshTelemetryMetrics);

    // Microphone & Audio
    if (elements.micBtn) elements.micBtn.addEventListener('click', toggleVoiceInput);

    // Clipboard & Star
    if (elements.copyBtn) elements.copyBtn.addEventListener('click', copyTranslation);
    if (elements.starBtn) elements.starBtn.addEventListener('click', toggleStar);

    // History Drawer & Tab Switching
    if (elements.historyToggleBtn) elements.historyToggleBtn.addEventListener('click', openHistoryDrawer);
    if (elements.closeDrawerBtn) elements.closeDrawerBtn.addEventListener('click', closeHistoryDrawer);
    if (elements.drawerBackdrop) elements.drawerBackdrop.addEventListener('click', closeHistoryDrawer);
    if (elements.clearHistoryBtn) elements.clearHistoryBtn.addEventListener('click', clearHistory);
    if (elements.refreshHistoryBtn) elements.refreshHistoryBtn.addEventListener('click', refreshHistoryList);

    if (elements.historyTabDb) {
      elements.historyTabDb.addEventListener('click', () => {
        currentHistoryTab = 'db';
        elements.historyTabDb.classList.add('active');
        elements.historyTabDb.setAttribute('aria-selected', 'true');
        if (elements.historyTabContext) {
          elements.historyTabContext.classList.remove('active');
          elements.historyTabContext.setAttribute('aria-selected', 'false');
        }
        fetchHistoryFromDb();
      });
    }

    if (elements.historyTabContext) {
      elements.historyTabContext.addEventListener('click', () => {
        currentHistoryTab = 'context';
        elements.historyTabContext.classList.add('active');
        elements.historyTabContext.setAttribute('aria-selected', 'true');
        if (elements.historyTabDb) {
          elements.historyTabDb.classList.remove('active');
          elements.historyTabDb.setAttribute('aria-selected', 'false');
        }
        fetchSessionContext();
      });
    }

    // Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        executeTranslation();
      }
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'S' || e.key === 's')) {
        e.preventDefault();
        swapDirection();
      }
      if (e.key === 'Escape') {
        closeHistoryDrawer();
        if (state.archVisualizerOpen && elements.archVisualizer) {
          state.archVisualizerOpen = false;
          elements.archVisualizer.classList.add('hidden');
        }
      }
    });
  }

  // Self-start
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
