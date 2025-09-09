<script>
        import { onMount } from 'svelte';
        // API configuration
        const API_BASE_URL = 'http://localhost:8000';
        
        // Game state
        let sessionId = null;
        let currentQuestion = null;
        let score = 100;
        let questionsAnswered = 0;
        let gameStarted = false;
        let loading = false;
        let error = null;

        // Start modal and song selection
        let showStartModal = false;
        let songsList = [];
        let selectedSongTitle = '';
        let selectedDifficulty = '';

        // Hint/lives
        let lives = 3;
        let showHintConfirm = false;
        let hintRevealed = false;

        // Background audio
        let bgAudio = null;
        const INSTRUMENTAL_URL = new URL('./assets/audio/instrumental.mp3', import.meta.url).href;
        let audioPlayPending = false;
        let isMuted = false;
        const AUDIO_SINGLETON_KEY = '__bgAudioInstance';
        let nextAudioUrl = null;
        const AUDIO_REGISTRY_KEY = '__allBgAudios';

        function registerAudioInstance(instance) {
            if (typeof window === 'undefined') return;
            const list = (window[AUDIO_REGISTRY_KEY] ||= []);
            if (!list.includes(instance)) list.push(instance);
        }

        function ensureUniqueAudioPlayback() {
            if (typeof window === 'undefined') return;
            const list = window[AUDIO_REGISTRY_KEY] || [];
            for (const a of list) {
                if (a && a !== bgAudio) {
                    try { a.pause(); } catch {}
                    try { a.currentTime = 0; } catch {}
                }
            }
        }

        function initAudio() {
            // Reuse a single global instance to avoid duplicates across re-mounts/HMR
            const existing = typeof window !== 'undefined' ? window[AUDIO_SINGLETON_KEY] : null;
            if (existing instanceof Audio) {
                bgAudio = existing;
                bgAudio.muted = isMuted;
                registerAudioInstance(bgAudio);
                return;
            }
            bgAudio = new Audio(INSTRUMENTAL_URL);
            bgAudio.loop = true;
            bgAudio.volume = 0.25;
            bgAudio.preload = 'auto';
            bgAudio.muted = isMuted;
            if (typeof window !== 'undefined') {
                window[AUDIO_SINGLETON_KEY] = bgAudio;
            }
            registerAudioInstance(bgAudio);
            // If a follow-up track is queued, switch only after current ends
            bgAudio.addEventListener('ended', () => {
                if (nextAudioUrl) {
                    bgAudio.src = nextAudioUrl;
                    nextAudioUrl = null;
                    try { bgAudio.play().catch(() => {}); } catch {}
                }
            });
        }

        function startAudioAutoplay() {
            try {
                initAudio();
                ensureUniqueAudioPlayback();
                const p = bgAudio.play();
                if (p && typeof p.then === 'function') {
                    p.catch(() => {
                        if (!audioPlayPending) {
                            audioPlayPending = true;
                            const resume = () => {
                                initAudio();
                                ensureUniqueAudioPlayback();
                                bgAudio.play().catch(() => {});
                                audioPlayPending = false;
                            };
                            window.addEventListener('pointerdown', resume, { once: true });
                            window.addEventListener('keydown', resume, { once: true });
                        }
                    });
                }
            } catch {}
        }

        function toggleMute() {
            initAudio();
            isMuted = !isMuted;
            bgAudio.muted = isMuted;
            if (isMuted) {
                // For robustness, also set volume to 0 and pause
                try { bgAudio.volume = 0; } catch {}
                try { bgAudio.pause(); } catch {}
            } else {
                // Restore volume and ensure playback resumes
                try { bgAudio.volume = 0.25; } catch {}
                if (bgAudio.paused) {
                    try {
                        ensureUniqueAudioPlayback();
                        bgAudio.play().catch(() => {});
                    } catch {}
                }
            }
            updateUI();
        }

        // Optional API to change instrumental source without overlap
        function queueInstrumental(url) {
            initAudio();
            if (!url) return;
            const newUrl = new URL(url, import.meta.url).href;
            if (bgAudio.ended || bgAudio.paused) {
                bgAudio.src = newUrl;
                try { bgAudio.play().catch(() => {}); } catch {}
            } else if (bgAudio.currentSrc !== newUrl) {
                nextAudioUrl = newUrl;
            }
        }

        // Game elements
        let promptBase = "Loading...";
        let correctAnswer = "";
        let options = [];
        let optionColors = {};
        let selectedIndex = 0;
        let selectedWord = '';
        let showWrong = false;
        let showRight = false;
        let filled = false;

        // Canvas elements
        let canvas, gameArea, ctx;
        let width = 0, height = 0, dpr = 1;

        // Game constants
        const bubbleRadius = 22;
        const bubbleSpeed = 15;
        let shooterX = 0, shooterY = 0;
        let aimAngle = Math.PI / 2;
        const MAX_QUESTIONS = 10;

        // Game objects
        let topRect = { x: 0, y: 0, w: 0, h: 0, r: 16 };
        let shot = null;
        let raf = 0;
        let showFinal = false;

        // Utility functions
        function clamp(val, min, max) {
            return Math.max(min, Math.min(max, val));
        }

        // API functions
        async function createGameSession() {
            try {
                loading = true;
                error = null;
                updateUI();
                
                const response = await fetch(`${API_BASE_URL}/session`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to create session: ${response.statusText}`);
                }
                
                const data = await response.json();
                sessionId = data.session_id;
                gameStarted = true;
                score = 100;
                questionsAnswered = 0;
                lives = 3;
                hintRevealed = false;
                
                await getNewQuestion();
                
            } catch (err) {
                error = err.message;
                console.error('Error creating session:', err);
            } finally {
                loading = false;
                updateUI();
            }
        }

        function openStartModal() {
            showStartModal = true;
            // ensure songs are loaded
            if (!songsList.length) {
                fetchSongs();
            }
            if (!selectedDifficulty) {
                selectedDifficulty = 'easy';
            }
            updateUI();
        }

        function cancelStartModal() {
            showStartModal = false;
            updateUI();
        }

        async function confirmStartModal() {
            if (!selectedSongTitle || !selectedDifficulty) {
                error = 'Please select a song and difficulty';
                updateUI();
                return;
            }
            showStartModal = false;
            await createGameSession();
            // ensure background audio is playing
            startAudioAutoplay();
            updateUI();
        }

        function fetchSongs() {
            fetch(`${API_BASE_URL}/songs`)
                .then(r => r.json())
                .then(data => {
                    const list = (data && data.songs) ? data.songs : [];
                    songsList = list;
                    if (!selectedSongTitle && songsList.length) {
                        selectedSongTitle = songsList[0].title;
                    }
                    updateUI();
                })
                .catch(() => {
                    error = 'Unable to load songs. Please restart or update backend.';
                    updateUI();
                });
        }

        function setSelectedSongTitle(val) {
            selectedSongTitle = val || '';
            updateUI();
        }

        function setSelectedDifficulty(val) {
            selectedDifficulty = val || '';
            updateUI();
        }

        async function getNewQuestion() {
            if (!sessionId) return;
            
            try {
                loading = true;
                error = null;
                updateUI();
                
                let url = `${API_BASE_URL}/question/${sessionId}`;
                if (selectedSongTitle && selectedDifficulty) {
                    const params = new URLSearchParams({ song: selectedSongTitle, part: selectedDifficulty });
                    url += `?${params.toString()}`;
                }
                const response = await fetch(url);
                if (!response.ok) throw new Error(`Failed to get question: ${response.statusText}`);
                
                const data = await response.json();
                currentQuestion = data;
                
                promptBase = data.incomplete_lyric;
                correctAnswer = data.correct_answer;
                options = data.options;

                // Generate colors
                const colors = ['#2ecc71','#e74c3c','#9b59b6','#f1c40f','#3498db'];
                optionColors = {};
                options.forEach((opt, i) => {
                    optionColors[opt] = colors[i % colors.length];
                });

                // Reset game state
                selectedIndex = 0;
                selectedWord = options[0];
                showWrong = false;
                showRight = false;
                filled = false;
                shot = null;
                hintRevealed = false;

                computeLayout();
                
            } catch(err) {
                error = err.message;
                console.error(err);
            } finally {
                loading = false;
                updateUI();
            }
        }

        async function checkAnswer(selectedAnswer) {
            if (!sessionId) return;
            
            try {
                const response = await fetch(`${API_BASE_URL}/check-answer`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: sessionId,
                        selected_answer: selectedAnswer
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`Failed to check answer: ${response.statusText}`);
                }
                
                const result = await response.json();
                
                // Update score and questions count from backend response
                score = result.score || score;
                questionsAnswered = result.questions_answered || questionsAnswered;
                
                if (questionsAnswered >= MAX_QUESTIONS) {
                    showRight = false;
                    showWrong = false;
                    filled = true;
                    showFinal = true;
                } else {
                    if (result.correct) {
                        // Correct answer - fill the bubble and show success
                        filled = true;
                        showRight = true;
                        showWrong = false;
                    } else {
                        // Wrong answer - show error modal
                        showWrong = true;
                        showRight = false;
                    }
                }
                
                updateUI();
                return result;
                
            } catch (err) {
                error = err.message;
                console.error('Error checking answer:', err);
                updateUI();
            }
        }

        // Canvas and drawing functions
        function computeLayout() {
            if (!gameArea || !canvas) return;
            
            const rect = gameArea.getBoundingClientRect();
            width = Math.max(400, rect.width);
            height = Math.max(500, rect.height);
            dpr = window.devicePixelRatio || 1;
            
            canvas.width = Math.floor(width * dpr);
            canvas.height = Math.floor(height * dpr);
            canvas.style.width = width + 'px';
            canvas.style.height = height + 'px';
            
            ctx = canvas.getContext('2d');
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

            shooterX = width / 2;
            shooterY = height - bubbleRadius - 40;

            const pad = 20;
            const w = 500;   // make it wider
            const h = 90;   // make it taller
            topRect = { x: (width - w) / 2, y: 20, w, h, r: 16 };

        }

        function drawRoundedRectPath(x, y, w, h, r) {
            const rr = Math.min(r, h / 2, w / 2);
            ctx.beginPath();
            ctx.moveTo(x + rr, y);
            ctx.lineTo(x + w - rr, y);
            ctx.arcTo(x + w, y, x + w, y + rr, rr);
            ctx.lineTo(x + w, y + h - rr);
            ctx.arcTo(x + w, y + h, x + w - rr, y + h, rr);
            ctx.lineTo(x + rr, y + h);
            ctx.arcTo(x, y + h, x, y + h - rr, rr);
            ctx.lineTo(x, y + rr);
            ctx.arcTo(x, y, x + rr, y, rr);
        }

        function drawTopLyricBubble() {
            const { x, y, w, h, r } = topRect;
            
            ctx.save();
            drawRoundedRectPath(x, y, w, h, r);

            // Top bubble gradient with white highlight at upper-left
            const topBubbleColor = '#8e24aa';
            const grd = ctx.createRadialGradient(
                x + w * 0.15, // moved more left (was 0.3)
                y + h * 0.3,  // same vertical position
                Math.min(w, h) * 0.1,  // inner radius stays the same
                x + w / 2,
                y + h / 2,
                Math.max(w, h) * 0.6   // outer radius stays the same
            );

            grd.addColorStop(0, '#ffffff');      
            grd.addColorStop(0.3, topBubbleColor); 
            grd.addColorStop(1, '#4a148c');

            ctx.fillStyle = grd;
            ctx.fill();


            // Border
            ctx.lineWidth = 3;
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
            ctx.stroke();

            // Text with high contrast
            ctx.fillStyle = '#ffffffff';
            ctx.shadowColor = 'rgba(0, 0, 0, 1)';
            ctx.shadowBlur = 4;
            ctx.shadowOffsetX = 2;
            ctx.shadowOffsetY = 2;
            
            const fontSize = 20;
            ctx.font = `bold ${fontSize}px Nexa, sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            
            const text = filled ? promptBase.replace('___', correctAnswer) : promptBase;
            
            // Handle text wrapping
            const maxWidth = w - 30;
            const words = text.split(' ');
            let line = '';
            const lines = [];
            
            for (let word of words) {
                const testLine = line + word + ' ';
                const metrics = ctx.measureText(testLine);
                if (metrics.width > maxWidth && line !== '') {
                    lines.push(line.trim());
                    line = word + ' ';
                } else {
                    line = testLine;
                }
            }
            if (line.trim()) {
                lines.push(line.trim());
            }
            
            const lineHeight = fontSize * 1.3;
            const totalHeight = lines.length * lineHeight;
            const startY = y + h / 2 - totalHeight / 2 + lineHeight / 2;
            
            lines.forEach((line, index) => {
                ctx.fillText(line, x + w / 2, startY + index * lineHeight);
            });
            
            // Reset shadow
            ctx.shadowColor = 'transparent';
            ctx.shadowBlur = 0;
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 0;
            
            ctx.restore();
        }

        function drawTextBubble(x, y, word) {
            ctx.save();
            ctx.beginPath();
            ctx.arc(x, y, bubbleRadius, 0, Math.PI * 2);
            
            const color = optionColors[word] || '#6a2f4d';
            const grd = ctx.createRadialGradient(
                x - bubbleRadius / 3, y - bubbleRadius / 3, bubbleRadius / 3, 
                x, y, bubbleRadius
            );
            grd.addColorStop(0, '#ffffff');
            grd.addColorStop(0.25, color);
            grd.addColorStop(1, '#000000');
            ctx.fillStyle = grd;
            ctx.fill();

            // Border
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
            ctx.lineWidth = 2;
            ctx.stroke();

            // Text
            ctx.fillStyle = 'white';
            ctx.font = 'bold 12px Arial, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(word, x, y);
            ctx.restore();
        }

        function drawCannon() {
            ctx.save();
            
            const minAngle = (15 * Math.PI) / 180;
            const maxAngle = (165 * Math.PI) / 180;
            const a = clamp(aimAngle, minAngle, maxAngle);
            
            // Simple base platform
            ctx.fillStyle = '#4a4a4a';
            ctx.fillRect(shooterX - 50, shooterY + 15, 100, 25);
            ctx.strokeStyle = '#666';
            ctx.lineWidth = 2;
            ctx.strokeRect(shooterX - 50, shooterY + 15, 100, 25);
            
            // Cannon pivot/base (circular)
            ctx.fillStyle = '#5a5a5a';
            ctx.beginPath();
            ctx.arc(shooterX, shooterY, 28, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = '#777';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // Draw barrel along the aiming line
            const barrelStartDistance = 30; // Start barrel just outside the circular base
            const barrelLength = 35; // Shorter barrel
            const barrelWidth = 20;
            
            const barrelStartX = shooterX + Math.cos(a) * barrelStartDistance;
            const barrelStartY = shooterY - Math.sin(a) * barrelStartDistance;
            const barrelEndX = shooterX + Math.cos(a) * (barrelStartDistance + barrelLength);
            const barrelEndY = shooterY - Math.sin(a) * (barrelStartDistance + barrelLength);
            
            // Draw barrel as a thick line along the aim direction
            ctx.save();
            ctx.strokeStyle = '#666';
            ctx.lineWidth = barrelWidth;
            ctx.lineCap = 'round';
            ctx.beginPath();
            ctx.moveTo(barrelStartX, barrelStartY);
            ctx.lineTo(barrelEndX, barrelEndY);
            ctx.stroke();
            
            // Draw barrel outline
            ctx.strokeStyle = '#888';
            ctx.lineWidth = barrelWidth + 4;
            ctx.globalCompositeOperation = 'destination-over';
            ctx.stroke();
            ctx.globalCompositeOperation = 'source-over';
            ctx.restore();
            
            // Draw muzzle at the end of the barrel
            ctx.save();
            ctx.fillStyle = '#555';
            ctx.beginPath();
            ctx.arc(barrelEndX, barrelEndY, barrelWidth/2 - 2, 0, Math.PI * 2);
            ctx.fill();
            ctx.strokeStyle = '#777';
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.restore();
            
            // Preview bubble at cannon center
            if (selectedWord) {
                const previewRadius = 16;
                
                ctx.save();
                ctx.beginPath();
                ctx.arc(shooterX, shooterY, previewRadius, 0, Math.PI * 2);
                
                const color = optionColors[selectedWord] || '#6a2f4d';
                const grd = ctx.createRadialGradient(
                    shooterX - previewRadius / 3, shooterY - previewRadius / 3, previewRadius / 4, 
                    shooterX, shooterY, previewRadius
                );
                grd.addColorStop(0, '#ffffff');
                grd.addColorStop(0.3, color);
                grd.addColorStop(1, '#000000');
                ctx.fillStyle = grd;
                ctx.fill();
                
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
                ctx.lineWidth = 2;
                ctx.stroke();
                
                ctx.fillStyle = 'white';
                ctx.font = 'bold 10px Arial, sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(selectedWord, shooterX, shooterY);
                ctx.restore();
            }
            
            // Draw aim line continuing from the barrel end
            ctx.save();
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
            ctx.lineWidth = 2;
            ctx.setLineDash([5, 5]);
            const aimLineLength = 80;
            const aimStartX = barrelEndX;
            const aimStartY = barrelEndY;
            const aimEndX = shooterX + Math.cos(a) * (barrelStartDistance + barrelLength + aimLineLength);
            const aimEndY = shooterY - Math.sin(a) * (barrelStartDistance + barrelLength + aimLineLength);
            ctx.beginPath();
            ctx.moveTo(aimStartX, aimStartY);
            ctx.lineTo(aimEndX, aimEndY);
            ctx.stroke();
            ctx.restore();
            
            ctx.restore();
        }

        // Game logic
        function shoot() {
            if (shot && shot.active) return;
            if (!selectedWord) return;
            
            const minAngle = (15 * Math.PI) / 180;
            const maxAngle = (165 * Math.PI) / 180;
            const a = clamp(aimAngle, minAngle, maxAngle);
            
            shot = {
                x: shooterX,
                y: shooterY,
                vx: Math.cos(a) * bubbleSpeed,
                vy: -Math.sin(a) * bubbleSpeed,
                word: selectedWord,
                active: true
            };
        }

        function circleIntersectsRect(cx, cy, r, rect) {
            const nearestX = clamp(cx, rect.x, rect.x + rect.w);
            const nearestY = clamp(cy, rect.y, rect.y + rect.h);
            const dx = cx - nearestX;
            const dy = cy - nearestY;
            return dx * dx + dy * dy <= r * r;
        }

        async function handleHit() {
            if (!(shot && shot.active)) return;
            shot.active = false;
            
            // Immediately check the answer when shot hits
            const result = await checkAnswer(shot.word);
            
            // The checkAnswer function already handles showing right/wrong modals
            // and updating the score, so we don't need to do anything else here
        }

        function update() {
            if (shot && shot.active) {
                shot.x += shot.vx;
                shot.y += shot.vy;
                
                // Bounce off walls
                if (shot.x <= bubbleRadius) {
                    shot.x = bubbleRadius;
                    shot.vx *= -1;
                } else if (shot.x >= width - bubbleRadius) {
                    shot.x = width - bubbleRadius;
                    shot.vx *= -1;
                }
                
                // Check collision
                if (circleIntersectsRect(shot.x, shot.y, bubbleRadius, topRect) || shot.y <= bubbleRadius) {
                    handleHit();
                }
            }
        }

        function draw() {
            if (!ctx) return;
            
            ctx.clearRect(0, 0, width, height);
            
            // Background gradient
            const bgGradient = ctx.createLinearGradient(0, 0, 0, height);
            bgGradient.addColorStop(0, '#1a1a2e');
            bgGradient.addColorStop(1, '#16213e');
            ctx.fillStyle = bgGradient;
            ctx.fillRect(0, 0, width, height);
            
            drawTopLyricBubble();
            drawCannon();
            
            // Draw shot
            if (shot && shot.active) {
                drawTextBubble(shot.x, shot.y, shot.word);
            }
        }

        function gameLoop() {
            update();
            draw();
            raf = requestAnimationFrame(gameLoop);
        }

        // Event handlers
        function onPointerMove(e) {
            if (!canvas) return;
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            const dx = mx - shooterX;
            const dy = shooterY - my;
            aimAngle = Math.atan2(dy, dx);
        }

        function handleKey(e) {
            if (!options.length) return;
            
            if (e.key === 'ArrowRight') {
                selectWord((selectedIndex + 1) % options.length);
            } else if (e.key === 'ArrowLeft') {
                selectWord((selectedIndex - 1 + options.length) % options.length);
            } else if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                shoot();
            }
        }

        function selectWord(index) {
            selectedIndex = index;
            selectedWord = options[index];
            updateUI();
        }

        function tryAgain() {
            showWrong = false;
            showRight = false;
            filled = false;
            shot = null;
            updateUI();
        }

        function nextQuestion() {
            if (showFinal) return;
            showRight = false;
            showWrong = false;
            filled = false;
            shot = null;
            hintRevealed = false;
            getNewQuestion();
        }

        function showHintModal() {
            if (lives <= 0) return;
            showHintConfirm = true;
            updateUI();
        }

        function cancelHintModal() {
            showHintConfirm = false;
            updateUI();
        }

        function confirmHint() {
            if (lives <= 0) return;
            lives -= 1;
            hintRevealed = true;
            showHintConfirm = false;
            updateUI();
        }

        function getScoreRemark(val) {
            if (val === 100) return '🌟🏆 Outstanding! 🏆🌟<br>You are a Taylor Swift expert!';
            if (val === 90) return '✅✨ Great job! ✨✅<br>You know your Taylor Swift lyrics!';
            if (val >= 60) return '👍🙂 Good effort! 🙂👍<br>Keep listening to Taylor Swift!';
            return '🍀😅 Keep practicing! 😅🍀<br>Taylor Swift has so many great songs!';
        }

        async function returnToStart() {
            // attempt to delete session
            try {
                if (sessionId) {
                    await fetch(`${API_BASE_URL}/session/${sessionId}`, { method: 'DELETE' });
                }
            } catch (e) {
                // ignore
            }
            // reset state
            sessionId = null;
            currentQuestion = null;
            score = 100;
            questionsAnswered = 0;
            gameStarted = false;
            loading = false;
            error = null;
            showStartModal = false;
            selectedSongTitle = '';
            selectedDifficulty = '';
            lives = 3;
            showHintConfirm = false;
            hintRevealed = false;
            promptBase = 'Loading...';
            correctAnswer = '';
            options = [];
            optionColors = {};
            selectedIndex = 0;
            selectedWord = '';
            showWrong = false;
            showRight = false;
            filled = false;
            shot = null;
            showFinal = false;
            updateUI();
        }

        // UI Update function
        function updateUI() {
            const app = document.getElementById('game-root');
            
            if (!gameStarted) {
                app.innerHTML = `
                    <div class="karaoke-container">
                        <h1>ENCHANTED<br>SHOOTER</h1>
                        <div class="start-screen">
                            <div class="start-content">
                                <h2>🎵 Taylor Swift Lyric Guesser 🎵</h2>
                                <p>Test your knowledge of Taylor Swift lyrics!</p>
                                <button class="sing-button start-button" ${loading ? 'disabled' : ''} onclick="openStartModal()">
                                    ${loading ? 'Starting...' : 'Start'}
                                </button>
                                ${error ? `
                                    <div class="error-message">
                                        <p>❌ ${error}</p>
                                        <p>Make sure the backend server is running on http://localhost:8000</p>
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                        ${showStartModal ? `
                        <div class="modal-overlay" onclick="event.target === this ? cancelStartModal() : null">
                            <div class="modal modal-wide start-modal">
                                <h3 style="color: #8e24aa;">Pick a Song and Difficulty</h3>
                                <div style="margin-top: 0.75rem; text-align: left;">
                                    <label style="display:block; margin: 0.25rem 0;">Song</label>
                                    <select id="songSelect" onchange="setSelectedSongTitle(this.value)" style="width:100%; padding:0.5rem; border-radius:8px; background:#2a2a4a; color:#fff; border:1px solid rgba(255,255,255,0.15);">
                                        ${songsList.length ? '' : '<option value="">-- Loading songs... --</option>'}
                                        ${songsList.map(s => `<option value="${s.title}" ${s.title===selectedSongTitle?'selected':''}>${s.title}</option>`).join('')}
                                    </select>
                                    <label style="display:block; margin: 0.75rem 0 0.25rem;">Difficulty</label>
                                    <div class="difficulty-row" style="display:flex; gap:0.5rem;">
                                        <button class="sing-button ${selectedDifficulty==='easy'?'selected':''}" style="max-width:none;" onclick="setSelectedDifficulty('easy')">Easy</button>
                                        <button class="sing-button ${selectedDifficulty==='medium'?'selected':''}" style="max-width:none;" onclick="setSelectedDifficulty('medium')">Medium</button>
                                        <button class="sing-button ${selectedDifficulty==='difficult'?'selected':''}" style="max-width:none;" onclick="setSelectedDifficulty('difficult')">Difficult</button>
                                    </div>
                                    <p style="margin-top:0.5rem; opacity:0.75;">Selected: ${selectedDifficulty || 'None'}</p>
                                </div>
                                <div class="actions">
                                    <button class="sing-button" onclick="confirmStartModal()">Start</button>
                                    <button class="sing-button" onclick="cancelStartModal()">Cancel</button>
                                </div>
                            </div>
                        </div>
                        ` : ''}
                    </div>
                `;
            } else {
                app.innerHTML = `
                    <div class="karaoke-container">
                        <h1>ENCHANTED<br>SHOOTER</h1>
                        
                        <div class="animated-rectangle-container">
                            <div class="glow-box"></div>
                            <div class="solid-rectangle">
                                <div class="mute-toggle">
                                    <button class="sing-button" style="max-width:none; padding:0.5rem 1rem;" onclick="toggleMute()">${isMuted ? 'Unmute' : 'Mute'}</button>
                                </div>
                                <div class="now-playing">
                                    <div class="score-display">
                                        <span>Score: ${score}</span>
                                        <span>Questions: ${questionsAnswered}</span>
                                        <span>Lives: ${lives}</span>
                                    </div>
                                </div>

                                <div class="game-area" id="gameArea">
                                    <canvas id="gameCanvas"></canvas>
                                </div>
                                
                                ${options.length > 0 ? `
                                    <div class="options-row">
                                        <div class="options-scroll">
                                            ${options.map((opt, i) => `
                                                <button class="option-bubble ${i === selectedIndex ? 'selected' : ''} ${(hintRevealed && opt === correctAnswer) ? 'hint-glow' : ''}" 
                                                        onclick="selectWord(${i})"
                                                        style="--opt-color: ${optionColors[opt] || '#6a2f4d'}">
                                                    ${opt}
                                                </button>
                                            `).join('')}
                                        </div>

                                    </div>
                                ` : ''}
                            </div>
                        </div>

                        <div class="buttons-container">
                            <button class="sing-button" ${lives <= 0 || showFinal ? 'disabled' : ''} onclick="showHintModal()">Hint</button>
                            <button class="sing-button" onclick="returnToStart()">Exit</button>
                        </div>
                        
                        ${showWrong ? `
                            <div class="modal-overlay" onclick="event.target === this ? nextQuestion() : null">
                                <div class="modal">
                                    <h3 style="color: #ff6b6b;">Wrong lyrics! ❌</h3>
                                    <p>The correct answer was: "<strong>${correctAnswer}</strong>"</p>
                                    <div class="actions">
                                        <button class="sing-button" onclick="nextQuestion()">Next Question</button>
                                    </div>
                                </div>
                            </div>
                        ` : ''}

                        
                        ${showRight ? `
                            <div class="modal-overlay" onclick="event.target === this ? nextQuestion() : null">
                                <div class="modal">
                                    <h3 style="color: #2ecc71;">You're a Great Singer! 🎵</h3>
                                    <p>Perfect! The lyric is "<strong>${correctAnswer}</strong>".</p>
                                    <div class="actions">
                                        <button class="sing-button" onclick="nextQuestion()">Next Question</button>
                                    </div>
                                </div>
                            </div>
                        ` : ''}

                        ${showHintConfirm ? `
                            <div class="modal-overlay" onclick="event.target === this ? cancelHintModal() : null">
                                <div class="modal">
                                    <h3 style="color:#ffd93d;">Use a hint?</h3>
                                    <p>You have <strong>${lives}</strong> ${lives === 1 ? 'life' : 'lives'} left.<p>
                                    <div class="actions">
                                        <button class="sing-button" onclick="confirmHint()">Yes, reveal</button>
                                        <button class="sing-button" onclick="cancelHintModal()">Cancel</button>
                                    </div>
                                </div>
                            </div>
                        ` : ''}

                        ${showFinal ? `
                            <div class="modal-overlay" onclick="event.target === this ? null : null">
                                <div class="modal">
                                    <h3 style="color:#8e24aa;">Final Score</h3>
                                    <p style="font-size:1.25rem; margin-top:0.25rem;"><strong>You collected ${score} points!</strong></p>
                                    <p style="font-size:1.25rem; margin-top:0.25rem;"><strong>${getScoreRemark(score)}</strong></p>
                                    <div class="actions">
                                        <button class="sing-button" onclick="returnToStart()">New Game</button>
                                    </div>
                                </div>
                                <canvas id="confetti-canvas" style="position:fixed; top:0; left:0; width:100%; height:100%; pointer-events:none;"></canvas>
                            </div>
                        ` : ''}

                    </div>
                `;
                
                // Re-initialize canvas after DOM update
                setTimeout(() => {
                    canvas = document.getElementById('gameCanvas');
                    gameArea = document.getElementById('gameArea');
                    if (canvas && gameArea) {
                        computeLayout();
                        canvas.addEventListener('pointermove', onPointerMove);
                        canvas.addEventListener('click', shoot);
                        if (!raf) {
                            raf = requestAnimationFrame(gameLoop);
                        }
                    }
                }, 100);
            }
        }

        // Initialize
        onMount(() => {
            updateUI();
            // preload songs so dropdown has real titles immediately
            fetchSongs();
            // try to start background audio at the very start
            startAudioAutoplay();
            window.addEventListener('resize', () => {
                if (gameStarted) {
                    computeLayout();
                }
            });
            window.addEventListener('keydown', handleKey);
            // expose functions for inline handlers in injected HTML
            Object.assign(window, {
                openStartModal,
                cancelStartModal,
                confirmStartModal,
                setSelectedSongTitle,
                setSelectedDifficulty,
                selectWord,
                showHintModal,
                getNewQuestion,
                nextQuestion,
                confirmHint,
                cancelHintModal,
                returnToStart,
                toggleMute,
                queueInstrumental
            });
            return () => {
                window.removeEventListener('keydown', handleKey);
            };
        });

        $: if (showFinal) {
        const canvas = document.getElementById('confetti-canvas');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;

            let confetti = [];
            for (let i = 0; i < 100; i++) {
                confetti.push({
                    x: Math.random() * canvas.width,
                    y: Math.random() * canvas.height - canvas.height,
                    r: Math.random() * 6 + 2,
                    d: Math.random() * 4 + 4,
                    color: `hsl(${Math.random() * 360}, 100%, 50%)`
                });
            }

            function drawConfetti() {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                for (let i = 0; i < confetti.length; i++) {
                    let c = confetti[i];
                    ctx.beginPath();
                    ctx.arc(c.x, c.y, c.r, 0, Math.PI * 2, false);
                    ctx.fillStyle = c.color;
                    ctx.fill();
                }
                updateConfetti();
            }

            function updateConfetti() {
                for (let i = 0; i < confetti.length; i++) {
                    let c = confetti[i];
                    c.y += c.d;
                    if (c.y > canvas.height) {
                        c.y = -10;
                        c.x = Math.random() * canvas.width;
                    }
                }
            }

            function animate() {
                drawConfetti();
                requestAnimationFrame(animate);
            }
            animate();
        }
    }

</script>

<div id="game-root"></div>