# 🤖 Autonomous Multi-AI Agent System

A **100% free**, **directory-agnostic**, and **Docker plug-and-play** Multi-Agent Software Development Fleet.

---

## 🏛️ Architecture Overview

```
1. Product Manager (You) -> Provides high-level goal and approves outcomes.
2. Lead Planner Squad   -> Lead Planner + Requirements Analyst + System Architect.
3. Project Manager      -> Orchestrates 4 engineers:
                           • Developer 1 (Core / Backend)
                           • Developer 2 (Frontend / Integration)
                           • Tester 1 (Unit & Functional Tests)
                           • Tester 2 (End-to-End & Regression Tests)
4. Health & Watchdog    -> Detects deadlocks, monitors heartbeats, limits retries.
```

---

## 🚀 Quick Start (Plug-and-Play with Docker)

### 1. Configure Your Free API Key
Copy the example environment file and add your [free Gemini API Key](https://aistudio.google.com/app/apikey):

```bash
cp .env.example .env
```
Inside `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
# Optional: Point to any folder on your machine you want the agents to work in:
TARGET_PROJECT_PATH=C:/Path/To/Your/Project
```

### 2. Launch the Fleet
```bash
docker compose up --build
```

### 3. Open the Dashboard
Navigate to `http://localhost:8501` in your browser:
1. Enter your **Project Name** and **High-Level Goal**.
2. Click **🚀 Plan & Dispatch Project**.
3. Watch the Lead Planner and sub-agents analyze requirements and break them down into technical tasks.
4. Go to **⚡ Project Execution Controls** and click **▶️ Run Sprint** to watch the Devs write code and Testers verify it!

---

## 💻 Running Locally (Without Docker)

If you prefer to run directly in Python:

```bash
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # (Windows)
# source venv/bin/activate    # (Mac/Linux)

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file with your GEMINI_API_KEY
copy .env.example .env

# 4. Run dashboard
streamlit run src/ui/app.py
```
