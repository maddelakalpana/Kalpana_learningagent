# Windows System Setup & User Guide — SSE Learning Bot

**Prepared for:** SSE Learning Bot Users & Developers  
**Version:** 2.0  
**Target OS:** Windows 10 / Windows 11  

---

## 1. Introduction

The **SSE Learning Bot** is an interactive AI-powered tutoring application that provides 1-on-1 personalized learning sessions using voice and text. It supports two primary study workflows:
1. **Intelligent Topic Search**: Automatically gathers live web context using **Tavily API** and synthesizes comprehensive study material using **OpenRouter LLMs** (*NVIDIA Nemotron 70B*, *Google Gemma 2 27B*, or *OpenRouter Free Model Router*).
2. **Document Upload & Paste**: Extracts study notes from uploaded **PDF**, **DOCX**, **TXT**, or **MD** documents.

Students can choose between two interactive modes:
- **📖 Teach Me**: Step-by-step progressive lessons with voice explanations, written notes, and interactive check questions (MCQs).
- **💬 Doubt Resolution**: Free-flowing conversational Q&A to resolve specific confusions.

---

## 2. Prerequisites

### 2.1 Hardware Requirements
- **Machine**: Laptop or Desktop running Windows 10/11.
- **RAM**: Minimum 8 GB RAM (16 GB recommended).
- **CPU**: Minimum 4 CPU cores (Intel i5/i7/i9 or AMD Ryzen 5/7/9).
- **Disk Space**: At least 5 GB of free disk space.
- **Audio Hardware**: Working Microphone (for student voice input) and Speakers/Headphones (for AI voice playback).
- **Internet Connection**: High-speed, stable internet connection.

### 2.2 Software Requirements
- **Operating System**: Windows 10 (Build 19041+) or Windows 11.
- **Python**: Python 3.10, 3.11, or 3.12 (with `pip` and `venv`).
- **Git**: Git for Windows installed and configured.
- **Web Browser**: Modern browser with WebAudio support (Google Chrome, Microsoft Edge, or Mozilla Firefox).
- **Code Editor**: Visual Studio Code (VS Code) recommended.

### 2.3 Required API Keys
To enable full voice, LLM, and search features, you will need the following API credentials:
1. **Deepgram API Key** (Required for Voice STT mic transcription and TTS voice playback): [https://console.deepgram.com](https://console.deepgram.com)
2. **Google Gemini API Key** or **OpenAI / Proxy Key** (Required for AI Professor teaching engine): [https://aistudio.google.com](https://aistudio.google.com)
3. **OpenRouter API Key** (Required for Topic Search AI Synthesis): [https://openrouter.ai/keys](https://openrouter.ai/keys)
4. **Tavily API Key** (Required for live web search context gathering): [https://tavily.com](https://tavily.com)

---

## 3. Step 1: Verify Hardware & System Setup

### 1. Verify RAM and CPU
1. Press `Win + X` and select **System**.
2. Under **Device specifications**, confirm:
   - **Installed RAM**: 8.00 GB or higher.
   - **Processor**: 4 cores or more.

### 2. Verify Free Disk Space
1. Open **File Explorer** (`Win + E`).
2. Right-click `C:` drive and select **Properties**.
3. Confirm at least 5 GB of free space available.

---

## 4. Step 2: Install Software Dependencies

### 4.1 Install Python (if not installed)
1. Download Python installer (version 3.10+): [https://www.python.org/downloads/windows](https://www.python.org/downloads/windows).
2. Run the installer `.exe` file.
3. **IMPORTANT**: Check the box **"Add python.exe to PATH"** before clicking **Install Now**.
4. Verify installation in PowerShell:
   ```powershell
   python --version
   pip --version
   ```

### 4.2 Install Git for Windows
1. Download installer: [https://git-scm.com/download/win](https://git-scm.com/download/win).
2. Run installer using default settings.
3. Verify in PowerShell:
   ```powershell
   git --version
   ```

---

## 5. Step 3: Clone Repository & Virtual Environment Setup

### 1. Clone Project Repository
Open PowerShell or Command Prompt and run:
```powershell
cd C:\Users\Relanto\Documents
git clone <repository-url> SSE-Learning-Bot
cd SSE-Learning-Bot
```

### 2. Create Python Virtual Environment
```powershell
python -m venv venv
```

### 3. Activate Virtual Environment
```powershell
.\venv\Scripts\activate
```
*(You will see `(venv)` prefix in your PowerShell prompt).*

### 4. Install Project Requirements
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 6. Step 4: Configure Environment Variables (`.env`)

1. In the project folder `SSE-Learning-Bot`, locate `.env.example`.
2. Create a copy of `.env.example` named `.env`:
   ```powershell
   copy .env.example .env
   ```
3. Open `.env` in VS Code or Notepad:
   ```powershell
   code .env
   ```
4. Fill in your API keys in `.env`:

   ```env
   # ==========================================
   # 1. AI PROFESSOR CORE LLM
   # ==========================================
   GEMINI_API_KEY=your_google_gemini_api_key_here
   GEMINI_MODEL=gemini-1.5-flash

   # ==========================================
   # 2. DEEPGRAM VOICE & AUDIO (STT + TTS)
   # ==========================================
   DEEPGRAM_API_KEY=your_deepgram_api_key_here
   DEEPGRAM_STT_MODEL=nova-3
   DEEPGRAM_TTS_MODEL=aura-asteria-en

   # ==========================================
   # 3. TOPIC SEARCH & WEB GATHERING
   # ==========================================
   TAVILY_API_KEY=your_tavily_api_key_here
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   OPENROUTER_MODEL=nvidia/llama-3.1-nemotron-70b-instruct:free
   ```

5. Save and close the `.env` file.

---

## 7. Step 5: Run the SSE Learning Bot Application

### 1. Start FastAPI Backend Server
Ensure virtual environment is activated, then launch Uvicorn:
```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

**Expected Output:**
```text
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### 2. Access the Application in Web Browser
Open your browser and navigate to:
[http://localhost:8000](http://localhost:8000)

---

## 8. Step 6: Step-by-Step User Workflow Guide

### Workflow Option A: Intelligent Topic Search (No Files Needed)
1. On the Setup Dashboard (`http://localhost:8000`), click the **"Search Topic (AI & Web Gather)"** tab.
2. Enter any study topic in the search bar (e.g., *Binary Search Trees*, *Transformer Models*, *Operating Systems Memory Management*).
3. Select your desired OpenRouter AI Model card:
   - **⚡ NVIDIA Nemotron (70B Instruct)**
   - **🌐 Google Gemma 2 (27B/29B Instruct)**
   - **🔀 Free Model Router (Auto Selection)**
4. Click **"Intelligently Gather & Synthesize Topic"**.
5. The system will search live web context via Tavily, synthesize a complete structured study guide, and auto-populate the study material box.

### Workflow Option B: Upload Document / Paste Notes
1. Click the **"Upload Document / Paste Notes"** tab.
2. Drag and drop a **PDF**, **DOCX**, **TXT**, or **MD** file into the drop zone (or paste your notes directly into the text area).
3. Enter the **Topic / Chapter Name** (e.g., *Data Structures Chapter 4*).

---

### Step 7: Select Learning Mode & Start Session

1. **Choose Learning Mode**:
   - **📖 Teach Me**: The AI Professor will explain concepts progressively step by step, asking interactive MCQ check questions after each concept.
   - **💬 Doubt Resolution**: Free-flowing Q&A session where you can ask any doubts about the topic.
2. Click **"Start Learning Session"**.
3. On the interactive session page:
   - Press **Hold to Speak** or click the **Mic Icon** to ask questions using your voice.
   - The AI Professor will speak aloud with Deepgram TTS voice and write notebook summaries.
   - Solve interactive check questions (MCQs) directly in the right-hand panel.

---

## 9. Troubleshooting & Common Issues

### 9.1 Common Python Installation Issues

#### 1. `'python' is not recognized as an internal or external command`
- **Cause**: Python was installed without checking **"Add Python to PATH"**.
- **Solution**: Re-run the Python installer `.exe`, select **Modify**, check **"Add Python to environment variables"**, and complete setup. Alternatively, manually add `C:\Users\<Username>\AppData\Local\Programs\Python\Python310` to your System Environment Variables under `PATH`.

#### 2. PowerShell Script Execution Policy Error (`activate.ps1 cannot be loaded`)
- **Cause**: Windows default PowerShell policy blocks running `.ps1` scripts (`.\venv\Scripts\activate`).
- **Solution**: Open PowerShell as Administrator and run:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

#### 3. Microsoft Store Windows Alias Shortcut
- **Cause**: Typing `python` opens Microsoft Store instead of running Python.
- **Solution**: Open Windows Settings ➔ Search **"Manage app execution aliases"** ➔ Toggle **OFF** the aliases for `python.exe` and `python3.exe`.

#### 4. `pip` Install Permission Denied
- **Cause**: Installing packages globally without administrative rights.
- **Solution**: Ensure your virtual environment is active (`.\venv\Scripts\activate`), or add `--user` flag:
  ```powershell
  pip install -r requirements.txt --user
  ```

---

### 9.2 Common Git Installation & Repository Issues

#### 1. `'git' is not recognized as an internal or external command`
- **Cause**: Git was installed without adding Git binaries to PATH.
- **Solution**: Add `C:\Program Files\Git\cmd` to System Environment Variables `PATH` and restart PowerShell.

#### 2. Line Ending Warnings (`LF will be replaced by CRLF`)
- **Cause**: Git cross-platform line ending conversion between Linux (LF) and Windows (CRLF).
- **Solution**: Configure Git to handle Windows line endings automatically:
  ```powershell
  git config --global core.autocrlf true
  ```

#### 3. SSL Certificate Verify Failed / Corporate Proxy Error
- **Cause**: Firewall or corporate proxy intercepting SSL certificates during `git clone`.
- **Solution**: Temporarily disable SSL verification for Git:
  ```powershell
  git config --global http.sslVerify false
  ```

#### 4. GitHub Authentication Error (`Support for password authentication was removed`)
- **Cause**: GitHub requires Personal Access Tokens (PAT) or SSH keys instead of account passwords.
- **Solution**: Create a PAT at GitHub ➔ Settings ➔ Developer Settings ➔ Personal Access Tokens, and paste the token as your password when cloning/pushing.

---

### 9.3 Common Application & Server Execution Issues

#### 1. `ModuleNotFoundError: No module named 'backend'`
- **Cause**: Running Uvicorn from inside the `backend/` directory instead of the project root.
- **Solution**: Navigate back to project root directory before running:
  ```powershell
  cd C:\Users\Relanto\Documents\SSE Learning Bot\SSE-Learning-Bot
  uvicorn backend.main:app --reload
  ```

#### 2. Port 8000 Already in Use (`[Errno 10048] address already in use`)
- **Cause**: Another process or previous server instance is occupying port 8000.
- **Solution**: Launch server on port 8080:
  ```powershell
  uvicorn backend.main:app --reload --port 8080
  ```
  Or kill the existing process occupying port 8000:
  ```powershell
  netstat -ano | findstr :8000
  taskkill /PID <PID_NUMBER> /F
  ```

#### 3. `OPENROUTER_API_KEY is not set` / Missing LLM Key
- **Cause**: `.env` file is missing API keys.
- **Solution**: Ensure your `.env` file contains `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, or `OPENAI_API_KEY`. The service dynamically falls back to available keys.


---

## 10. Summary Checklist for Setup

- [x] Python 3.10+ installed and added to PATH.
- [x] Virtual environment `venv` created and requirements installed.
- [x] `.env` file configured with Deepgram, Gemini/OpenAI, Tavily, and OpenRouter keys.
- [x] Server launched with `uvicorn backend.main:app --reload`.
- [x] Browser navigated to `http://localhost:8000`.
