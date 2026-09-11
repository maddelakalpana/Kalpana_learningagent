/* ═══════════════════════════════════════════════════════════════════════════
   SSE Learning Bot — Interactive Learning Room (app.js)
   ═══════════════════════════════════════════════════════════════════════════ */

(function () {
  "use strict";

  // ── Extract session ID from URL (/learn/<uuid> or /session/<uuid>) ───────
  const pathParts = window.location.pathname.split("/").filter(Boolean);
  const SESSION_ID = pathParts[pathParts.length - 1] || "";
  if (!SESSION_ID) {
    document.body.innerHTML = "<h1 style='padding:40px;font-family:sans-serif'>Invalid session URL.</h1>";
    return;
  }

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const tutorOrb = document.getElementById("tutorOrb");
  const tutorLabel = document.getElementById("tutorLabel");
  const speechBubble = document.getElementById("currentAiText");
  const listeningChip = document.getElementById("listeningChip");
  const chipLabel = document.getElementById("chipLabel");
  const connectionDot = document.querySelector(".dot-ring");
  const transcriptScroll = document.getElementById("transcriptScroll");
  const transcriptEmpty = document.getElementById("transcriptEmpty");
  const textInput = document.getElementById("textInput");
  const sendTextBtn = document.getElementById("sendTextBtn");
  const micBtn = document.getElementById("micBtn");
  const headerTopicName = document.getElementById("headerTopicName");
  const headerModeBadge = document.getElementById("headerModeBadge");
  const convoTopicTitle = document.getElementById("convoTopicTitle");
  const convoModePill = document.getElementById("convoModePill");

  let mcqCounter = 0;
  let activeStreamMsg = null;
  let ws = null;
  let isIntentionallyClosed = false;
  let lastProcessedAiText = "";

  // ── Load session metadata ─────────────────────────────────────────────────
  let sessionMode = "teach";
  let sessionTopic = "Session";

  function getAiLabel() {
    return sessionMode === "teach" ? "AI Professor" : "Doubt Resolver";
  }

  function parseMcqFromJson(raw_text) {
    if (!raw_text) return null;
    const match = raw_text.match(/\[MCQ\]([\s\S]*?)(?:\[\/MCQ\]|$)/i);
    if (!match) return null;
    try {
      let raw = match[1].trim();
      const jsonMatch = raw.match(/(\{[\s\S]*\})/);
      if (jsonMatch) raw = jsonMatch[1].trim();
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  // ── Helper to split raw text into spoken dialogue & chat notes ────────────
  function extractSpeechAndNotes(rawText) {
    if (!rawText) return { speech: "", notes: "" };
    const cleanText = cleanTextFromMcq(rawText);

    const speechMatch = cleanText.match(/\[SPEECH\]([\s\S]*?)(?:\[\/SPEECH\]|$)/i);
    const notesMatch = cleanText.match(/\[NOTES\]([\s\S]*?)(?:\[\/NOTES\]|$)/i);

    if (speechMatch && notesMatch) {
      return { speech: speechMatch[1].trim(), notes: notesMatch[1].trim() };
    }
    if (speechMatch) {
      const sp = speechMatch[1].trim();
      let nt = cleanText.replace(/\[SPEECH\][\s\S]*?(?:\[\/SPEECH\]|$)/i, "").replace(/\[\/?NOTES\]/gi, "").trim();
      return { speech: sp, notes: nt || sp };
    }
    if (notesMatch) {
      const nt = notesMatch[1].trim();
      let sp = cleanText.replace(/\[NOTES\][\s\S]*?(?:\[\/NOTES\]|$)/i, "").replace(/\[\/?SPEECH\]/gi, "").trim();
      return { speech: sp || nt, notes: nt };
    }

    // Fallback: If text contains bullet points (•, *, -), spoken dialogue is text before the bullets, and notes are the bullets
    const bulletSplit = cleanText.split(/(?:^|\n)\s*[•\*\-]\s+/);
    if (bulletSplit.length > 1 && bulletSplit[0].trim()) {
      const speechPart = bulletSplit[0].trim();
      const notesPart = "• " + bulletSplit.slice(1).join("\n• ");
      return { speech: speechPart, notes: notesPart };
    }


    return { speech: cleanText, notes: cleanText };
  }

  async function loadSessionMeta() {
    try {
      const res = await fetch(`/api/session/${SESSION_ID}`);
      if (!res.ok) throw new Error("Session not found");
      const data = await res.json();
      sessionMode = data.mode || "teach";
      sessionTopic = data.topic_name || "Session";

      headerTopicName.textContent = sessionTopic;
      convoTopicTitle.textContent = sessionTopic;

      const modeLabel = sessionMode === "teach" ? "📖 Teach Me" : "💬 Doubt Resolution";
      headerModeBadge.textContent = modeLabel;
      convoModePill.textContent = modeLabel;
      tutorLabel.textContent = getAiLabel();

      // Pre-render past history if resuming session
      if (data.history && data.history.length > 0) {
        if (transcriptEmpty) transcriptEmpty.classList.add("hidden");
        data.history.forEach((msg) => {
          if (msg.role === "user") {
            appendMsg("You", msg.content, "user");
          } else {
            const { speech, notes } = extractSpeechAndNotes(msg.content);
            const mcqData = parseMcqFromJson(msg.content);
            appendMsg(getAiLabel(), notes, "ai", mcqData);
            speechBubble.textContent = cleanSpeechText(speech);
          }
        });
      }
    } catch (e) {
      console.error("Could not load session:", e);
    }
  }

  // ── Helper to strip MCQ block from text stream ─────────────────────────────
  function cleanTextFromMcq(text) {
    if (!text) return "";
    return text.replace(/\[MCQ\][\s\S]*?(?:\[\/MCQ\]|$)/gi, "").trim();
  }

  // ── WebSocket Management ──────────────────────────────────────────────────
  function initWebSocket() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws/learn/${SESSION_ID}`);

    ws.addEventListener("open", () => {
      setConnected(true);
      ws.send(JSON.stringify({ type: "start" }));
    });

    ws.addEventListener("close", () => {
      setConnected(false);
      if (!isIntentionallyClosed) {
        setChip("Reconnecting...", "");
        setTimeout(() => {
          initWebSocket();
        }, 3000);
      } else {
        setChip("Disconnected", "");
      }
    });

    ws.addEventListener("error", (err) => {
      console.error("WS error:", err);
      setConnected(false);
    });

    ws.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleServerMessage(payload);
      } catch (err) {
        console.error("Error parsing WS message:", err);
      }
    });
  }

  // ── Message handler ───────────────────────────────────────────────────────
  function handleServerMessage(payload) {
    const { type } = payload;

    // 1. New Differentiated Streaming Chunk
    if (type === "ai_stream_chunk") {
      // Subtitle box displays ONLY spoken words
      if (payload.speech_chunk) {
        speechBubble.textContent = cleanSpeechText(payload.speech_chunk);
      }

      // Chat box displays structured concept notes & takeaways
      const notesContent = payload.notes_chunk || payload.speech_chunk || "";
      if (notesContent) {
        if (!activeStreamMsg) {
          if (transcriptEmpty) transcriptEmpty.classList.add("hidden");
          const msg = document.createElement("div");
          msg.className = "msg msg-ai";

          const lbl = document.createElement("span");
          lbl.className = "msg-label";
          lbl.textContent = getAiLabel();

          const bubble = document.createElement("div");
          bubble.className = "msg-bubble";

          msg.appendChild(lbl);
          msg.appendChild(bubble);

          transcriptScroll.appendChild(msg);
          activeStreamMsg = { msgEl: msg, bubbleEl: bubble };
        }

        activeStreamMsg.bubbleEl.innerHTML = formatMessageText(notesContent, "ai");
        transcriptScroll.scrollTop = transcriptScroll.scrollHeight;
      }

      setOrbState("speaking");
      setChip("Generating response...", "speaking");
      return;
    }

    // 2. New Differentiated Completed Response
    if (type === "ai_response_done") {
      const speech = payload.speech || "";
      const notes = payload.notes || speech;

      lastProcessedAiText = (speech + notes).trim();
      speechBubble.textContent = cleanSpeechText(speech);

      if (activeStreamMsg) {
        activeStreamMsg.bubbleEl.innerHTML = formatMessageText(notes, "ai");
        if (payload.mcq && payload.mcq.options && payload.mcq.options.length) {
          const mcqCard = createMcqCard(payload.mcq);
          activeStreamMsg.msgEl.appendChild(mcqCard);
        }
        activeStreamMsg = null;
      } else {
        appendMsg(getAiLabel(), notes, "ai", payload.mcq);
      }

      setOrbState("speaking");
      setChip("Speaking...", "speaking");
      transcriptScroll.scrollTop = transcriptScroll.scrollHeight;
      return;
    }

    // 3. Backward Compatibility Fallbacks
    if (type === "ai_text_chunk") {
      const { speech, notes } = extractSpeechAndNotes(payload.accumulated || payload.chunk || "");
      if (speech) speechBubble.textContent = cleanSpeechText(speech);

      if (!activeStreamMsg) {
        if (transcriptEmpty) transcriptEmpty.classList.add("hidden");
        const msg = document.createElement("div");
        msg.className = "msg msg-ai";

        const lbl = document.createElement("span");
        lbl.className = "msg-label";
        lbl.textContent = getAiLabel();

        const bubble = document.createElement("div");
        bubble.className = "msg-bubble";

        msg.appendChild(lbl);
        msg.appendChild(bubble);

        transcriptScroll.appendChild(msg);
        activeStreamMsg = { msgEl: msg, bubbleEl: bubble };
      }

      activeStreamMsg.bubbleEl.innerHTML = formatMessageText(notes || speech, "ai");
      transcriptScroll.scrollTop = transcriptScroll.scrollHeight;
      setOrbState("speaking");
      setChip("Generating response...", "speaking");
      return;
    }

    if (type === "ai_text_done" || type === "ai_text") {
      const { speech, notes } = extractSpeechAndNotes(payload.text || "");
      if (notes.trim() && notes.trim() === lastProcessedAiText && !activeStreamMsg) {
        return;
      }
      lastProcessedAiText = notes.trim();
      speechBubble.textContent = cleanSpeechText(speech);

      if (activeStreamMsg) {
        activeStreamMsg.bubbleEl.innerHTML = formatMessageText(notes, "ai");
        if (payload.mcq && payload.mcq.options && payload.mcq.options.length) {
          const mcqCard = createMcqCard(payload.mcq);
          activeStreamMsg.msgEl.appendChild(mcqCard);
        }
        activeStreamMsg = null;
      } else {
        appendMsg(getAiLabel(), notes, "ai", payload.mcq);
      }

      setOrbState("speaking");
      setChip("Speaking...", "speaking");
      transcriptScroll.scrollTop = transcriptScroll.scrollHeight;
      return;
    }

    // Audio stream from Deepgram TTS
    if (type === "ai_audio") {
      playAudio(payload.data, () => {
        setOrbState("idle");
        setChip("Listening", "listening");
      });
    }

    // Speech-to-text transcript of what student said
    if (type === "transcript") {
      appendMsg("You", payload.text, "user");
      setOrbState("thinking");
      setChip("Thinking...", "");
    }

    // Server status notification
    if (type === "server_status") {
      setChip(payload.message || "Processing...", "");
      setOrbState("thinking");
    }

    // Error notification
    if (type === "error") {
      appendSystemMsg("⚠ " + (payload.message || "An error occurred."));
      setOrbState("idle");
      setChip("Ready", "listening");
      activeStreamMsg = null;
    }
  }

  // ── Append message to transcript ──────────────────────────────────────────
  function appendMsg(label, text, role, mcqData) {
    if (transcriptEmpty) {
      transcriptEmpty.classList.add("hidden");
    }

    const msg = document.createElement("div");
    msg.className = `msg msg-${role === "ai" ? "ai" : "user"}`;

    const lbl = document.createElement("span");
    lbl.className = "msg-label";
    lbl.textContent = label;

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.innerHTML = formatMessageText(text, role);

    if (role === "user") {
      msg.appendChild(bubble);
      msg.appendChild(lbl);
    } else {
      msg.appendChild(lbl);
      msg.appendChild(bubble);

      // Render interactive MCQ card if provided
      if (mcqData && mcqData.options && mcqData.options.length) {
        const mcqCard = createMcqCard(mcqData);
        msg.appendChild(mcqCard);
      }
    }

    transcriptScroll.appendChild(msg);
    transcriptScroll.scrollTop = transcriptScroll.scrollHeight;
  }

  // ── Interactive MCQ Component ─────────────────────────────────────────────
  function createMcqCard(mcq) {
    mcqCounter++;
    const cardId = `mcq_${mcqCounter}_${Date.now()}`;
    const card = document.createElement("div");
    card.className = "mcq-card";

    const header = document.createElement("div");
    header.className = "mcq-card-header";
    header.innerHTML = `
      <span class="mcq-badge">🎯 Interactive Check</span>
      <h4 class="mcq-question">${escapeHtml(mcq.question)}</h4>
    `;
    card.appendChild(header);

    const optionsContainer = document.createElement("div");
    optionsContainer.className = "mcq-options";

    mcq.options.forEach((opt, idx) => {
      const optionLabel = document.createElement("label");
      optionLabel.className = "mcq-option";
      optionLabel.innerHTML = `
        <input type="radio" name="${cardId}" value="${idx}">
        <span class="mcq-option-indicator">${String.fromCharCode(65 + idx)}</span>
        <span class="mcq-option-text">${escapeHtml(opt)}</span>
      `;
      optionsContainer.appendChild(optionLabel);
    });
    card.appendChild(optionsContainer);

    // Submit button
    const actions = document.createElement("div");
    actions.className = "mcq-actions";

    const submitBtn = document.createElement("button");
    submitBtn.type = "button";
    submitBtn.className = "btn-mcq-submit";
    submitBtn.textContent = "Check Answer";
    actions.appendChild(submitBtn);

    // Feedback area
    const feedbackBox = document.createElement("div");
    feedbackBox.className = "mcq-feedback hidden";
    card.appendChild(actions);
    card.appendChild(feedbackBox);

    // Submit handler
    submitBtn.addEventListener("click", () => {
      const selectedInput = optionsContainer.querySelector(`input[name="${cardId}"]:checked`);
      if (!selectedInput) {
        feedbackBox.className = "mcq-feedback wrong";
        feedbackBox.textContent = "Please select an option first!";
        feedbackBox.classList.remove("hidden");
        return;
      }

      const selectedIdx = parseInt(selectedInput.value, 10);
      const isCorrect = selectedIdx === mcq.answer_index;

      // Lock options
      optionsContainer.querySelectorAll("input").forEach((inp) => (inp.disabled = true));
      submitBtn.disabled = true;

      // Style options
      optionsContainer.querySelectorAll(".mcq-option").forEach((optEl, i) => {
        if (i === mcq.answer_index) {
          optEl.classList.add("correct");
        } else if (i === selectedIdx && !isCorrect) {
          optEl.classList.add("wrong");
        }
      });

      // Feedback message
      if (isCorrect) {
        feedbackBox.className = "mcq-feedback correct";
        feedbackBox.innerHTML = `<strong>🎉 Correct!</strong> ${escapeHtml(mcq.explanation || "")}`;
      } else {
        const correctLetter = String.fromCharCode(65 + mcq.answer_index);
        feedbackBox.className = "mcq-feedback wrong";
        feedbackBox.innerHTML = `<strong>❌ Incorrect.</strong> Correct answer is <strong>(${correctLetter})</strong>. ${escapeHtml(mcq.explanation || "")}`;
      }
      feedbackBox.classList.remove("hidden");

      // Notify WebSocket of user response so AI knows student's understanding
      if (ws && ws.readyState === WebSocket.OPEN) {
        const chosenText = mcq.options[selectedIdx];
        const statusText = isCorrect ? "correct" : "incorrect";
        ws.send(JSON.stringify({
          type: "text",
          text: `[Quick Check Answer]: I selected option (${String.fromCharCode(65 + selectedIdx)}) "${chosenText}". Result: ${statusText}.`
        }));
      }

      transcriptScroll.scrollTop = transcriptScroll.scrollHeight;
    });

    return card;
  }

  function formatMessageText(text, role) {
    if (!text) return "";
    let safe = escapeHtml(text.trim());

    if (role === "user") {
      return safe.replace(/\n/g, "<br>");
    }

    // Clean any tags
    safe = safe.replace(/\[\/?(NOTES|SPEECH)\]/gi, "").trim();

    // Bold **text** -> <strong>text</strong>
    safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Key Insight block
    safe = safe.replace(/(?:💡|Idea|Insight|Tip):\s*(.+)/gi, "<div class='msg-insight'><span class='insight-badge'>💡 Key Insight</span><p class='insight-text'>$1</p></div>");

    // Bullet points -> Key Takeaways
    safe = safe.replace(/(?:^|\n)\s*[•\*\-]\s+(.+)/g, "<div class='msg-bullet'>📌 $1</div>");

    // Headings
    safe = safe.replace(/(?:^|\n)#{1,3}\s+(.+)/g, "<h4 class='notes-heading'>$1</h4>");

    // Paragraph gaps
    safe = safe.replace(/\n\n+/g, "<div class='msg-gap'></div>").replace(/\n/g, "<br>");

    return `<div class='notes-card-header'><span class='notes-badge'>📝 Concept Notes &amp; Key Insights</span></div><div class='notes-card-body'>${safe}</div>`;
  }

  function cleanSpeechText(text) {
    if (!text) return "";
    let cleaned = text.replace(/\[\/?(SPEECH|NOTES)\]/gi, "");
    cleaned = cleaned.replace(/\[MCQ\][\s\S]*?(?:\[\/MCQ\]|$)/gi, "");
    return cleaned.replace(/[\*\#\_]/g, "").replace(/\s+/g, " ").trim();
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function appendSystemMsg(text) {
    const el = document.createElement("div");
    el.style.cssText = "font-size:12.5px;color:#64748b;text-align:center;padding:6px 0;font-weight:500;";
    el.textContent = text;
    transcriptScroll.appendChild(el);
    transcriptScroll.scrollTop = transcriptScroll.scrollHeight;
  }

  // ── Orb state ─────────────────────────────────────────────────────────────
  function setOrbState(state) {
    tutorOrb.classList.remove("speaking", "thinking", "idle");
    tutorOrb.classList.add(state);
  }

  // ── Status chip ───────────────────────────────────────────────────────────
  function setChip(text, state) {
    chipLabel.textContent = text;
    listeningChip.classList.remove("listening", "speaking");
    if (state) listeningChip.classList.add(state);
  }

  // ── Connection dot ────────────────────────────────────────────────────────
  function setConnected(connected) {
    connectionDot.classList.toggle("connected", connected);
    if (connected) setChip("Ready", "listening");
  }

  // ── Audio playback ────────────────────────────────────────────────────────
  let currentAudio = null;

  function playAudio(b64data, onEnd) {
    if (!b64data) {
      if (onEnd) onEnd();
      return;
    }
    if (currentAudio) {
      try { currentAudio.pause(); } catch (e) {}
      currentAudio = null;
    }
    try {
      const binary = atob(b64data);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      const blob = new Blob([bytes], { type: "audio/mp3" });
      const url = URL.createObjectURL(blob);
      currentAudio = new Audio(url);
      currentAudio.onended = () => { URL.revokeObjectURL(url); if (onEnd) onEnd(); };
      currentAudio.onerror = (err) => { console.warn("[Audio] Audio element error:", err); URL.revokeObjectURL(url); if (onEnd) onEnd(); };
      const p = currentAudio.play();
      if (p !== undefined) {
        p.catch((err) => {
          console.warn("[Audio] Autoplay / Play error:", err);
          if (onEnd) onEnd();
        });
      }
    } catch (e) {
      console.warn("[Audio] Playback failed:", e);
      if (onEnd) onEnd();
    }
  }

  // ── Text input (Immediate Bubble Rendering) ──────────────────────────────
  function sendTextMessage() {
    const text = textInput.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    textInput.value = "";
    
    // Immediately append user message to chat transcript
    appendMsg("You", text, "user");

    // Send to WebSocket
    ws.send(JSON.stringify({ type: "text", text }));
    setOrbState("thinking");
    setChip("Thinking...", "");
  }

  sendTextBtn.addEventListener("click", sendTextMessage);
  textInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendTextMessage();
    }
  });

  // ── Voice recording ───────────────────────────────────────────────────────
  let mediaRecorder = null;
  let audioChunks = [];
  let micStream = null;

  micBtn.addEventListener("mousedown", startRecording);
  micBtn.addEventListener("touchstart", (e) => { e.preventDefault(); startRecording(); }, { passive: false });
  document.addEventListener("mouseup", stopRecording);
  document.addEventListener("touchend", stopRecording);

  async function startRecording() {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      appendSystemMsg("Not connected. Reconnecting...");
      return;
    }
    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunks = [];
      mediaRecorder = new MediaRecorder(micStream);
      mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
      mediaRecorder.onstop = handleAudioStop;
      mediaRecorder.start();
      micBtn.classList.add("recording");
    } catch (err) {
      appendSystemMsg("Microphone access denied or not available.");
      console.error("[Mic]", err);
    }
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
      if (micStream) { micStream.getTracks().forEach(t => t.stop()); micStream = null; }
      micBtn.classList.remove("recording");
    }
  }

  async function handleAudioStop() {
    if (!audioChunks.length) return;
    const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
    const reader = new FileReader();
    reader.onloadend = () => {
      const dataUrl = reader.result;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "audio", data: dataUrl }));
        setChip("Transcribing...", "");
        setOrbState("thinking");
      }
    };
    reader.readAsDataURL(blob);
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  loadSessionMeta();
  initWebSocket();
  setOrbState("thinking");
  setChip("Connecting...", "");

})();