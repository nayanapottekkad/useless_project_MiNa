/**
 * THE UNNECESSARY FM — Spotify-Inspired Modern Audio Studio
 * Procedural Music Generation Logic
 * Team MiNa • Midhun K M & Nayana P • TinkerHub Useless Projects 3.0
 */

(() => {
  // API URL Configuration:
  // 1. Checks window.ENV.BACKEND_URL (injected from ENV variable BACKEND_URL via /env.js)
  // 2. Checks window.BACKEND_URL or window.API_BASE_URL
  // 3. Checks <meta name="backend-url"> or <meta name="api-base-url">
  // 4. Checks URL query param (?backend=... or ?api=...)
  // 5. Checks localStorage('BACKEND_URL' or 'API_BASE_URL')
  // If not set, defaults to "" (current origin / relative path).
  const getApiBaseUrl = () => {
    try {
      if (typeof window !== 'undefined' && window.ENV && window.ENV.BACKEND_URL) {
        return window.ENV.BACKEND_URL.trim().replace(/\/+$/, '');
      }
      if (typeof window !== 'undefined' && (window.BACKEND_URL || window.API_BASE_URL)) {
        return (window.BACKEND_URL || window.API_BASE_URL).trim().replace(/\/+$/, '');
      }
      const meta = document.querySelector('meta[name="backend-url"], meta[name="api-base-url"]');
      if (meta && meta.content && meta.content.trim()) {
        return meta.content.trim().replace(/\/+$/, '');
      }
      const urlParams = new URLSearchParams(window.location.search);
      const queryApi = urlParams.get('backend') || urlParams.get('api');
      if (queryApi) return queryApi.trim().replace(/\/+$/, '');
      const stored = localStorage.getItem('BACKEND_URL') || localStorage.getItem('API_BASE_URL');
      if (stored && stored.trim()) return stored.trim().replace(/\/+$/, '');
    } catch (e) {}
    return '';
  };

  const API_BASE = getApiBaseUrl();
  const buildUrl = (path) => {
    if (!path) return '';
    if (path.startsWith('http://') || path.startsWith('https://')) return path;
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return API_BASE ? `${API_BASE}${cleanPath}` : cleanPath;
  };

  // DOM Elements - Source & Input
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('audioFileInput');
  const dropZoneContent = document.getElementById('dropZoneContent');
  const selectedFilePill = document.getElementById('selectedFilePill');
  const selectedFileName = document.getElementById('selectedFileName');
  const selectedFileSize = document.getElementById('selectedFileSize');
  const btnRemoveFile = document.getElementById('btnRemoveFile');

  // Microphone Recording Elements
  const btnRecord = document.getElementById('btnRecord');
  const recordBtnText = document.getElementById('recordBtnText');
  const recTimer = document.getElementById('recTimer');
  const recTimeDisplay = document.getElementById('recTimeDisplay');
  const liveMicCanvas = document.getElementById('liveMicCanvas');

  // Composition Directives Elements
  const beatSelect = document.getElementById('beatSelect');
  const styleSelect = document.getElementById('styleSelect');
  const styleCountHint = document.getElementById('styleCountHint');
  const energySelect = document.getElementById('energySelect');
  const seedInput = document.getElementById('seedInput');
  const btnRandomizeSeed = document.getElementById('btnRandomizeSeed');
  const btnGenerate = document.getElementById('btnGenerate');
  const btnRerollArtist = document.getElementById('btnRerollArtist');
  const bottomPlayerReroll = document.getElementById('bottomPlayerReroll');

  // Vocal Extraction Mode Elements
  const vocalModeSelect = document.getElementById('vocalModeSelect');
  const vocalHelperNote = document.getElementById('vocalHelperNote');

  let allAvailableStyles = [];

  async function loadAvailableStyles() {
    try {
      const res = await fetch(buildUrl('/api/styles'));
      if (!res.ok) return;
      const data = await res.json();
      allAvailableStyles = data.styles || [];
      populateStyleDropdown();
    } catch (err) {
      console.warn('Failed to load styles metadata', err);
    }
  }

  function populateStyleDropdown() {
    if (!styleSelect) return;
    const currentVal = styleSelect.value;
    const selectedGenre = (beatSelect ? beatSelect.value : 'pop').toLowerCase();
    let targetGenre = selectedGenre;
    if (targetGenre === 'light_percussion') targetGenre = 'rhythmic';

    // Preserve auto option
    styleSelect.innerHTML = '<option value="" selected>🎲 Auto-Cycle (Surprise Me / Non-Repeating)</option>';

    if (!allAvailableStyles || allAvailableStyles.length === 0) return;

    // Filter styles strictly for current selected genre
    const currentGenreStyles = allAvailableStyles.filter(s => s.genre === targetGenre);

    // Extract clean genre display label
    let genreClean = 'Pop';
    if (beatSelect && beatSelect.selectedOptions && beatSelect.selectedOptions[0]) {
      const fullText = beatSelect.selectedOptions[0].textContent;
      genreClean = fullText.replace(/^[\p{Emoji}\s✨🥁🎺🎸🎷🎹⚡🪐🔥🎧🧩🌌🎵]+/gu, '').split('(')[0].trim() || targetGenre.toUpperCase();
    }

    if (styleCountHint) {
      const activeText = (!styleSelect.value) ? 'Auto-Cycle active' : 'Switch anytime';
      styleCountHint.textContent = `(${currentGenreStyles.length} ${genreClean} Styles • ${activeText})`;
    }

    if (currentGenreStyles.length > 0) {
      currentGenreStyles.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.id;
        const isDefaultTag = (targetGenre === 'pop' && s.id === 'ladygaga_redone_electro') ? ' [Plays 1st on Auto-Cycle]' : '';
        opt.textContent = `${s.display_name} (${s.bpm_default} BPM)${isDefaultTag}`;
        styleSelect.appendChild(opt);
      });
    }

    // Default to Auto-Cycle by rule; keep user selection if explicitly made
    if (currentVal && Array.from(styleSelect.options).some(o => o.value === currentVal)) {
      styleSelect.value = currentVal;
    } else {
      styleSelect.value = '';
    }

    updateStyleHelperNote();
  }

  function updateStyleHelperNote() {
    if (!styleSelect) return;
    const currentVal = styleSelect.value;
    const noteEl = document.getElementById('styleHelperNote');
    const nudgeEl = document.getElementById('styleExploreNudge');
    const countHint = document.getElementById('styleCountHint');

    let genreClean = 'Pop';
    const targetGenre = (beatSelect ? beatSelect.value : 'pop').toLowerCase();
    if (beatSelect && beatSelect.selectedOptions && beatSelect.selectedOptions[0]) {
      const fullText = beatSelect.selectedOptions[0].textContent;
      genreClean = fullText.replace(/^[\p{Emoji}\s✨🥁🎺🎸🎷🎹⚡🪐🔥🎧🧩🌌🎵]+/gu, '').split('(')[0].trim() || 'Genre';
    }

    if (countHint && countHint.textContent.includes('Styles')) {
      const currentGenreStyles = allAvailableStyles.filter(s => s.genre === targetGenre);
      const activeText = (!currentVal) ? 'Auto-Cycle active' : 'Switch anytime';
      countHint.textContent = `(${currentGenreStyles.length} ${genreClean} Styles • ${activeText})`;
    }

    if (noteEl) {
      if (!currentVal) {
        if (targetGenre === 'pop') {
          noteEl.textContent = `🎲 Auto-Cycle: Always plays Electro-Pop Supersaw first, then randomizes unplayed styles — switch anytime!`;
        } else {
          noteEl.textContent = `🎲 Auto-cycles unplayed ${genreClean} styles on each roll — switch to any archetype anytime!`;
        }
      } else {
        const selectedOpt = styleSelect.options[styleSelect.selectedIndex];
        const optLabel = selectedOpt ? selectedOpt.textContent.replace(/\s*\[Plays 1st on Auto-Cycle\]|\s*\[Default\]\s*/g, '').trim() : '';
        noteEl.textContent = `🎛️ Active Archetype: ${optLabel} — you can freely switch styles or choose Auto-Cycle!`;
      }
    }

    if (nudgeEl) {
      if (!currentVal) {
        nudgeEl.textContent = `🔀 Auto-Cycle active! Or choose any specific archetype below to switch sounds & tempos.`;
      } else {
        nudgeEl.textContent = `🔀 Feel free to switch archetypes anytime — explore different sounds, tempos & vibes!`;
      }
    }
  }

  if (styleSelect) {
    styleSelect.addEventListener('change', () => {
      const chosenId = styleSelect.value;
      if (chosenId) {
        const match = allAvailableStyles.find(s => s.id === chosenId);
        if (match && beatSelect && beatSelect.value !== match.genre) {
          beatSelect.value = match.genre;
        }
      }
      updateStyleHelperNote();
    });
  }

  if (beatSelect) {
    beatSelect.addEventListener('change', () => {
      populateStyleDropdown();
    });
  }

  function triggerStyleRoll() {
    if (!currentJobId && !currentFile) {
      showToast('Please upload or record audio first!', 'info', 'NO AUDIO');
      return;
    }
    // Set style selector back to auto-cycle so it rolls an unplayed style!
    if (styleSelect) {
      styleSelect.value = '';
    }
    showToast('Rolling next sound style...', 'info', 'STYLE ROLL');
    submitMusicGeneration();
  }

  if (btnRerollArtist) {
    btnRerollArtist.addEventListener('click', triggerStyleRoll);
  }
  if (bottomPlayerReroll) {
    bottomPlayerReroll.addEventListener('click', triggerStyleRoll);
  }

  // Load styles immediately on page init
  loadAvailableStyles();

  // ── EXPLORE TIP BANNER: rotating hints + dismiss for new users ──────────────
  (function initExploreTipBanner() {
    const banner = document.getElementById('exploreTipBanner');
    const tipText = document.getElementById('exploreTipText');
    const dismissBtn = document.getElementById('exploreTipDismiss');
    if (!banner) return;

    // Skip if user already dismissed this session
    if (sessionStorage.getItem('exploreTipDismissed')) {
      banner.classList.add('dismissed');
      return;
    }

    const tips = [
      "You're not stuck on one style! Switch genres, pick any archetype, or let Auto-Cycle surprise you — every run sounds completely different.",
      "Try all 8 genres: Pop, Rap/Electro, Hip Hop, Trap, Minimal, Rhythmic, Light Percussion, and Ambient — the same noise becomes a new song each time!",
      "🎲 Auto-Cycle picks an unplayed style on every run, so just keep hitting Create and explore the full palette!",
      "Each genre has multiple sound archetypes (e.g. Boom-Bap, Crunk Club, Nu-Disco, Supersaw). Pick one from the dropdown or let Auto-Cycle tour them all.",
      "Hit Create with the same recording but a different genre — you'll be surprised how wild the transformation changes!",
      "Tip: change Energy & Pace to 'High Dynamics' for festival-ready bangers, or 'Subtle & Ambient' for chilled vibes.",
    ];

    let tipIdx = 0;
    let tipTimer = null;

    function rotateTip() {
      if (!tipText || banner.classList.contains('dismissed')) return;
      tipText.classList.add('fading');
      setTimeout(() => {
        tipIdx = (tipIdx + 1) % tips.length;
        tipText.textContent = tips[tipIdx];
        tipText.classList.remove('fading');
      }, 260);
    }

    tipTimer = setInterval(rotateTip, 5000);

    function dismissBanner() {
      banner.classList.add('dismissed');
      sessionStorage.setItem('exploreTipDismissed', '1');
      if (tipTimer) clearInterval(tipTimer);
    }

    if (dismissBtn) dismissBtn.addEventListener('click', dismissBanner);

    // Auto-dismiss banner once user starts interacting with the studio controls
    const autoHideTargets = ['beatSelect', 'styleSelect', 'energySelect', 'btnGenerate', 'btnRecord', 'dropZone'];
    autoHideTargets.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('click', dismissBanner, { once: true });
    });
  })();
  // ────────────────────────────────────────────────────────────────────────────


  // Sound Guide Tooltip Toggle (supports mobile tap & keyboard Escape)
  const soundGuideInfoBtn = document.getElementById('soundGuideInfoBtn');
  const soundGuideTooltipWrap = document.getElementById('soundGuideTooltipWrap');
  if (soundGuideInfoBtn && soundGuideTooltipWrap) {
    soundGuideInfoBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      soundGuideTooltipWrap.classList.toggle('active');
    });
    document.addEventListener('click', (e) => {
      if (!soundGuideTooltipWrap.contains(e.target)) {
        soundGuideTooltipWrap.classList.remove('active');
      }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        soundGuideTooltipWrap.classList.remove('active');
      }
    });
  }

  // Sound Style Archetype Info Tooltip Toggle (supports tap & keyboard Escape)
  const styleInfoBtn = document.getElementById('styleInfoBtn');
  const styleInfoTooltipWrap = document.getElementById('styleInfoTooltipWrap');
  if (styleInfoBtn && styleInfoTooltipWrap) {
    styleInfoBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      styleInfoTooltipWrap.classList.toggle('active');
    });
    document.addEventListener('click', (e) => {
      if (!styleInfoTooltipWrap.contains(e.target)) {
        styleInfoTooltipWrap.classList.remove('active');
      }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        styleInfoTooltipWrap.classList.remove('active');
      }
    });
  }

  // Dynamic Energy Info Tooltip Toggle (supports mobile tap & keyboard Escape)
  const energyInfoBtn = document.getElementById('energyInfoBtn');
  const energyInfoTooltipWrap = document.getElementById('energyInfoTooltipWrap');
  if (energyInfoBtn && energyInfoTooltipWrap) {
    energyInfoBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      energyInfoTooltipWrap.classList.toggle('active');
    });
    document.addEventListener('click', (e) => {
      if (!energyInfoTooltipWrap.contains(e.target)) {
        energyInfoTooltipWrap.classList.remove('active');
      }
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        energyInfoTooltipWrap.classList.remove('active');
      }
    });
  }

  // Dynamic Energy helper note synchronization
  const energyHelperNote = document.getElementById('energyHelperNote');
  const energyDescriptions = {
    'low': '🍃 Spacious tempo & phrasing — lets your input noise take center stage',
    'balanced': '⚖️ Classic song structure balancing source noise with synth groove',
    'high': '⚡ Faster tempo, denser phrasing & energetic build-ups'
  };

  if (energySelect && energyHelperNote) {
    energySelect.addEventListener('change', () => {
      energyHelperNote.textContent = energyDescriptions[energySelect.value] || '';
    });
  }

  // Generation & Status UI Elements
  const emptyState = document.getElementById('emptyState');
  const processingState = document.getElementById('processingState');
  const resultsDisplay = document.getElementById('resultsDisplay');
  const progressPercent = document.getElementById('progressPercent');
  const progressStage = document.getElementById('progressStage');
  const progressBarFill = document.getElementById('progressBarFill');

  // Candidate tabs & metadata banner
  const candidateTabs = document.getElementById('candidateTabs');
  const metaGenre = document.getElementById('metaGenre');
  const metaTempo = document.getElementById('metaTempo');
  const metaScale = document.getElementById('metaScale');
  const metaDuration = document.getElementById('metaDuration');
  const metaSourceRatio = document.getElementById('metaSourceRatio');
  const metaSynthRatio = document.getElementById('metaSynthRatio');
  const metaScore = document.getElementById('metaScore');
  const metaSeed = document.getElementById('metaSeed');

  // Waveform displays & controls
  const srcNameDisplay = document.getElementById('srcNameDisplay');
  const srcTimeDisplay = document.getElementById('srcTimeDisplay');
  const srcWaveformCanvas = document.getElementById('srcWaveformCanvas');
  const srcPlayhead = document.getElementById('srcPlayhead');
  const srcCanvasWrapper = document.getElementById('srcCanvasWrapper');
  const btnPlaySource = document.getElementById('btnPlaySource');
  const srcPlayIcon = document.getElementById('srcPlayIcon');
  const srcPlayText = document.getElementById('srcPlayText');

  const resFormDisplay = document.getElementById('resFormDisplay');
  const resTimeDisplay = document.getElementById('resTimeDisplay');
  const resWaveformCanvas = document.getElementById('resWaveformCanvas');
  const resPlayhead = document.getElementById('resPlayhead');
  const resCanvasWrapper = document.getElementById('resCanvasWrapper');
  const btnPlayResult = document.getElementById('btnPlayResult');
  const resPlayIcon = document.getElementById('resPlayIcon');
  const resPlayText = document.getElementById('resPlayText');
  const btnDownload = document.getElementById('btnDownload');

  const SVG_PLAY = '<svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14" style="display:block;"><polygon points="6 4 20 12 6 20 6 4"/></svg>';
  const SVG_PAUSE = '<svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14" style="display:block;"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>';

  // A/B Studio Comparison & Stem Elements
  const btnABSwitch = document.getElementById('btnABSwitch');
  const abSwitchIndicator = document.getElementById('abSwitchIndicator');
  const abActiveChip = document.getElementById('abActiveChip');
  const abBalanceSlider = document.getElementById('abBalanceSlider');
  const faderBlendLabel = document.getElementById('faderBlendLabel');
  const btnSoloA = document.getElementById('btnSoloA');
  const btnSoloB = document.getElementById('btnSoloB');
  const btnPresetA = document.getElementById('btnPresetA');
  const btnPresetBlend = document.getElementById('btnPresetBlend');
  const btnPresetB = document.getElementById('btnPresetB');
  const btnSkipBackSource = document.getElementById('btnSkipBackSource');
  const btnSkipFwdSource = document.getElementById('btnSkipFwdSource');
  const btnSpeedSource = document.getElementById('btnSpeedSource');
  const btnSkipBackResult = document.getElementById('btnSkipBackResult');
  const btnSkipFwdResult = document.getElementById('btnSkipFwdResult');
  const btnSpeedResult = document.getElementById('btnSpeedResult');
  const stemDrumsDesc = document.getElementById('stemDrumsDesc');
  const stemHatsDesc = document.getElementById('stemHatsDesc');
  const stemLeadDesc = document.getElementById('stemLeadDesc');
  const stemChordsDesc = document.getElementById('stemChordsDesc');
  const stemFXDesc = document.getElementById('stemFXDesc');
  const stemBassDesc = document.getElementById('stemBassDesc');

  // Acoustic DNA Panel Elements
  const catPill = document.getElementById('catPill');
  const meterRhythm = document.getElementById('meterRhythm');
  const valRhythm = document.getElementById('valRhythm');
  const meterHarmonic = document.getElementById('meterHarmonic');
  const valHarmonic = document.getElementById('valHarmonic');
  const meterTexture = document.getElementById('meterTexture');
  const valTexture = document.getElementById('valTexture');
  const meterEnergy = document.getElementById('meterEnergy');
  const valEnergy = document.getElementById('valEnergy');

  const dnaDetectedPitch = document.getElementById('dnaDetectedPitch');
  const dnaActiveStems = document.getElementById('dnaActiveStems');
  const dnaPaletteSlices = document.getElementById('dnaPaletteSlices');
  const dnaClassReason = document.getElementById('dnaClassReason');
  const dnaFormName = document.getElementById('dnaFormName');
  // Duration toggle elements
  const btnDur30 = document.getElementById('btnDur30');
  const btnDur60 = document.getElementById('btnDur60');
  const generateBtnLabel = document.getElementById('generateBtnLabel');

  // Hidden Audio Players & Notifications
  const sourceAudioPlayer = document.getElementById('sourceAudioPlayer');
  const resultAudioPlayer = document.getElementById('resultAudioPlayer');
  const toastContainer = document.getElementById('toastContainer');

  // Persistent Spotify Bottom Player Elements
  const bottomPlayer = document.getElementById('bottomPlayer');
  const playerTrackTitle = document.getElementById('playerTrackTitle');
  const playerTrackSubtitle = document.getElementById('playerTrackSubtitle');
  const btnPlayerFav = document.getElementById('btnPlayerFav');
  const playerBtnShuffle = document.getElementById('playerBtnShuffle');
  const playerBtnPrev = document.getElementById('playerBtnPrev');
  const playerBtnSkipBack = document.getElementById('playerBtnSkipBack');
  const playerBtnPlay = document.getElementById('playerBtnPlay');
  const playerPlaySvg = document.getElementById('playerPlaySvg');
  const playerBtnSkipFwd = document.getElementById('playerBtnSkipFwd');
  const playerBtnNext = document.getElementById('playerBtnNext');
  const playerBtnLoop = document.getElementById('playerBtnLoop');
  const playerBtnSpeed = document.getElementById('playerBtnSpeed');
  const playerCurrentTime = document.getElementById('playerCurrentTime');
  const playerTotalDuration = document.getElementById('playerTotalDuration');
  const playerSliderTrack = document.getElementById('playerSliderTrack');
  const playerSliderFill = document.getElementById('playerSliderFill');
  const playerSliderThumb = document.getElementById('playerSliderThumb');
  const playerBtnTogglePanel = document.getElementById('playerBtnTogglePanel');
  const btnCloseRightPanel = document.getElementById('btnCloseRightPanel');
  const playerBtnDownload = document.getElementById('playerBtnDownload');
  const playerBtnVolume = document.getElementById('playerBtnVolume');
  const volumeSliderTrack = document.getElementById('volumeSliderTrack');
  const volumeSliderFill = document.getElementById('volumeSliderFill');
  const volumeSvg = document.getElementById('volumeSvg');

  // Right Panel & Shell Elements
  const spotifyShell = document.querySelector('.spotify-shell');
  const rightPanelTrackTitle = document.getElementById('rightPanelTrackTitle');
  const rightPanelTrackSub = document.getElementById('rightPanelTrackSub');
  const btnScrollToDNA = document.getElementById('btnScrollToDNA');

  // Library & Search Elements
  const libCurrentTrack = document.getElementById('libCurrentTrack');
  const libTrackTitle = document.getElementById('libTrackTitle');
  const libTrackMeta = document.getElementById('libTrackMeta');
  const libSourceTrack = document.getElementById('libSourceTrack');
  const libSourceTitle = document.getElementById('libSourceTitle');
  const quickFilterInput = document.getElementById('quickFilterInput');

  // State
  let currentFile = null;
  let currentJobId = null;
  let currentResultData = null;
  let activeCandidateIndex = 0;
  let isRecording = false;
  let mediaRecorder = null;
  let audioChunks = [];
  let recordStartTime = 0;
  let recordTimerInterval = null;
  let micAudioContext = null;
  let micAnalyser = null;
  let micStream = null;
  let micAnimFrame = null;
  let isLooping = false;
  let isMuted = false;
  let previousVolume = 0.8;
  let currentVolume = 0.8;
  let activePlayingTarget = 'result'; // 'result' or 'source'
  let selectedDuration = 30; // 30 or 60 seconds
  let currentPlaybackRate = 1.0;
  const PLAYBACK_SPEEDS = [0.75, 1.0, 1.25, 1.5, 2.0];
  let balanceValue = 100; // 0 = 100% source, 100 = 100% result
  let isPlayheadRafRunning = false;
  let isScrubbing = false;
  let isVolumeDragging = false;

  // Set default audio volume
  sourceAudioPlayer.volume = currentVolume;
  resultAudioPlayer.volume = currentVolume;

  // Web Audio Context for Waveform Decoding
  let decodeAudioCtx = null;
  function getDecodeAudioContext() {
    if (!decodeAudioCtx) {
      decodeAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    return decodeAudioCtx;
  }

  // Toast Notifications
  function showToast(message, type = 'info', title = '') {
    if (!toastContainer) {
      alert(message);
      return;
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const defaultTitle = type === 'error' ? 'Notice' : (type === 'success' ? 'Success' : 'The Unnecessary FM');
    toast.innerHTML = `
      <div style="flex: 1;">
        <div class="toast-title">${title || defaultTitle}</div>
        <div class="toast-message">${escapeHtml(message)}</div>
      </div>
      <button type="button" class="toast-close" title="Close">&times;</button>
    `;
    toast.querySelector('.toast-close').addEventListener('click', () => {
      toast.remove();
    });
    toastContainer.appendChild(toast);
    setTimeout(() => {
      if (toast.parentElement) toast.remove();
    }, 5000);
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, s => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[s]));
  }

  // 1. File Upload & Drag-and-Drop
  if (dropZone) {
    dropZone.addEventListener('click', (e) => {
      if (e.target !== btnRemoveFile && !btnRemoveFile.contains(e.target)) {
        fileInput.click();
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        handleFileSelected(e.target.files[0]);
      }
    });

    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropZone.classList.remove('dragover');
      });
    });

    dropZone.addEventListener('drop', (e) => {
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFileSelected(e.dataTransfer.files[0]);
      }
    });
  }

  if (btnRemoveFile) {
    btnRemoveFile.addEventListener('click', (e) => {
      e.stopPropagation();
      resetFileInput();
    });
  }

  // Dynamic server upload limit (defaults to 15MB, synced via /api/config)
  let maxFileSizeBytes = 15 * 1024 * 1024;
  let maxFileSizeMB = 15;

  async function syncServerConfig() {
    try {
      const res = await fetch(buildUrl('/api/config'));
      if (res.ok) {
        const data = await res.json();
        if (data.file_size_limit_bytes) {
          maxFileSizeBytes = Number(data.file_size_limit_bytes);
          maxFileSizeMB = data.file_size_limit_mb || Math.round(maxFileSizeBytes / (1024 * 1024));
          updateUploadLimitUI();
        }
      }
    } catch (e) {
      // Keep resilient 15MB default
    }
  }

  function updateUploadLimitUI() {
    const hintEl = document.getElementById('uploadLimitHint');
    if (hintEl) {
      hintEl.textContent = `${maxFileSizeMB}MB`;
    }
  }

  // Fetch server configuration on startup
  syncServerConfig();

  function handleFileSelected(file) {
    if (!file) return;

    if (file.size > maxFileSizeBytes) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
      showToast(`File size (${sizeMB} MB) exceeds the ${maxFileSizeMB} MB limit. Please select a smaller audio clip.`, 'error', 'FILE TOO LARGE');
      resetFileInput();
      return;
    }

    currentFile = file;
    if (selectedFileName) {
      selectedFileName.textContent = file.name;
      selectedFileName.title = file.name;
    }
    if (selectedFileSize) selectedFileSize.textContent = (file.size / (1024 * 1024)).toFixed(2) + ' MB';
    if (dropZoneContent) dropZoneContent.classList.add('hidden');
    if (selectedFilePill) selectedFilePill.classList.remove('hidden');
    if (btnGenerate) {
      btnGenerate.disabled = false;
      btnGenerate.title = 'Create procedural music from audio';
      btnGenerate.classList.add('ready');
    }

    // Update Player & Library state
    if (playerTrackTitle) playerTrackTitle.textContent = file.name;
    if (playerTrackSubtitle) playerTrackSubtitle.textContent = 'Uploaded Audio • Ready to Compose';
    if (libSourceTitle) libSourceTitle.textContent = file.name;

    showToast(`Loaded "${file.name}". Ready to compose ${selectedDuration}s music!`, 'success', 'AUDIO READY');
  }

  function resetFileInput() {
    currentFile = null;
    fileInput.value = '';
    if (selectedFilePill) selectedFilePill.classList.add('hidden');
    if (dropZoneContent) dropZoneContent.classList.remove('hidden');
    if (!currentJobId && btnGenerate) {
      btnGenerate.disabled = true;
      btnGenerate.title = 'Upload or record audio on the left first';
      btnGenerate.classList.remove('ready');
    }
  }

  // 2. Microphone Recording (5 - 60s)
  if (btnRecord) {
    btnRecord.addEventListener('click', async () => {
      if (!isRecording) {
        startMicRecording();
      } else {
        stopMicRecording();
      }
    });
  }

  async function startMicRecording() {
    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      mediaRecorder = new MediaRecorder(micStream);
      audioChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunks.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const recordedFile = new File([audioBlob], `noise_recording_${Date.now()}.webm`, { type: 'audio/webm' });
        handleFileSelected(recordedFile);
        cleanupMicStream();
      };

      mediaRecorder.start(100);
      isRecording = true;
      btnRecord.classList.add('recording');
      if (recordBtnText) recordBtnText.textContent = 'Stop Recording';
      if (recTimer) recTimer.classList.remove('hidden');
      if (liveMicCanvas) liveMicCanvas.classList.remove('hidden');

      recordStartTime = Date.now();
      updateRecordTimer();
      recordTimerInterval = setInterval(updateRecordTimer, 500);

      // Start live visualizer
      startLiveMicVisualizer(micStream);

      // Auto stop at 60s
      setTimeout(() => {
        if (isRecording) {
          stopMicRecording();
        }
      }, 60000);

    } catch (err) {
      showToast('Microphone access was denied or not available: ' + err.message, 'error', 'MIC ACCESS ERROR');
    }
  }

  function stopMicRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
    isRecording = false;
    if (btnRecord) btnRecord.classList.remove('recording');
    if (recordBtnText) recordBtnText.textContent = 'Record Mic (5–60s)';
    if (recTimer) recTimer.classList.add('hidden');
    if (liveMicCanvas) liveMicCanvas.classList.add('hidden');
    if (recordTimerInterval) {
      clearInterval(recordTimerInterval);
      recordTimerInterval = null;
    }
  }

  function updateRecordTimer() {
    const elapsed = Math.floor((Date.now() - recordStartTime) / 1000);
    const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const s = String(elapsed % 60).padStart(2, '0');
    if (recTimeDisplay) recTimeDisplay.textContent = `${m}:${s}`;
  }

  function startLiveMicVisualizer(stream) {
    if (!liveMicCanvas) return;
    micAudioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = micAudioContext.createMediaStreamSource(stream);
    micAnalyser = micAudioContext.createAnalyser();
    micAnalyser.fftSize = 64;
    source.connect(micAnalyser);

    const canvasCtx = liveMicCanvas.getContext('2d');
    const dataArray = new Uint8Array(micAnalyser.frequencyBinCount);

    function draw() {
      if (!isRecording) return;
      micAnimFrame = requestAnimationFrame(draw);
      micAnalyser.getByteFrequencyData(dataArray);

      canvasCtx.clearRect(0, 0, liveMicCanvas.width, liveMicCanvas.height);
      const barWidth = (liveMicCanvas.width / dataArray.length) * 1.5;
      let x = 0;

      for (let i = 0; i < dataArray.length; i++) {
        const barHeight = (dataArray[i] / 255) * (liveMicCanvas.height - 4);
        canvasCtx.fillStyle = '#1ed760';
        canvasCtx.fillRect(x, liveMicCanvas.height - barHeight, Math.max(2, barWidth - 2), barHeight);
        x += barWidth;
      }
    }
    draw();
  }

  function cleanupMicStream() {
    if (micStream) {
      micStream.getTracks().forEach(t => t.stop());
      micStream = null;
    }
    if (micAudioContext) {
      micAudioContext.close();
      micAudioContext = null;
    }
    if (micAnimFrame) {
      cancelAnimationFrame(micAnimFrame);
      micAnimFrame = null;
    }
  }

  // 3. Seed Helpers
  if (btnRandomizeSeed) {
    btnRandomizeSeed.addEventListener('click', () => {
      seedInput.value = Math.floor(Math.random() * 9000000000) + 1000000000;
    });
  }

  if (metaSeed) {
    metaSeed.style.cursor = 'pointer';
    metaSeed.addEventListener('click', () => {
      const val = metaSeed.textContent.trim();
      if (val && navigator.clipboard) {
        navigator.clipboard.writeText(val).then(() => {
          showToast(`Seed ${val} copied to clipboard!`, 'success', 'SEED COPIED');
        }).catch(() => {});
      }
    });
  }

  // Hero Quick CTA Buttons
  const btnHeroUpload = document.getElementById('btnHeroUpload');
  const btnHeroRecord = document.getElementById('btnHeroRecord');

  if (btnHeroUpload) {
    btnHeroUpload.addEventListener('click', (e) => {
      e.preventDefault();
      const studio = document.getElementById('studioSection');
      if (studio) studio.scrollIntoView({ behavior: 'smooth', block: 'start' });
      if (audioFileInput) audioFileInput.click();
    });
  }

  if (btnHeroRecord) {
    btnHeroRecord.addEventListener('click', (e) => {
      e.preventDefault();
      const studio = document.getElementById('studioSection');
      if (studio) studio.scrollIntoView({ behavior: 'smooth', block: 'start' });
      if (btnRecord && !isRecording) btnRecord.click();
    });
  }

  // 4. Quick Preset Shelves
  document.querySelectorAll('.preset-card').forEach(card => {
    card.addEventListener('click', () => {
      const g = card.dataset.genre;
      const e = card.dataset.energy;
      if (g && beatSelect) {
        beatSelect.value = g;
        populateStyleDropdown();
      }
      if (e && energySelect) {
        energySelect.value = e;
        if (energyHelperNote) energyHelperNote.textContent = energyDescriptions[e] || '';
      }
      const title = card.querySelector('h3') ? card.querySelector('h3').textContent : g;
      showToast(`Selected style: ${title}. Choose an audio file and hit Create!`, 'info', 'STYLE PRESET');

      // Scroll to studio
      const studioSec = document.getElementById('studioSection');
      if (studioSec) {
        studioSec.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });

  // Quick filter search
  const genreSearchInput = document.getElementById('genreSearchInput');
  if (genreSearchInput) {
    genreSearchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      document.querySelectorAll('.preset-card').forEach(card => {
        const text = card.textContent.toLowerCase();
        card.style.display = (!q || text.includes(q)) ? '' : 'none';
      });
    });
  }

  // Quick Mode Chips in Hero
  document.querySelectorAll('.mode-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const genre = chip.dataset.genre;
      if (genre && beatSelect) {
        beatSelect.value = genre;
        populateStyleDropdown();
        document.querySelectorAll('.mode-chip').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        showToast(`Genre directive set: ${chip.textContent.trim()}`, 'success', 'GENRE DIRECTIVE');
      }
    });
  });

  // Navigation Links
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      const target = item.dataset.target;
      if (target === 'home') {
        const h = document.getElementById('heroBanner');
        if (h) h.scrollIntoView({ behavior: 'smooth' });
      } else if (target === 'studio') {
        const s = document.getElementById('studioSection');
        if (s) s.scrollIntoView({ behavior: 'smooth' });
      } else if (target === 'dna') {
        if (spotifyShell) spotifyShell.classList.remove('right-panel-closed');
      } else if (target === 'presets') {
        const p = document.getElementById('presetsShelf');
        if (p) p.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });

  // Mobile Nav items
  document.querySelectorAll('.mobile-nav-item').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.mobile-nav-item').forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      const target = item.dataset.target;
      if (target === 'home') {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else if (target === 'studio') {
        const s = document.getElementById('studioSection');
        if (s) s.scrollIntoView({ behavior: 'smooth' });
      } else if (target === 'results') {
        const r = document.getElementById('resultsSection');
        if (r) r.scrollIntoView({ behavior: 'smooth' });
      } else if (target === 'dna') {
        showToast('Acoustic DNA is displayed in the Right Panel on desktop!', 'info', 'ACOUSTIC DNA');
      }
    });
  });

  // 5. Generate Music Request
  if (btnGenerate) {
    btnGenerate.addEventListener('click', () => {
      submitMusicGeneration();
    });
  }

  // Duration toggle
  if (btnDur30) {
    btnDur30.addEventListener('click', () => {
      selectedDuration = 30;
      btnDur30.classList.add('active');
      btnDur30.setAttribute('aria-pressed', 'true');
      if (btnDur60) {
        btnDur60.classList.remove('active');
        btnDur60.setAttribute('aria-pressed', 'false');
      }
      if (generateBtnLabel) generateBtnLabel.textContent = 'CREATE MUSIC (30s)';
      if (playerTotalDuration && (!currentResultData || !currentResultData.winner)) playerTotalDuration.textContent = '00:30';
      if (libTrackMeta && (!currentResultData || !currentResultData.winner)) {
        libTrackMeta.textContent = 'Your Produced Tune (30s)';
      }
    });
  }
  if (btnDur60) {
    btnDur60.addEventListener('click', () => {
      selectedDuration = 60;
      btnDur60.classList.add('active');
      btnDur60.setAttribute('aria-pressed', 'true');
      if (btnDur30) {
        btnDur30.classList.remove('active');
        btnDur30.setAttribute('aria-pressed', 'false');
      }
      if (generateBtnLabel) generateBtnLabel.textContent = 'CREATE MUSIC (60s)';
      if (playerTotalDuration && (!currentResultData || !currentResultData.winner)) playerTotalDuration.textContent = '01:00';
      if (libTrackMeta && (!currentResultData || !currentResultData.winner)) {
        libTrackMeta.textContent = 'Your Produced Tune (60s)';
      }
    });
  }

  // Vocal Mode Select (Smart Auto / Lead Vocal / Chops)
  if (vocalModeSelect) {
    vocalModeSelect.addEventListener('change', () => {
      const mode = vocalModeSelect.value;
      if (vocalHelperNote) {
        if (mode === 'lead') {
          vocalHelperNote.textContent = '🎙️ Plays your full recording in 100% continuous chronological order, zero chopping & studio vocal chain';
        } else if (mode === 'chops') {
          vocalHelperNote.textContent = '✂️ Slices vocal input into fast, syncopated soul chops & rhythmic riffs';
        } else {
          vocalHelperNote.textContent = '✨ Automatically plays continuous unbroken vocals without cutting off words or chopping';
        }
      }
    });
  }

  // ---------------------------------------------------------------------------
  // BROWSER LOCALSTORAGE ARTIST CYCLING MANAGER ("Bag Without Replacement")
  // Stores played history strictly in user's browser localStorage (zero server files)
  // ---------------------------------------------------------------------------
  const PLAYED_ARTISTS_STORAGE_KEY = 'unnecessaryfm_played_artists';

  function getPlayedArtistsMap() {
    try {
      const raw = localStorage.getItem(PLAYED_ARTISTS_STORAGE_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      return {};
    }
  }

  function recordPlayedArtist(genre, artistId, cycleReset) {
    if (!genre || !artistId) return;
    try {
      const g = genre.toLowerCase();
      let map = getPlayedArtistsMap();
      if (cycleReset || !Array.isArray(map[g])) {
        map[g] = [artistId];
      } else if (!map[g].includes(artistId)) {
        map[g].push(artistId);
      }
      localStorage.setItem(PLAYED_ARTISTS_STORAGE_KEY, JSON.stringify(map));
    } catch (e) {
      console.warn("localStorage artist tracking error", e);
    }
  }

  async function submitMusicGeneration() {
    if (!currentFile && !currentJobId) return;

    if (currentFile && currentFile.size > maxFileSizeBytes) {
      const sizeMB = (currentFile.size / (1024 * 1024)).toFixed(1);
      showToast(`File size (${sizeMB} MB) exceeds the ${maxFileSizeMB} MB limit. Please select a smaller audio clip.`, 'error', 'FILE TOO LARGE');
      return;
    }

    showProcessingState("Initializing DSP pipeline & decoding acoustic timbre...");

    const formData = new FormData();
    if (currentFile) {
      formData.append('file', currentFile);
    } else if (currentJobId) {
      formData.append('existing_job_id', currentJobId);
    }

    const selectedGenre = beatSelect ? beatSelect.value : 'pop';
    formData.append('beat_preference', selectedGenre);
    formData.append('energy_preference', energySelect ? energySelect.value : 'low');
    formData.append('duration_seconds', String(selectedDuration));
    formData.append('vocal_mode', (vocalModeSelect ? vocalModeSelect.value : 'auto'));
    if (seedInput && seedInput.value.trim()) {
      formData.append('seed', seedInput.value.trim());
    }

    // If a specific style is selected, pass preferred_artist_id; otherwise pass played list for auto-cycling
    if (styleSelect && styleSelect.value) {
      formData.append('preferred_artist_id', styleSelect.value);
    } else {
      const playedMap = getPlayedArtistsMap();
      const playedList = playedMap[selectedGenre.toLowerCase()] || [];
      if (playedList.length > 0) {
        formData.append('played_artists', playedList.join(','));
      }
    }


    try {
      const response = await fetch(buildUrl('/api/generate'), {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to submit generation job');
      }

      const data = await response.json();
      currentJobId = data.job_id;
      sessionStorage.setItem('unnecessary_fm_active_job', currentJobId);
      trackJobProgress(currentJobId);

    } catch (err) {
      showToast(err.message, 'error', 'COMPOSITION FAILED');
      hideProcessingState();
    }
  }

  function showProcessingState(stageText) {
    if (emptyState) emptyState.classList.add('hidden');
    if (resultsDisplay) resultsDisplay.classList.add('hidden');
    if (processingState) processingState.classList.remove('hidden');
    if (progressPercent) progressPercent.textContent = '15%';
    if (progressBarFill) progressBarFill.style.width = '15%';
    if (progressStage) progressStage.textContent = stageText || 'Processing...';
    if (btnGenerate) btnGenerate.disabled = true;

    // Scroll to results section
    const resSec = document.getElementById('resultsSection');
    if (resSec) resSec.scrollIntoView({ behavior: 'smooth' });
  }

  function hideProcessingState() {
    if (processingState) processingState.classList.add('hidden');
    if (btnGenerate) btnGenerate.disabled = false;
  }

  // 6. Real-Time Job Progress Tracking (SSE + Fallback Polling + Background Tab Sync)
  // Authentic project quotes from README.md
  const README_QUOTES = [
    `"The world is full of perfectly ordinary noises, but for some reason, they aren't songs. We decided this was unacceptable."`,
    `"Unnecessary FM turns ordinary noises into songs. Because apparently, being a noise wasn't enough."`,
    `"Wish these loud honking noises would become music instead! And can you believe it, that's when we had this eureka moment."`,
    `"We've been shouting hello, hi, bye into laptop mics, capturing clapping noises, and laughing as our algorithms turn it into tunes!"`,
    `"Doing wizard math on sound waves with frequency filters and beat grids!"`,
    `"Extracting the soul of that noise, and turning it into something, uhh, pleasing? Almost ready!"`
  ];

  let activeEventSource = null;
  let activePollInterval = null;
  let activeQuoteInterval = null;

  function cleanupJobTracking() {
    if (activeEventSource) {
      activeEventSource.close();
      activeEventSource = null;
    }
    if (activePollInterval) {
      clearInterval(activePollInterval);
      activePollInterval = null;
    }
    if (activeQuoteInterval) {
      clearInterval(activeQuoteInterval);
      activeQuoteInterval = null;
    }
  }

  function trackJobProgress(jobId) {
    cleanupJobTracking();

    const processingQuoteEl = document.getElementById('processingQuote');
    let quoteIdx = 0;
    activeQuoteInterval = setInterval(() => {
      if (!processingQuoteEl) return;
      quoteIdx = (quoteIdx + 1) % README_QUOTES.length;
      processingQuoteEl.style.opacity = '0';
      setTimeout(() => {
        if (processingQuoteEl) {
          processingQuoteEl.textContent = README_QUOTES[quoteIdx];
          processingQuoteEl.style.opacity = '1';
        }
      }, 300);
    }, 4500);

    const applyProgressUpdate = (data) => {
      if (!data) return;
      const pct = Math.max(10, Math.min(100, Math.round(data.progress || 10)));
      if (progressPercent) progressPercent.textContent = `${pct}%`;
      if (progressBarFill) progressBarFill.style.width = `${pct}%`;
      if (progressStage && data.stage) {
        progressStage.textContent = data.stage;
      }

      if (data.status === 'completed') {
        cleanupJobTracking();
        sessionStorage.removeItem('unnecessary_fm_active_job');
        if (progressPercent) progressPercent.textContent = '100%';
        if (progressBarFill) progressBarFill.style.width = '100%';
        loadFinalResults(jobId, true);
      } else if (data.status === 'failed') {
        cleanupJobTracking();
        sessionStorage.removeItem('unnecessary_fm_active_job');
        showToast(data.error || 'DSP synthesis error', 'error', 'SYNTHESIS ERROR');
        hideProcessingState();
      }
    };

    // 1. Try Server-Sent Events (SSE) first for instant real-time pushes
    if (typeof EventSource !== 'undefined') {
      try {
        const sseUrl = buildUrl(`/api/progress/${jobId}`);
        activeEventSource = new EventSource(sseUrl);

        activeEventSource.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            applyProgressUpdate(data);
          } catch (e) {
            console.error("SSE parse error", e);
          }
        };

        activeEventSource.onerror = () => {
          // If SSE connection drops or is blocked, seamlessly fallback to polling
          if (activeEventSource) {
            activeEventSource.close();
            activeEventSource = null;
          }
          if (!activePollInterval) {
            startPollingFallback(jobId, applyProgressUpdate);
          }
        };
      } catch (e) {
        startPollingFallback(jobId, applyProgressUpdate);
      }
    } else {
      startPollingFallback(jobId, applyProgressUpdate);
    }
  }

  function startPollingFallback(jobId, applyProgressUpdate) {
    if (activePollInterval) return;
    let failCount = 0;
    activePollInterval = setInterval(async () => {
      try {
        const res = await fetch(buildUrl(`/api/status/${jobId}`));
        if (!res.ok) {
          failCount++;
          if (failCount >= 10) {
            cleanupJobTracking();
            sessionStorage.removeItem('unnecessary_fm_active_job');
            showToast('Service temporarily unavailable. Please try generating again.', 'error', 'CONNECTION ERROR');
            hideProcessingState();
          }
          return;
        }
        failCount = 0;
        const statusData = await res.json();
        applyProgressUpdate(statusData);
      } catch (err) {
        failCount++;
        if (failCount >= 10) {
          cleanupJobTracking();
          sessionStorage.removeItem('unnecessary_fm_active_job');
          showToast('Connection interrupted. Please try again.', 'error', 'NETWORK ERROR');
          hideProcessingState();
        }
      }
    }, 1000);
  }

  // Handle Tab Switch / Backgrounding: Instantly sync latest status when user switches back to tab
  document.addEventListener('visibilitychange', async () => {
    if (document.visibilityState === 'visible' && currentJobId && !currentResultData) {
      try {
        const res = await fetch(buildUrl(`/api/status/${currentJobId}`));
        if (res.ok) {
          const statusData = await res.json();
          const pct = Math.max(10, Math.min(100, Math.round(statusData.progress || 10)));
          if (progressPercent) progressPercent.textContent = `${pct}%`;
          if (progressBarFill) progressBarFill.style.width = `${pct}%`;
          if (progressStage && statusData.stage) progressStage.textContent = statusData.stage;
          if (statusData.status === 'completed') {
            cleanupJobTracking();
            sessionStorage.removeItem('unnecessary_fm_active_job');
            loadFinalResults(currentJobId, true);
          } else if (statusData.status === 'failed') {
            cleanupJobTracking();
            sessionStorage.removeItem('unnecessary_fm_active_job');
            showToast(statusData.error || 'DSP synthesis error', 'error', 'SYNTHESIS ERROR');
            hideProcessingState();
          }
        }
      } catch (e) {}
    }
  });

  // 7. Load & Render Results
  async function loadFinalResults(jobId, isNewGeneration = false) {
    try {
      const res = await fetch(buildUrl(`/api/result/${jobId}`));
      if (!res.ok) throw new Error('Failed to retrieve result');

      currentResultData = await res.json();
      renderCompositionUI(currentResultData);
      if (isNewGeneration) {
        const candCount = (currentResultData.candidates && currentResultData.candidates.length) || 1;
        const winnerDur = (currentResultData.winner && currentResultData.winner.duration)
          ? Math.round(currentResultData.winner.duration)
          : selectedDuration;
        showToast(`${winnerDur}-second music composition synthesized across ${candCount} candidate${candCount > 1 ? 's' : ''}!`, 'success', 'TA DAA!');
      }

    } catch (err) {
      showToast(err.message, 'error', 'LOAD ERROR');
      hideProcessingState();
    }
  }

  function renderCompositionUI(result) {
    if (processingState) processingState.classList.add('hidden');
    if (emptyState) emptyState.classList.add('hidden');
    if (resultsDisplay) resultsDisplay.classList.remove('hidden');
    if (btnGenerate) btnGenerate.disabled = false;

    // Populate DNA Panel
    const analysis = result.source.analysis || {};
    const sp = analysis.smart_profile || (result.candidates && result.candidates[0] && result.candidates[0].smart_profile) || null;
    if (catPill) {
      if (sp && sp.display_title) {
        catPill.textContent = sp.display_title.toUpperCase();
      } else {
        catPill.textContent = analysis.classification || 'TEXTURAL';
      }
    }

    const rDens = analysis.rhythmic_density || 0;
    if (meterRhythm) meterRhythm.style.width = `${Math.min(100, rDens * 35)}%`;
    if (valRhythm) valRhythm.textContent = rDens.toFixed(2);

    const harm = analysis.harmonicity || 0.5;
    if (meterHarmonic) meterHarmonic.style.width = `${Math.min(100, harm * 100)}%`;
    if (valHarmonic) valHarmonic.textContent = harm.toFixed(2);

    const text = analysis.noisiness || 0.5;
    if (meterTexture) meterTexture.style.width = `${Math.min(100, text * 100)}%`;
    if (valTexture) valTexture.textContent = text.toFixed(2);

    const bright = analysis.brightness || 0.5;
    if (meterEnergy) meterEnergy.style.width = `${Math.min(100, bright * 100)}%`;
    if (valEnergy) valEnergy.textContent = bright.toFixed(2);

    if (dnaDetectedPitch) {
      dnaDetectedPitch.textContent = analysis.has_reliable_pitch ? `${analysis.nearest_note}` : 'None (Resonators Applied)';
    }
    if (dnaClassReason) {
      if (sp && sp.settings_summary) {
        dnaClassReason.innerHTML = `<strong>Smart DSP:</strong> ${sp.settings_summary}`;
      } else {
        dnaClassReason.textContent = (analysis.reasons && analysis.reasons.length > 0) ? analysis.reasons[0] : 'Balanced harmonic & transient spectrum';
      }
    }

    // Source Audio Setup
    if (srcNameDisplay) srcNameDisplay.textContent = result.source.filename || 'source.wav';
    sourceAudioPlayer.src = buildUrl(result.source.audio_url);
    drawWaveformFromUrl(result.source.audio_url, srcWaveformCanvas, '#22d3ee');

    // Build Candidate Tabs
    if (candidateTabs) {
      candidateTabs.innerHTML = '';
      result.candidates.forEach((cand, idx) => {
        const tab = document.createElement('button');
        tab.type = 'button';
        tab.className = `cand-tab ${idx === 0 ? 'active' : ''}`;
        tab.dataset.index = idx;
        tab.innerHTML = `<span>Candidate ${String.fromCharCode(65 + idx)}</span> ${cand.is_winner ? '<span class="tag-winner">WINNER</span>' : ''}`;
        tab.addEventListener('click', () => selectCandidate(idx));
        candidateTabs.appendChild(tab);
      });
    }

    // Select Winner by default
    selectCandidate(0);
  }

  function selectCandidate(index) {
    if (!currentResultData || !currentResultData.candidates[index]) return;
    activeCandidateIndex = index;
    activePlayingTarget = 'result';

    // Update active tab styles
    const tabs = candidateTabs.querySelectorAll('.cand-tab');
    tabs.forEach((t, idx) => {
      t.classList.toggle('active', idx === index);
    });

    const cand = currentResultData.candidates[index];
    const letter = String.fromCharCode(65 + index);

    // Update Banner
    if (metaGenre) {
      const pref = (currentResultData.settings && currentResultData.settings.beat_preference) || (beatSelect ? beatSelect.value : 'pop');
      const genreLabels = {
        'pop': 'Pop',
        'rap': 'Rap / Electro',
        'hiphop': 'Hip Hop',
        'trap': 'Trap',
        'minimal': 'Minimal',
        'rhythmic': 'Rhythmic Pulse',
        'light_percussion': 'Light Percussion',
        'none': 'Ambient'
      };
      metaGenre.textContent = genreLabels[pref.toLowerCase()] || pref.toUpperCase();
    }
    if (metaTempo) metaTempo.textContent = `${cand.tempo_bpm} BPM`;
    if (metaScale) metaScale.textContent = cand.scale_name;
    if (metaDuration) metaDuration.textContent = `${cand.duration.toFixed(1)}s`;
    if (metaSourceRatio) {
      const srcPct = cand.score && cand.score.source_usage_ratio !== undefined ? Math.round(cand.score.source_usage_ratio * 100) : 100;
      metaSourceRatio.textContent = `${srcPct}%`;
    }
    if (metaSynthRatio) {
      const synPct = cand.score && cand.score.synthetic_audio_ratio !== undefined ? Math.round(cand.score.synthetic_audio_ratio * 100) : 0;
      metaSynthRatio.textContent = `${synPct}%`;
    }
    if (metaScore) metaScore.textContent = `${cand.score.total} / 100`;
    if (metaSeed) metaSeed.textContent = cand.seed;

    if (resFormDisplay) resFormDisplay.textContent = cand.form;
    if (dnaFormName) dnaFormName.textContent = cand.form;
    if (dnaActiveStems) dnaActiveStems.textContent = Object.values(cand.stems).join(', ');
    if (dnaPaletteSlices) {
      const pal = cand.palette || {};
      const tot = pal.total_slices || 48;
      const extraCounts = [];
      if (pal.full_vocal_phrases) extraCounts.push(`${pal.full_vocal_phrases} full phrases`);
      if (pal.beatbox_kicks) extraCounts.push(`${pal.beatbox_kicks} mouth kicks`);
      if (pal.beatbox_snares) extraCounts.push(`${pal.beatbox_snares} mouth snares`);
      if (pal.traffic_horns) extraCounts.push(`${pal.traffic_horns} horns`);
      if (pal.humming_slices) extraCounts.push(`${pal.humming_slices} hums`);
      if (pal.vocal_chops) extraCounts.push(`${pal.vocal_chops} vocal chops`);
      const extraStr = extraCounts.length > 0 ? ` (${extraCounts.slice(0, 3).join(', ')})` : ` (${pal.impacts || 0} impacts, ${pal.pulses || 0} pulses, ${pal.ambience || 0} beds)`;
      dnaPaletteSlices.textContent = `${tot} slices${extraStr}`;
    }

    // Update Smart Extraction Banner & DNA Smart DSP
    const smartP = cand.smart_profile || (currentResultData.source && currentResultData.source.analysis && currentResultData.source.analysis.smart_profile) || null;
    const smartBanner = document.getElementById('smartExtractionBanner');
    const smartTitle = document.getElementById('smartExtractionTitle');
    const smartDetails = document.getElementById('smartExtractionDetails');
    const dnaSmartExtraction = document.getElementById('dnaSmartExtraction');

    const isLeadVocal = cand.stems && cand.stems['Vocal Hook'] && cand.stems['Vocal Hook'].includes('Lead Vocal');

    if (smartP || isLeadVocal) {
      if (smartBanner) smartBanner.classList.remove('hidden');
      if (smartTitle) {
        smartTitle.textContent = isLeadVocal ? '🎙️ Lead Vocal Mode (Full Lyrics & Auto-Tune)' : (smartP ? smartP.display_title : 'Smart Audio Extraction');
      }
      if (smartDetails) {
        const leadPrefix = isLeadVocal ? '✨ Full phrases & lyrics preserved without cutoff, auto-tuned to track scale • ' : '';
        smartDetails.textContent = leadPrefix + (smartP ? smartP.settings_summary : 'Scale Auto-Tuned Lead Vocal active');
      }
      if (dnaSmartExtraction) {
        dnaSmartExtraction.textContent = isLeadVocal ? '🎙️ Lead Vocal: Full Phrases & Words Intact' : (smartP ? smartP.settings_summary : 'Scale Auto-Tuner Active');
      }
    } else {
      if (smartBanner) smartBanner.classList.add('hidden');
      if (dnaSmartExtraction) dnaSmartExtraction.textContent = 'Standard Multi-Scale Leveling';
    }

    // Update Stem Architecture Breakdown Cards
    const stems = cand.stems || {};
    if (stemDrumsDesc && stems.Drums) stemDrumsDesc.textContent = stems.Drums;
    if (stemHatsDesc && stems.HiHats) stemHatsDesc.textContent = stems.HiHats;
    if (stemLeadDesc && stems.Melody) stemLeadDesc.textContent = stems.Melody;
    if (stemChordsDesc && stems.Chords) stemChordsDesc.textContent = stems.Chords;
    if (stemFXDesc && stems.Accents) stemFXDesc.textContent = stems.Accents;
    if (stemBassDesc && stems.Bass) stemBassDesc.textContent = stems.Bass;

    updateABUI('result');

    // Update Sound Archetype Card in Banner and record to browser localStorage
    const metaArtist = document.getElementById('metaArtist');
    const styleDisplayName = cand.style_name || cand.artist_name || 'Sound Archetype';
    const styleDisplayDesc = cand.style_desc || cand.artist_track_hint || 'Procedural Acoustic Modeling';

    if (metaArtist) {
      metaArtist.textContent = styleDisplayName;
      metaArtist.title = `Vibe: ${styleDisplayDesc}`;
    }

    const genreKey = (currentResultData.settings && currentResultData.settings.beat_preference) || (beatSelect ? beatSelect.value : 'pop');
    if (cand.artist_id) {
      recordPlayedArtist(genreKey, cand.artist_id, cand.cycle_reset);
    }

    // Set Audio Player
    const candUrl = buildUrl(cand.audio_url);
    resultAudioPlayer.src = candUrl;
    if (btnDownload) {
      btnDownload.href = candUrl;
      btnDownload.download = `unnecessaryfm_${currentResultData.job_id}_cand${letter}.wav`;
    }
    if (playerBtnDownload) {
      playerBtnDownload.href = candUrl;
      playerBtnDownload.download = `unnecessaryfm_${currentResultData.job_id}_cand${letter}.wav`;
    }

    // Update Bottom Player & Right Panel
    const trackName = `Candidate ${letter} ${cand.is_winner ? '[Winner]' : ''}`;
    const candDur = cand.duration || selectedDuration;
    const trackSub = `${styleDisplayName} • ${cand.tempo_bpm} BPM • ${cand.scale_name}`;
    if (playerTrackTitle) playerTrackTitle.textContent = trackName;
    if (playerTrackSubtitle) playerTrackSubtitle.textContent = trackSub;
    if (rightPanelTrackTitle) rightPanelTrackTitle.textContent = trackName;
    if (rightPanelTrackSub) {
      rightPanelTrackSub.textContent = `Vibe: ${styleDisplayDesc} • ${cand.tempo_bpm} BPM`;
    }
    if (libTrackTitle) libTrackTitle.textContent = trackName;
    if (libTrackMeta) libTrackMeta.textContent = `${cand.scale_name} • ${cand.tempo_bpm} BPM (${Math.round(candDur)}s)`;

    if (playerTotalDuration) playerTotalDuration.textContent = formatTime(candDur);
    if (playerCurrentTime) playerCurrentTime.textContent = '0:00';
    if (resTimeDisplay) resTimeDisplay.textContent = `0:00 / ${formatTime(candDur)}`;

    // Reset Play Buttons
    resetResultPlayState();


    // Draw Result Waveform in Spotify Green
    drawWaveformFromUrl(candUrl, resWaveformCanvas, '#1ed760');
  }

  // 8. Audio Playback Engine & 60fps RAF Synchronization
  function getActiveAudioPlayer() {
    return (activePlayingTarget === 'source') ? sourceAudioPlayer : resultAudioPlayer;
  }

  let lastAudioTime = 0;
  let lastSyncTimestamp = performance.now();
  let lastFormattedCur = '';
  let lastFormattedDur = '';

  function startPlayheadRAF() {
    const p = getActiveAudioPlayer();
    lastAudioTime = p.currentTime || 0;
    lastSyncTimestamp = performance.now();
    if (!isPlayheadRafRunning) {
      isPlayheadRafRunning = true;
      rafId = requestAnimationFrame(updatePlayheadRAF);
    }
  }

  function stopPlayheadRAF() {
    isPlayheadRafRunning = false;
    if (rafId) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  }

  function updatePlayheadRAF() {
    if (!isPlayheadRafRunning) return;

    const p = getActiveAudioPlayer();
    const now = performance.now();
    const rawCur = p.currentTime || 0;

    // Detect when audio element clock advances (~4Hz - 8Hz)
    if (Math.abs(rawCur - lastAudioTime) > 0.005 || p.paused) {
      lastAudioTime = rawCur;
      lastSyncTimestamp = now;
    }

    // Buttery-smooth 60fps/120fps high-resolution interpolation between coarse audio ticks
    let smoothCur = rawCur;
    if (!p.paused) {
      const elapsedSec = ((now - lastSyncTimestamp) / 1000) * (p.playbackRate || 1.0);
      smoothCur = lastAudioTime + elapsedSec;
    }

    const candDur = (currentResultData && currentResultData.candidates && currentResultData.candidates[activeCandidateIndex])
      ? currentResultData.candidates[activeCandidateIndex].duration
      : selectedDuration;
    const fallbackDur = (activePlayingTarget === 'result')
      ? candDur
      : ((currentResultData && currentResultData.source && currentResultData.source.duration) ? currentResultData.source.duration : 10);
    const dur = (p.duration && !isNaN(p.duration) && p.duration > 0) ? p.duration : fallbackDur;
    smoothCur = Math.max(0, Math.min(dur, smoothCur));
    const pct = dur > 0 ? Math.max(0, Math.min(100, (smoothCur / dur) * 100)) : 0;
    const pctStr = `${pct.toFixed(2)}%`;

    if (!isScrubbing) {
      if (playerSliderFill) playerSliderFill.style.width = pctStr;
      if (playerSliderThumb) playerSliderThumb.style.left = pctStr;

      // Layout thrashing prevention: only mutate textContent once per second when string changes!
      const curStr = formatTime(smoothCur);
      const durStr = formatTime(dur);

      if (curStr !== lastFormattedCur) {
        lastFormattedCur = curStr;
        if (playerCurrentTime) playerCurrentTime.textContent = curStr;
      }
      if (durStr !== lastFormattedDur) {
        lastFormattedDur = durStr;
        if (playerTotalDuration) playerTotalDuration.textContent = durStr;
      }

      if (activePlayingTarget === 'result') {
        if (resPlayhead) resPlayhead.style.left = pctStr;
        if (resTimeDisplay) resTimeDisplay.textContent = `${curStr} / ${durStr}`;
      } else {
        if (srcPlayhead) srcPlayhead.style.left = pctStr;
        if (srcTimeDisplay) srcTimeDisplay.textContent = `${curStr} / ${durStr}`;
      }
    }

    if (!sourceAudioPlayer.paused || !resultAudioPlayer.paused) {
      rafId = requestAnimationFrame(updatePlayheadRAF);
    } else {
      isPlayheadRafRunning = false;
      rafId = null;
    }
  }

  // Audio loadedmetadata listeners to sync duration as soon as audio decodes
  resultAudioPlayer.addEventListener('loadedmetadata', () => {
    const d = resultAudioPlayer.duration;
    if (d && !isNaN(d) && d > 0 && activePlayingTarget === 'result') {
      if (playerTotalDuration) playerTotalDuration.textContent = formatTime(d);
      if (resTimeDisplay) resTimeDisplay.textContent = `${formatTime(resultAudioPlayer.currentTime || 0)} / ${formatTime(d)}`;
    }
  });

  sourceAudioPlayer.addEventListener('loadedmetadata', () => {
    const d = sourceAudioPlayer.duration;
    if (d && !isNaN(d) && d > 0 && activePlayingTarget === 'source') {
      if (playerTotalDuration) playerTotalDuration.textContent = formatTime(d);
      if (srcTimeDisplay) srcTimeDisplay.textContent = `${formatTime(sourceAudioPlayer.currentTime || 0)} / ${formatTime(d)}`;
    }
  });

  // Audio lifecycle listeners for jitter-free playhead & UI synchronization
  sourceAudioPlayer.addEventListener('play', startPlayheadRAF);
  resultAudioPlayer.addEventListener('play', startPlayheadRAF);

  sourceAudioPlayer.addEventListener('pause', () => {
    if (resultAudioPlayer.paused) stopPlayheadRAF();
    updatePlayIcons(false, 'source');
  });
  resultAudioPlayer.addEventListener('pause', () => {
    if (sourceAudioPlayer.paused) stopPlayheadRAF();
    updatePlayIcons(false, 'result');
  });

  sourceAudioPlayer.addEventListener('seeking', () => {
    lastAudioTime = sourceAudioPlayer.currentTime || 0;
    lastSyncTimestamp = performance.now();
  });
  resultAudioPlayer.addEventListener('seeking', () => {
    lastAudioTime = resultAudioPlayer.currentTime || 0;
    lastSyncTimestamp = performance.now();
  });

  if (btnPlaySource) {
    btnPlaySource.addEventListener('click', () => {
      toggleSourcePlayback();
    });
  }

  if (btnPlayResult) {
    btnPlayResult.addEventListener('click', () => {
      toggleResultPlayback();
    });
  }

  // Persistent Player Play/Pause Button
  if (playerBtnPlay) {
    playerBtnPlay.addEventListener('click', () => {
      if (activePlayingTarget === 'source') {
        toggleSourcePlayback();
      } else {
        toggleResultPlayback();
      }
    });
  }

  function updateABUI(target) {
    if (!abSwitchIndicator || !btnABSwitch) return;
    if (target === 'source') {
      abSwitchIndicator.textContent = 'Playing: [A] Raw Source Noise';
      btnABSwitch.className = 'btn-ab-switch playing-source';
      if (abActiveChip) abActiveChip.textContent = 'Active: [A] Raw Noise';
      if (faderBlendLabel) faderBlendLabel.textContent = '100% Raw [A]';
      if (abBalanceSlider) abBalanceSlider.value = 0;
      updateFaderButtonsState(0);
    } else {
      abSwitchIndicator.textContent = 'Playing: [B] Produced Track';
      btnABSwitch.className = 'btn-ab-switch playing-result';
      if (abActiveChip) abActiveChip.textContent = 'Active: [B] Produced Track';
      if (faderBlendLabel) faderBlendLabel.textContent = '100% Master [B]';
      if (abBalanceSlider) abBalanceSlider.value = 100;
      updateFaderButtonsState(100);
    }
  }

  function updateFaderButtonsState(val) {
    if (btnSoloA) btnSoloA.classList.toggle('active', val === 0);
    if (btnSoloB) btnSoloB.classList.toggle('active', val === 100);
    if (btnPresetA) btnPresetA.classList.toggle('active', val === 0);
    if (btnPresetBlend) btnPresetBlend.classList.toggle('active', val > 35 && val < 65);
    if (btnPresetB) btnPresetB.classList.toggle('active', val === 100);

    if (abBalanceSlider) {
      // Set dynamic border-color on slider thumb
      const thumbColor = val === 0 ? '#38bdf8' : (val === 100 ? '#1ed760' : '#ffffff');
      abBalanceSlider.style.setProperty('--thumb-color', thumbColor);
    }
  }

  // Click-free Micro-fade A/B Transition
  function toggleABComparison() {
    if (!sourceAudioPlayer.src || !resultAudioPlayer.src) {
      showToast('Generate or select a composition first to compare A/B!', 'info');
      return;
    }

    if (activePlayingTarget === 'result') {
      crossfadeToTarget('source');
    } else {
      crossfadeToTarget('result');
    }
  }

  function crossfadeToTarget(target) {
    const fromPlayer = (target === 'source') ? resultAudioPlayer : sourceAudioPlayer;
    const toPlayer = (target === 'source') ? sourceAudioPlayer : resultAudioPlayer;
    const wasPlaying = !fromPlayer.paused;
    const curTime = fromPlayer.currentTime;

    activePlayingTarget = target;
    updateABUI(target);

    // Micro volume ramp-down to prevent any digital clicking
    const rampSteps = 4;
    let step = 0;
    const origVol = currentVolume;
    const rampDownInterval = setInterval(() => {
      step++;
      const ratio = Math.max(0, 1 - (step / rampSteps));
      fromPlayer.volume = origVol * ratio;
      if (step >= rampSteps) {
        clearInterval(rampDownInterval);
        fromPlayer.pause();
        fromPlayer.volume = origVol;
        if (fromPlayer === resultAudioPlayer) resetResultPlayState();
        else {
          if (srcPlayIcon) srcPlayIcon.innerHTML = SVG_PLAY;
          if (srcPlayText) srcPlayText.textContent = 'Play Source';
        }

        // Align playback position
        const targetDur = toPlayer.duration || curTime;
        toPlayer.currentTime = Math.min(curTime, targetDur);
        toPlayer.playbackRate = currentPlaybackRate;

        if (wasPlaying) {
          toPlayer.volume = 0;
          toPlayer.play().then(() => {
            updatePlayIcons(true, target);
            startPlayheadRAF();
            let upStep = 0;
            const rampUpInterval = setInterval(() => {
              upStep++;
              toPlayer.volume = origVol * (upStep / rampSteps);
              if (upStep >= rampSteps) {
                clearInterval(rampUpInterval);
                toPlayer.volume = origVol;
              }
            }, 5);
          }).catch(() => {});
        }
      }
    }, 5);

    showToast(target === 'source' ? 'Switched to [A] Raw Source Noise' : 'Switched to [B] Produced Track', 'info', 'A/B STUDIO COMPARE');
  }

  if (btnABSwitch) {
    btnABSwitch.addEventListener('click', toggleABComparison);
  }

  // Quick Solo & Blend Preset Buttons
  if (btnSoloA) {
    btnSoloA.addEventListener('click', () => {
      if (abBalanceSlider) abBalanceSlider.value = 0;
      balanceValue = 0;
      applyBalance(0);
    });
  }

  if (btnPresetA) {
    btnPresetA.addEventListener('click', () => {
      if (abBalanceSlider) abBalanceSlider.value = 0;
      balanceValue = 0;
      applyBalance(0);
    });
  }

  if (btnPresetBlend) {
    btnPresetBlend.addEventListener('click', () => {
      if (abBalanceSlider) abBalanceSlider.value = 50;
      balanceValue = 50;
      applyBalance(50);
    });
  }

  if (btnSoloB) {
    btnSoloB.addEventListener('click', () => {
      if (abBalanceSlider) abBalanceSlider.value = 100;
      balanceValue = 100;
      applyBalance(100);
    });
  }

  if (btnPresetB) {
    btnPresetB.addEventListener('click', () => {
      if (abBalanceSlider) abBalanceSlider.value = 100;
      balanceValue = 100;
      applyBalance(100);
    });
  }

  // Real-Time Sound Balance Slider (Blends between Source and Mastered Track)
  if (abBalanceSlider) {
    abBalanceSlider.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      balanceValue = val;
      applyBalance(val);
    });
  }

  function applyBalance(val) {
    const srcGain = currentVolume * (1 - (val / 100));
    const resGain = currentVolume * (val / 100);
    sourceAudioPlayer.volume = srcGain;
    resultAudioPlayer.volume = resGain;

    updateFaderButtonsState(val);

    if (faderBlendLabel) {
      if (val === 0) faderBlendLabel.textContent = '100% Raw [A]';
      else if (val === 100) faderBlendLabel.textContent = '100% Master [B]';
      else if (val === 50) faderBlendLabel.textContent = '50% / 50% Blend';
      else faderBlendLabel.textContent = `${100 - val}% [A] / ${val}% [B]`;
    }

    // If both volumes are active (> 0), synchronize both players in parallel
    if (val > 0 && val < 100) {
      if (abActiveChip) abActiveChip.textContent = `Active: Dual Blend (${100 - val}% [A] / ${val}% [B])`;
      if (abSwitchIndicator) abSwitchIndicator.textContent = `Playing: Dual Blend (${100 - val}% / ${val}%)`;
      if (btnABSwitch) btnABSwitch.className = 'btn-ab-switch';

      if (!sourceAudioPlayer.paused && resultAudioPlayer.paused) {
        resultAudioPlayer.currentTime = sourceAudioPlayer.currentTime;
        resultAudioPlayer.play().catch(() => {});
      } else if (!resultAudioPlayer.paused && sourceAudioPlayer.paused) {
        sourceAudioPlayer.currentTime = resultAudioPlayer.currentTime;
        sourceAudioPlayer.play().catch(() => {});
      }
    } else if (val === 0) {
      activePlayingTarget = 'source';
      updateABUI('source');
      if (!resultAudioPlayer.paused) resultAudioPlayer.pause();
    } else if (val === 100) {
      activePlayingTarget = 'result';
      updateABUI('result');
      if (!sourceAudioPlayer.paused) sourceAudioPlayer.pause();
    }
  }

  // Keyboard shortcut: Spacebar toggles A/B when in results mode and not typing
  window.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'SELECT' && e.target.tagName !== 'TEXTAREA') {
      if (resultsDisplay && !resultsDisplay.classList.contains('hidden') && sourceAudioPlayer.src && resultAudioPlayer.src) {
        e.preventDefault();
        toggleABComparison();
      }
    }
  });

  function toggleSourcePlayback() {
    activePlayingTarget = 'source';
    updateABUI('source');
    if (sourceAudioPlayer.paused) {
      resultAudioPlayer.pause();
      resetResultPlayState();
      sourceAudioPlayer.playbackRate = currentPlaybackRate;
      sourceAudioPlayer.play().catch(() => {});
      updatePlayIcons(true, 'source');
      startPlayheadRAF();
    } else {
      sourceAudioPlayer.pause();
      updatePlayIcons(false, 'source');
    }
  }

  function toggleResultPlayback() {
    activePlayingTarget = 'result';
    updateABUI('result');
    if (resultAudioPlayer.paused) {
      sourceAudioPlayer.pause();
      if (srcPlayIcon) srcPlayIcon.innerHTML = SVG_PLAY;
      if (srcPlayText) srcPlayText.textContent = 'Play Source';

      resultAudioPlayer.playbackRate = currentPlaybackRate;
      resultAudioPlayer.play().catch(() => {});
      updatePlayIcons(true, 'result');
      startPlayheadRAF();
    } else {
      resultAudioPlayer.pause();
      updatePlayIcons(false, 'result');
    }
  }

  function updatePlayIcons(isPlaying, target) {
    if (isPlaying) {
      if (target === 'result') {
        if (resPlayIcon) resPlayIcon.innerHTML = SVG_PAUSE;
        if (resPlayText) resPlayText.textContent = 'Pause Composition';
      } else {
        if (srcPlayIcon) srcPlayIcon.innerHTML = SVG_PAUSE;
        if (srcPlayText) srcPlayText.textContent = 'Pause Source';
      }
      if (playerPlaySvg) {
        playerPlaySvg.innerHTML = '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>';
      }
    } else {
      if (target === 'result') {
        if (resPlayIcon) resPlayIcon.innerHTML = SVG_PLAY;
        if (resPlayText) resPlayText.textContent = 'Play Composition';
      } else {
        if (srcPlayIcon) srcPlayIcon.innerHTML = SVG_PLAY;
        if (srcPlayText) srcPlayText.textContent = 'Play Source';
      }
      if (playerPlaySvg) {
        playerPlaySvg.innerHTML = '<polygon points="8 5 19 12 8 19 8 5"/>';
      }
    }
  }

  // Playback Speed Cycling Control (0.75x, 1x, 1.25x, 1.5x, 2x)
  function cyclePlaybackSpeed() {
    const curIdx = PLAYBACK_SPEEDS.indexOf(currentPlaybackRate);
    const nextIdx = (curIdx + 1) % PLAYBACK_SPEEDS.length;
    currentPlaybackRate = PLAYBACK_SPEEDS[nextIdx];

    sourceAudioPlayer.playbackRate = currentPlaybackRate;
    resultAudioPlayer.playbackRate = currentPlaybackRate;

    const label = `${currentPlaybackRate}x`;
    if (playerBtnSpeed) playerBtnSpeed.textContent = label;
    if (btnSpeedSource) btnSpeedSource.textContent = label;
    if (btnSpeedResult) btnSpeedResult.textContent = label;

    showToast(`Playback speed: ${label}`, 'info', 'SPEED');
  }

  [playerBtnSpeed, btnSpeedSource, btnSpeedResult].forEach(btn => {
    if (btn) btn.addEventListener('click', cyclePlaybackSpeed);
  });

  // Relative Time Skipping (-5s / +5s)
  function skipTime(deltaSeconds) {
    const p = getActiveAudioPlayer();
    const cur = p.currentTime || 0;
    const dur = p.duration || 60;
    const target = Math.max(0, Math.min(dur, cur + deltaSeconds));
    p.currentTime = target;

    // Sync other player if both are active in balance mode
    if (balanceValue > 0 && balanceValue < 100) {
      const other = (p === sourceAudioPlayer) ? resultAudioPlayer : sourceAudioPlayer;
      other.currentTime = target;
    }

    updatePlayheadRAF();
    showToast(`${deltaSeconds > 0 ? '+' : ''}${deltaSeconds}s`, 'info', 'SEEK');
  }

  if (playerBtnSkipBack) playerBtnSkipBack.addEventListener('click', () => skipTime(-5));
  if (playerBtnSkipFwd) playerBtnSkipFwd.addEventListener('click', () => skipTime(5));
  if (btnSkipBackSource) btnSkipBackSource.addEventListener('click', () => skipTime(-5));
  if (btnSkipFwdSource) btnSkipFwdSource.addEventListener('click', () => skipTime(5));
  if (btnSkipBackResult) btnSkipBackResult.addEventListener('click', () => skipTime(-5));
  if (btnSkipFwdResult) btnSkipFwdResult.addEventListener('click', () => skipTime(5));

  // Audio Ended Listeners
  sourceAudioPlayer.addEventListener('ended', () => {
    if (srcPlayIcon) srcPlayIcon.innerHTML = SVG_PLAY;
    if (srcPlayText) srcPlayText.textContent = 'Play Source';
    if (srcPlayhead) srcPlayhead.style.left = '0%';
    updatePlayIcons(false, 'source');
    stopPlayheadRAF();
  });

  resultAudioPlayer.addEventListener('ended', () => {
    resetResultPlayState();
    if (isLooping) {
      resultAudioPlayer.currentTime = 0;
      resultAudioPlayer.play().catch(() => {});
      updatePlayIcons(true, 'result');
      startPlayheadRAF();
    } else {
      stopPlayheadRAF();
    }
  });

  function resetResultPlayState() {
    if (resPlayIcon) resPlayIcon.innerHTML = SVG_PLAY;
    if (resPlayText) resPlayText.textContent = 'Play Composition';
    if (resPlayhead) resPlayhead.style.left = '0%';
    if (playerPlaySvg) {
      playerPlaySvg.innerHTML = '<polygon points="8 5 19 12 8 19 8 5"/>';
    }
    if (playerSliderFill) playerSliderFill.style.width = '0%';
    if (playerSliderThumb) playerSliderThumb.style.left = '0%';
  }

  // Waveform Click-to-Scrub Seeking
  if (srcCanvasWrapper) {
    srcCanvasWrapper.addEventListener('click', (e) => {
      const rect = srcCanvasWrapper.getBoundingClientRect();
      const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      if (sourceAudioPlayer.duration) {
        sourceAudioPlayer.currentTime = pos * sourceAudioPlayer.duration;
        updatePlayheadRAF();
      }
    });
  }

  if (resCanvasWrapper) {
    resCanvasWrapper.addEventListener('click', (e) => {
      const rect = resCanvasWrapper.getBoundingClientRect();
      const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      if (resultAudioPlayer.duration) {
        resultAudioPlayer.currentTime = pos * resultAudioPlayer.duration;
        updatePlayheadRAF();
      }
    });
  }

  // Pointer Drag-to-Scrub on Player Progress Bar (Glitch-Free & Pop-Free)
  if (playerSliderTrack) {
    let pendingScrubPos = 0;

    const updateScrubVisuals = (pos) => {
      const pct = Math.max(0, Math.min(100, pos * 100));
      const pctStr = `${pct.toFixed(2)}%`;
      if (playerSliderFill) playerSliderFill.style.width = pctStr;
      if (playerSliderThumb) playerSliderThumb.style.left = pctStr;
      if (activePlayingTarget === 'result' && resPlayhead) resPlayhead.style.left = pctStr;
      if (activePlayingTarget === 'source' && srcPlayhead) srcPlayhead.style.left = pctStr;

      const p = getActiveAudioPlayer();
      const dur = (p.duration && !isNaN(p.duration)) ? p.duration : selectedDuration;
      const previewTime = pos * dur;
      const curStr = formatTime(previewTime);
      if (playerCurrentTime && curStr !== lastFormattedCur) {
        lastFormattedCur = curStr;
        playerCurrentTime.textContent = curStr;
      }
    };

    const commitScrubSeek = (pos) => {
      const p = getActiveAudioPlayer();
      if (p.duration && !isNaN(p.duration)) {
        const targetTime = Math.max(0, Math.min(p.duration, pos * p.duration));
        p.currentTime = targetTime;
        lastAudioTime = targetTime;
        lastSyncTimestamp = performance.now();
        if (balanceValue > 0 && balanceValue < 100) {
          const other = (p === sourceAudioPlayer) ? resultAudioPlayer : sourceAudioPlayer;
          other.currentTime = targetTime;
        }
      }
      updatePlayheadRAF();
    };

    playerSliderTrack.addEventListener('pointerdown', (e) => {
      isScrubbing = true;
      try { playerSliderTrack.setPointerCapture(e.pointerId); } catch (err) {}
      const rect = playerSliderTrack.getBoundingClientRect();
      pendingScrubPos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      updateScrubVisuals(pendingScrubPos);
    });

    playerSliderTrack.addEventListener('pointermove', (e) => {
      if (isScrubbing) {
        const rect = playerSliderTrack.getBoundingClientRect();
        pendingScrubPos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
        updateScrubVisuals(pendingScrubPos);
      }
    });

    playerSliderTrack.addEventListener('pointerup', (e) => {
      if (isScrubbing) {
        isScrubbing = false;
        try { playerSliderTrack.releasePointerCapture(e.pointerId); } catch (err) {}
        commitScrubSeek(pendingScrubPos);
      }
    });

    playerSliderTrack.addEventListener('pointercancel', (e) => {
      if (isScrubbing) {
        isScrubbing = false;
        try { playerSliderTrack.releasePointerCapture(e.pointerId); } catch (err) {}
        commitScrubSeek(pendingScrubPos);
      }
    });
  }

  // Bottom Player Next / Previous Controls
  if (playerBtnNext) {
    playerBtnNext.addEventListener('click', () => {
      if (currentResultData && currentResultData.candidates.length > 0) {
        const nextIdx = (activeCandidateIndex + 1) % currentResultData.candidates.length;
        selectCandidate(nextIdx);
        toggleResultPlayback();
      }
    });
  }

  if (playerBtnPrev) {
    playerBtnPrev.addEventListener('click', () => {
      if (activePlayingTarget === 'result' && sourceAudioPlayer.src) {
        toggleSourcePlayback();
      } else if (currentResultData && currentResultData.candidates.length > 0) {
        const prevIdx = (activeCandidateIndex - 1 + currentResultData.candidates.length) % currentResultData.candidates.length;
        selectCandidate(prevIdx);
        toggleResultPlayback();
      }
    });
  }

  if (playerBtnShuffle) {
    playerBtnShuffle.addEventListener('click', () => {
      if (currentResultData && currentResultData.candidates.length > 0) {
        const randIdx = Math.floor(Math.random() * currentResultData.candidates.length);
        selectCandidate(randIdx);
        showToast(`Switched to Candidate ${String.fromCharCode(65 + randIdx)}`, 'info');
      }
    });
  }

  if (playerBtnLoop) {
    playerBtnLoop.addEventListener('click', () => {
      isLooping = !isLooping;
      playerBtnLoop.classList.toggle('active', isLooping);
      showToast(isLooping ? 'Looping enabled' : 'Looping disabled', 'info');
    });
  }

  if (btnPlayerFav) {
    btnPlayerFav.addEventListener('click', () => {
      btnPlayerFav.classList.toggle('active');
      const isFav = btnPlayerFav.classList.contains('active');
      showToast(isFav ? 'Added composition to favorites!' : 'Removed from favorites', 'info');
    });
  }

  // Smooth Pointer Drag-to-Adjust Volume
  if (volumeSliderTrack) {
    const handleVolumeSeek = (e) => {
      const rect = volumeSliderTrack.getBoundingClientRect();
      const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      setVolume(pos);
    };

    volumeSliderTrack.addEventListener('pointerdown', (e) => {
      isVolumeDragging = true;
      volumeSliderTrack.setPointerCapture(e.pointerId);
      handleVolumeSeek(e);
    });

    volumeSliderTrack.addEventListener('pointermove', (e) => {
      if (isVolumeDragging) handleVolumeSeek(e);
    });

    volumeSliderTrack.addEventListener('pointerup', (e) => {
      if (isVolumeDragging) {
        isVolumeDragging = false;
        try { volumeSliderTrack.releasePointerCapture(e.pointerId); } catch (err) {}
      }
    });

    volumeSliderTrack.addEventListener('pointercancel', (e) => {
      isVolumeDragging = false;
      try { volumeSliderTrack.releasePointerCapture(e.pointerId); } catch (err) {}
    });
  }

  if (playerBtnVolume) {
    playerBtnVolume.addEventListener('click', () => {
      if (isMuted) {
        setVolume(previousVolume || 0.8);
        isMuted = false;
      } else {
        previousVolume = currentVolume;
        setVolume(0);
        isMuted = true;
      }
    });
  }

  function setVolume(val) {
    currentVolume = val;
    applyBalance(balanceValue);
    if (volumeSliderFill) volumeSliderFill.style.width = `${val * 100}%`;

    if (val === 0) {
      if (volumeSvg) volumeSvg.innerHTML = '<path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/>';
    } else {
      if (volumeSvg) volumeSvg.innerHTML = '<path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>';
    }
  }

  // Right Panel Toggle
  if (playerBtnTogglePanel) {
    playerBtnTogglePanel.addEventListener('click', () => {
      if (spotifyShell) spotifyShell.classList.toggle('right-panel-closed');
    });
  }

  if (btnCloseRightPanel) {
    btnCloseRightPanel.addEventListener('click', () => {
      if (spotifyShell) spotifyShell.classList.add('right-panel-closed');
    });
  }

  if (btnScrollToDNA) {
    btnScrollToDNA.addEventListener('click', () => {
      if (spotifyShell) spotifyShell.classList.remove('right-panel-closed');
      showToast('Acoustic DNA Panel opened on the right!', 'info', 'ACOUSTIC DNA');
    });
  }

  // Library Items Click
  if (libCurrentTrack) {
    libCurrentTrack.addEventListener('click', () => {
      const resSec = document.getElementById('resultsSection');
      if (resSec) resSec.scrollIntoView({ behavior: 'smooth' });
      if (resultAudioPlayer.src) toggleResultPlayback();
    });
  }

  if (libSourceTrack) {
    libSourceTrack.addEventListener('click', () => {
      if (sourceAudioPlayer.src) toggleSourcePlayback();
    });
  }

  // 9. Waveform Canvas Drawing with In-Memory Cache (Zero CPU Decode Stalls)
  const waveformCache = new Map();

  async function drawWaveformFromUrl(url, canvas, color) {
    if (!canvas || !url) return;
    try {
      let channelData = waveformCache.get(url);
      if (!channelData) {
        const response = await fetch(buildUrl(url));
        const arrayBuffer = await response.arrayBuffer();
        const ctx = getDecodeAudioContext();
        const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
        channelData = audioBuffer.getChannelData(0);
        waveformCache.set(url, channelData);
      }
      drawWaveform(channelData, canvas, color);
    } catch (err) {
      console.warn("Waveform decode note:", err);
      drawFallbackWaveform(canvas, color);
    }
  }

  function drawWaveform(samples, canvas, color) {
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = rect.width || (canvas.width / dpr) || 800;
    const height = rect.height || (canvas.height / dpr) || 80;

    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    ctx.scale(dpr, dpr);

    // Clean dark backdrop
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#0a0d12';
    ctx.fillRect(0, 0, width, height);

    // Subtle horizontal guideline
    ctx.fillStyle = 'rgba(255, 255, 255, 0.06)';
    ctx.fillRect(0, Math.floor(height / 2), width, 1);

    const numBars = Math.min(140, Math.max(80, Math.floor(width / 6)));
    const step = Math.floor(samples.length / numBars);
    const barWidth = Math.max(2.5, (width / numBars) * 0.65);
    const spacing = width / numBars;

    // 1. Calculate raw RMS and peak for each bin
    const rawHeights = [];
    for (let i = 0; i < numBars; i++) {
      let sumSq = 0;
      let peak = 0;
      const start = i * step;
      const stepInc = Math.max(1, Math.floor(step / 32));
      let count = 0;
      for (let j = 0; j < step; j += stepInc) {
        const val = Math.abs(samples[start + j] || 0);
        sumSq += val * val;
        if (val > peak) peak = val;
        count++;
      }
      const rms = count > 0 ? Math.sqrt(sumSq / count) : 0;
      // Balanced weighting of RMS body and transient peak
      const combined = (rms * 0.6) + (peak * 0.4);
      rawHeights.push(combined);
    }

    // 2. Smooth envelope filter (3-point moving average) to prevent jagged jumps
    const smoothed = [];
    for (let i = 0; i < numBars; i++) {
      const prev = rawHeights[Math.max(0, i - 1)];
      const curr = rawHeights[i];
      const next = rawHeights[Math.min(numBars - 1, i + 1)];
      smoothed.push((prev * 0.25) + (curr * 0.5) + (next * 0.25));
    }

    // 3. Draw sleek rounded bars with vertical gradient
    const isSource = (color && color.includes('38bdf8')) || color === '#38bdf8';
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    if (isSource) {
      grad.addColorStop(0, '#38bdf8');
      grad.addColorStop(1, '#0284c7');
    } else {
      grad.addColorStop(0, '#1ed760');
      grad.addColorStop(1, '#059669');
    }
    ctx.fillStyle = grad;

    for (let i = 0; i < numBars; i++) {
      const norm = Math.min(1, Math.pow(smoothed[i], 0.75) * 1.8);
      const barH = Math.max(4, Math.floor(norm * (height * 0.86)));
      const x = Math.floor(i * spacing);
      const y = Math.floor((height - barH) / 2);

      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, barH, 2);
      ctx.fill();
    }
  }

  function drawFallbackWaveform(canvas, color) {
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = rect.width || 800;
    const height = rect.height || 80;

    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#0a0d12';
    ctx.fillRect(0, 0, width, height);

    ctx.fillStyle = color || '#1ed760';

    const numBars = 100;
    const barWidth = 3;
    const spacing = width / numBars;

    for (let i = 0; i < numBars; i++) {
      const barH = 8 + Math.sin(i * 0.12) * (height * 0.32);
      const x = Math.floor(i * spacing);
      const y = Math.floor((height - barH) / 2);
      ctx.beginPath();
      ctx.roundRect(x, y, barWidth, barH, 2);
      ctx.fill();
    }
  }

  function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '00:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }

  // 10. Startup Session Restoration (Auto-reconnects ONLY if a job is actively processing)
  try {
    const savedJobId = sessionStorage.getItem('unnecessary_fm_active_job');
    if (savedJobId) {
      fetch(buildUrl(`/api/status/${savedJobId}`))
        .then(res => {
          if (!res.ok) throw new Error("Job not found");
          return res.json();
        })
        .then(statusData => {
          if (statusData.status === 'processing' || statusData.status === 'queued') {
            currentJobId = savedJobId;
            showProcessingState(statusData.stage || 'Processing DSP audio...');
            trackJobProgress(savedJobId);
          } else {
            // Already completed or failed — clear session so fresh visits remain clean
            sessionStorage.removeItem('unnecessary_fm_active_job');
          }
        })
        .catch(() => {
          sessionStorage.removeItem('unnecessary_fm_active_job');
        });
    }
  } catch (e) {}

})();

