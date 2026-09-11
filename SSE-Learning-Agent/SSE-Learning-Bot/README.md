# 🎓 SSE Learning Bot — Complete Setup & Quickstart Guide

An interactive, 1-on-1 AI-powered classroom tutor that reads study materials (PDF, DOCX, TXT), speaks naturally with an animated AI avatar, provides real-time speech transcription, generates structured revision notes & insights, and tests concepts with hands-on interactive quizzes.

---

## 📋 Table of Contents
1. [System Prerequisites](#1-system-prerequisites)
2. [Step 1: Install Python](#step-1-install-python)
3. [Step 2: Get the Project Code](#step-2-get-the-project-code)
4. [Step 3: Create & Activate Virtual Environment](#step-3-create--activate-virtual-environment)
5. [Step 4: Install Dependencies](#step-4-install-dependencies)
6. [Step 5: Get Free API Keys](#step-5-get-free-api-keys)
   - [Google Gemini API Key (Core AI Brain)](#51-google-gemini-api-key)
   - [Deepgram API Key (Voice Input & Speech Playback)](#52-deepgram-api-key)
7. [Step 6: Configure Environment Variables (.env)](#step-6-configure-environment-variables-env)
8. [Step 7: Start the Application](#step-7-start-the-application)
9. [How to Use the Learning Room](#how-to-use-the-learning-room)
10. [Troubleshooting & Common Questions](#troubleshooting--faqs)

---

## 1. System Prerequisites

Before starting, ensure your computer has:
- **Operating System**: Windows 10/11, macOS (Intel or Apple Silicon), or Ubuntu/Debian Linux.
- **Hardware**: Working Microphone and Speakers or Headphones (for voice conversations).
- **Web Browser**: Google Chrome, Microsoft Edge, Brave, or Safari.

---

## Step 1: Install Python

The application requires **Python 3.10, 3.11, or 3.12**.

1. Download the Python installer for your operating system:
   - 🔗 **Official Download**: [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. **⚠️ VERY IMPORTANT (Windows users)**:
   - During installation, **check the box** that says:
     `☑ Add python.exe to PATH` (at the bottom of the installer window).
   - Then click **Install Now**.
3. Verify the installation:
   - Open your terminal (PowerShell on Windows, or Terminal on macOS/Linux) and run:
     ```bash
     python --version
     pip --version
     ```
   - You should see `Python 3.10.x` (or higher) and `pip x.x.x`.

---

## Step 2: Get the Project Code

### Option A: Using Git (Recommended)
If you have Git installed ([Download Git](https://git-scm.com/downloads)):
```bash
git clone <repository-url>
cd SSE-Learning-Bot
```

### Option B: Download as ZIP
1. Download the project repository ZIP file and extract it to your desired folder (e.g. `Documents/SSE-Learning-Bot`).
2. Open your terminal and navigate inside the project folder:
   ```bash
   cd path/to/SSE-Learning-Bot
   ```

---

## Step 3: Create & Activate Virtual Environment

A virtual environment keeps your project packages clean and isolated.

### On Windows (PowerShell):
```powershell
# Create the virtual environment
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\Activate.ps1
```
> 💡 *Note for Windows*: If you see an error saying `running scripts is disabled on this system`, run this command once and try activating again:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### On Windows (Command Prompt `cmd.exe`):
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

### On macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

*When activated, your terminal prompt will show `(venv)` at the beginning.*

---

## Step 4: Install Dependencies

With your virtual environment activated, run:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs FastAPI, Uvicorn, Deepgram SDK, PDFPlumber, python-docx, and all required machine learning and web dependencies.

---

## Step 5: Get Free API Keys

The application uses two services with generous free tiers.

### 5.1 Google Gemini API Key
Powers the AI Professor's teaching lessons, explanations, study notes, and quizzes.

1. Go to **Google AI Studio**:
   - 🔗 [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account.
3. Click the blue **Create API key** button.
4. Select a project or create a new one, then copy your generated API key (starts with `AIzaSy...`).
5. *(Gemini offers a completely free tier with plenty of daily requests for learning).*

---

### 5.2 Deepgram API Key
Powers the voice system: transcribing your voice via microphone (Speech-to-Text) and generating natural avatar speech (Text-to-Speech).

1. Go to the **Deepgram Console**:
   - 🔗 [https://console.deepgram.com/signup](https://console.deepgram.com/signup)
2. Sign up with email or GitHub. (Deepgram gives **$200 in free credits** to every new user — enough for hundreds of hours of voice).
3. In the left navigation menu, click **API Keys**.
4. Click **Create a New API Key**.
5. Give it a name (e.g. `SSE Learning Bot`), click **Create Key**, and copy the token.

---

## Step 6: Configure Environment Variables (.env)

1. Inside the `SSE-Learning-Bot` project root folder, copy `.env.example` to `.env`:

   **Windows (PowerShell):**
   ```powershell
   Copy-Item .env.example .env
   ```

   **macOS / Linux:**
   ```bash
   cp .env.example .env
   ```

2. Open the `.env` file in Notepad, VS Code, or any text editor:
   ```ini
   # ==============================================================================
   # 1. CORE LLM (Required)
   # ==============================================================================
   GEMINI_API_KEY=your_actual_gemini_key_here
   GEMINI_MODEL=gemini-1.5-flash

   # ==============================================================================
   # 2. VOICE & AUDIO (Required)
   # ==============================================================================
   DEEPGRAM_API_KEY=your_actual_deepgram_key_here
   DEEPGRAM_STT_MODEL=nova-3
   DEEPGRAM_TTS_MODEL=aura-asteria-en
   ```
3. Replace `your_actual_gemini_key_here` and `your_actual_deepgram_key_here` with your real keys.
4. Save and close the file.

---

## Step 7: Start the Application

Make sure your virtual environment is still activated `(venv)`, then run:

```bash
uvicorn backend.main:app --reload --port 8000
```

You should see output similar to:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

Open your web browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)** (or **[http://127.0.0.1:8000](http://127.0.0.1:8000)**)

---

## How to Use the Learning Room

1. **Upload Study Material**:
   - Drag & drop any document (**PDF, DOCX, TXT, or Markdown**), or paste your syllabus/notes directly into the text box.
   - Enter a topic name (e.g., *Binary Search Trees*, *Photosynthesis*, *Operating Systems*).
2. **Choose Learning Mode**:
   - **📖 Teach Me**: The AI Professor walks you through the document concept-by-concept, explaining foundations, generating structured study notes, and verifying your understanding with interactive quizzes.
   - **💬 Doubt Resolution**: Ask any specific question, troubleshoot code, or clarify difficult parts of the document.
3. **Click "Start Learning Session"**:
   - **Left Panel (AI Professor Avatar & Subtitles)**: Shows the animated professor orb and live spoken dialogue subtitles while playing clear voice audio.
   - **Right Panel (Concept Notes & Quizzes)**: Generates structured revision notes with **📌 Key Takeaways**, **💡 Key Insights**, and interactive multiple-choice verification questions.
4. **Interact with Voice or Text**:
   - Click and **Hold to Speak** (or press the microphone button) to ask questions aloud.
   - Or type in the input bar at the bottom.
5. **Resume Past Sessions**:
   - Click **`⏳ Past Sessions`** in the top navigation bar at any time to open your slide-out session history and resume any past lesson right where you left off.

---

## Troubleshooting & FAQs

### Q: The browser says "Microphone access denied"
- **Solution**: Click the lock icon 🔒 next to the URL bar in your browser, find **Microphone**, and change it from *Block* to *Allow*. Then refresh the page.

### Q: No voice is playing from the AI avatar
- **Solution**: Modern browsers block audio from playing automatically until you interact with the page. Click anywhere on the webpage or press the audio/mic button to permit audio playback.
- Check that your `DEEPGRAM_API_KEY` in `.env` is valid and has remaining free credits.

### Q: Error: `Address already in use` or Port 8000 is occupied
- **Solution**: Another program is using port 8000. Start the server on port 8001 instead:
  ```bash
  uvicorn backend.main:app --reload --port 8001
  ```
  Then visit [http://localhost:8001](http://localhost:8001).

### Q: How do I stop the server?
- Press `Ctrl + C` in the terminal window where Uvicorn is running.

---

### ✨ Summary Checklist
- [x] Python 3.10+ installed with PATH checked
- [x] Virtual environment created and activated `(venv)`
- [x] Packages installed (`pip install -r requirements.txt`)
- [x] Keys pasted into `.env` ([Gemini API](https://aistudio.google.com/app/apikey) & [Deepgram API](https://console.deepgram.com/signup))
- [x] Started with `uvicorn backend.main:app --reload --port 8000`
