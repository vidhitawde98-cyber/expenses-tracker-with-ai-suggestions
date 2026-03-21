document.addEventListener("DOMContentLoaded", function () {

    // ===== DARK MODE =====
    const darkModeToggle = document.getElementById("darkModeToggle");
    const body = document.body;

    if (localStorage.getItem("darkMode") === "enabled") {
        body.classList.add("dark-mode");
        if (darkModeToggle) darkModeToggle.innerText = "☀️ Light Mode";
    } else {
        if (darkModeToggle) darkModeToggle.innerText = "🌙 Dark Mode";
    }

    if (darkModeToggle) {
        darkModeToggle.addEventListener("click", function () {
            body.classList.toggle("dark-mode");
            if (body.classList.contains("dark-mode")) {
                localStorage.setItem("darkMode", "enabled");
                darkModeToggle.innerText = "☀️ Light Mode";
            } else {
                localStorage.setItem("darkMode", "disabled");
                darkModeToggle.innerText = "🌙 Dark Mode";
            }
        });
    }

    // ===== AUTO-DISMISS FLASH MESSAGES =====
    setTimeout(function () {
        const flashMessages = document.querySelectorAll('.alert-dismissible');
        flashMessages.forEach(function (alert) {
            try {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            } catch (e) {}
        });
    }, 5000);

    // ===== EYE ICON FOR ALL PASSWORD FIELDS =====
    const passwordFields = document.querySelectorAll('input[type="password"]');

    passwordFields.forEach(function (input) {
        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'position: relative; display: block;';

        // Insert wrapper before input
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        // Create eye button
        const eyeBtn = document.createElement('button');
        eyeBtn.type = 'button';
        eyeBtn.innerHTML = '👁️';
        input.style.paddingRight = '44px';
        eyeBtn.style.cssText = `
            position: absolute;
            right: 10px;
            top: 0;
            bottom: 0;
            height: 100%;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 18px;
            padding: 0 4px;
            line-height: 1;
            z-index: 10;
            display: flex;
            align-items: center;
            justify-content: center;
         `;
        
        wrapper.appendChild(eyeBtn);

        // Toggle on click
        eyeBtn.addEventListener('click', function () {
            if (input.type === 'password') {
                input.type = 'text';
                eyeBtn.innerHTML = '🙈';
            } else {
                input.type = 'password';
                eyeBtn.innerHTML = '👁️';
            }
        });
    });
// ===== ACCESSIBILITY PANEL =====
    const accToggle = document.getElementById('accessibilityToggle');
    const accPanel = document.getElementById('accessibilityPanel');
    const accClose = document.getElementById('accessibilityClose');
    const accOverlay = document.getElementById('accessibilityOverlay');

    if (accToggle && accPanel) {

        // Open / close
        accToggle.addEventListener('click', function () {
            accPanel.style.display = accPanel.style.display === 'none' ? 'block' : 'none';
        });
        if (accClose) accClose.addEventListener('click', () => accPanel.style.display = 'none');
        if (accOverlay) accOverlay.addEventListener('click', () => accPanel.style.display = 'none');

        // --- Feature toggle buttons ---
        const featureMap = {
            highContrast:      'acc-high-contrast',
            grayscale:         'acc-grayscale',
            darkHighContrast:  'acc-dark-contrast',
            lightBackground:   'acc-light-bg',
            hideImages:        'acc-hide-images',
            bigCursor:         'acc-big-cursor',
            dyslexiaFont:      'acc-dyslexia-font',
            readableFont:      'acc-readable-font',
            highlightLinks:    'acc-highlight-links',
            highlightHeaders:  'acc-highlight-headers',
            focusMode:         'acc-focus-mode',
            pauseAnimations:   'acc-pause-animations',
            keyboardNav:       'acc-keyboard-nav',
            focusHighlight:    'acc-focus-highlight',
        };

        // Load saved features
        Object.entries(featureMap).forEach(([feature, cls]) => {
            if (localStorage.getItem('acc_' + feature) === 'on') {
                document.body.classList.add(cls);
                const btn = document.querySelector('[data-feature="' + feature + '"]');
                if (btn) btn.classList.add('active');
            }
        });

        document.querySelectorAll('.acc-btn[data-feature]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                const feature = this.dataset.feature;
                const cls = featureMap[feature];
                if (!cls) return;
                const isOn = document.body.classList.toggle(cls);
                this.classList.toggle('active', isOn);
                localStorage.setItem('acc_' + feature, isOn ? 'on' : 'off');
            });
        });

        // --- Font size ---
        let fontSize = parseInt(localStorage.getItem('acc_fontSize') || '100');
        function applyFontSize() {
            document.documentElement.style.fontSize = fontSize + '%';
            document.getElementById('fontSizeLabel').textContent = fontSize + '%';
            localStorage.setItem('acc_fontSize', fontSize);
        }
        applyFontSize();
        document.getElementById('fontIncrease').addEventListener('click', () => { if (fontSize < 150) { fontSize += 10; applyFontSize(); } });
        document.getElementById('fontDecrease').addEventListener('click', () => { if (fontSize > 70) { fontSize -= 10; applyFontSize(); } });
        document.getElementById('fontReset').addEventListener('click', () => { fontSize = 100; applyFontSize(); });

        // --- Line height ---
        const lineSteps = ['normal', '1.5', '1.8', '2.2', '2.8'];
        let lineIdx = parseInt(localStorage.getItem('acc_lineIdx') || '0');
        function applyLineHeight() {
            document.body.style.lineHeight = lineSteps[lineIdx];
            document.getElementById('lineSizeLabel').textContent = lineSteps[lineIdx];
            localStorage.setItem('acc_lineIdx', lineIdx);
        }
        applyLineHeight();
        document.getElementById('lineIncrease').addEventListener('click', () => { if (lineIdx < lineSteps.length - 1) { lineIdx++; applyLineHeight(); } });
        document.getElementById('lineDecrease').addEventListener('click', () => { if (lineIdx > 0) { lineIdx--; applyLineHeight(); } });

        // --- Letter spacing ---
        const letterSteps = ['normal', '0.05em', '0.1em', '0.15em', '0.2em'];
        let letterIdx = parseInt(localStorage.getItem('acc_letterIdx') || '0');
        function applyLetterSpacing() {
            document.body.style.letterSpacing = letterSteps[letterIdx];
            document.getElementById('letterSizeLabel').textContent = letterSteps[letterIdx];
            localStorage.setItem('acc_letterIdx', letterIdx);
        }
        applyLetterSpacing();
        document.getElementById('letterIncrease').addEventListener('click', () => { if (letterIdx < letterSteps.length - 1) { letterIdx++; applyLetterSpacing(); } });
        document.getElementById('letterDecrease').addEventListener('click', () => { if (letterIdx > 0) { letterIdx--; applyLetterSpacing(); } });

        // --- Reading Guide ---
        const guideLine = document.getElementById('readingGuideLine');
        let readingGuideOn = localStorage.getItem('acc_readingGuide') === 'on';
        function toggleReadingGuide(on) {
            readingGuideOn = on;
            guideLine.style.display = on ? 'block' : 'none';
            localStorage.setItem('acc_readingGuide', on ? 'on' : 'off');
            const btn = document.querySelector('[data-feature="readingGuide"]');
            if (btn) btn.classList.toggle('active', on);
        }
        toggleReadingGuide(readingGuideOn);
        document.addEventListener('mousemove', (e) => {
            if (readingGuideOn) guideLine.style.top = e.clientY + 'px';
        });
        document.querySelector('[data-feature="readingGuide"]').addEventListener('click', function () {
            toggleReadingGuide(!readingGuideOn);
        });

        // --- Mute Sounds (stops HTML5 audio/video) ---
        document.querySelector('[data-feature="muteSounds"]').addEventListener('click', function () {
            const isActive = this.classList.toggle('active');
            document.querySelectorAll('audio, video').forEach(el => el.muted = isActive);
            localStorage.setItem('acc_muteSounds', isActive ? 'on' : 'off');
        });
        if (localStorage.getItem('acc_muteSounds') === 'on') {
            document.querySelectorAll('audio, video').forEach(el => el.muted = true);
            const btn = document.querySelector('[data-feature="muteSounds"]');
            if (btn) btn.classList.add('active');
        }

        // --- Text to Speech ---
        const synth = window.speechSynthesis;
        let ttsRate = 1;
        let ttsVoice = null;
        const ttsStatus = document.getElementById('ttsStatus');
        const ttsSpeedLabel = document.getElementById('ttsSpeedLabel');
        const ttsVoiceSelect = document.getElementById('ttsVoiceSelect');

        // Load available voices into dropdown
        function loadVoices() {
            const voices = synth.getVoices();
            if (!ttsVoiceSelect) return;
            ttsVoiceSelect.innerHTML = '';
            voices.forEach(function(voice, i) {
                const opt = document.createElement('option');
                opt.value = i;
                opt.textContent = voice.name + ' (' + voice.lang + ')';
                ttsVoiceSelect.appendChild(opt);
            });
            // Default to first English voice
            const engIdx = voices.findIndex(v => v.lang.startsWith('en'));
            if (engIdx >= 0) ttsVoiceSelect.value = engIdx;
        }

        if (synth) {
            loadVoices();
            if (synth.onvoiceschanged !== undefined) {
                synth.onvoiceschanged = loadVoices;
            }
        }

        // Read full page
        document.getElementById('ttsReadPage').addEventListener('click', function () {
            if (!synth) { alert('Sorry, your browser does not support text-to-speech.'); return; }
            synth.cancel();

            // Get all visible text from main content
            const mainContent = document.querySelector('main#mainContent') || document.querySelector('.container.mt-4') || document.body;
            const text = mainContent.innerText || mainContent.textContent;
            if (!text.trim()) return;

            // Split into chunks (browsers have a limit per utterance)
            const chunkSize = 200;
            const words = text.split(' ');
            const chunks = [];
            let current = '';
            words.forEach(word => {
                if ((current + ' ' + word).length > chunkSize) {
                    chunks.push(current.trim());
                    current = word;
                } else {
                    current += ' ' + word;
                }
            });
            if (current.trim()) chunks.push(current.trim());

            let chunkIndex = 0;
            if (ttsStatus) ttsStatus.textContent = '🔊 Reading...';

            function speakNext() {
                if (chunkIndex >= chunks.length) {
                    if (ttsStatus) ttsStatus.textContent = '✅ Done reading';
                    return;
                }
                const utter = new SpeechSynthesisUtterance(chunks[chunkIndex]);
                utter.rate = ttsRate;
                const voices = synth.getVoices();
                if (ttsVoiceSelect && voices[ttsVoiceSelect.value]) {
                    utter.voice = voices[ttsVoiceSelect.value];
                }
                utter.onend = function() {
                    chunkIndex++;
                    speakNext();
                };
                utter.onerror = function() {
                    chunkIndex++;
                    speakNext();
                };
                synth.speak(utter);
            }
            speakNext();
        });

        // Stop reading
        document.getElementById('ttsStop').addEventListener('click', function () {
            if (synth) {
                synth.cancel();
                if (ttsStatus) ttsStatus.textContent = '⏹️ Stopped';
            }
        });

        // Speed controls
        const ttsRates = [0.5, 0.75, 1, 1.25, 1.5, 2];
        let ttsRateIdx = 2;
        document.getElementById('ttsFaster').addEventListener('click', function () {
            if (ttsRateIdx < ttsRates.length - 1) {
                ttsRateIdx++;
                ttsRate = ttsRates[ttsRateIdx];
                if (ttsSpeedLabel) ttsSpeedLabel.textContent = ttsRate + 'x';
            }
        });
        document.getElementById('ttsSlower').addEventListener('click', function () {
            if (ttsRateIdx > 0) {
                ttsRateIdx--;
                ttsRate = ttsRates[ttsRateIdx];
                if (ttsSpeedLabel) ttsSpeedLabel.textContent = ttsRate + 'x';
            }
        });




        // --- Reset All ---
        document.getElementById('resetAllAccessibility').addEventListener('click', function () {
            Object.entries(featureMap).forEach(([feature, cls]) => {
                document.body.classList.remove(cls);
                localStorage.removeItem('acc_' + feature);
                const btn = document.querySelector('[data-feature="' + feature + '"]');
                if (btn) btn.classList.remove('active');
            });
            fontSize = 100; applyFontSize();
            lineIdx = 0; applyLineHeight();
            letterIdx = 0; applyLetterSpacing();
            toggleReadingGuide(false);
            document.documentElement.style.fontSize = '';
            document.body.style.lineHeight = '';
            document.body.style.letterSpacing = '';
            ['acc_fontSize','acc_lineIdx','acc_letterIdx','acc_readingGuide','acc_muteSounds'].forEach(k => localStorage.removeItem(k));
        });

    }


});