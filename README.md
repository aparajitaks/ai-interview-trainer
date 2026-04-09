# AI Interview Simulator & Coach

AI Interview Simulator & Coach is a full-stack AI platform that simulates realistic technical interviews, evaluates answers with LLMs (Gemini), and generates a structured post-interview coaching report.

Built to feel like a modern startup product, this system combines an interactive interview UX with adaptive intelligence to help candidates practice, learn, and improve.

---

## Project Overview

The platform is designed around an end-to-end interview learning loop:

- Real-time interview experience
- Adaptive questioning (LLM-based)
- Answer evaluation (technical quality + communication clarity)
- Detailed final report with personalized improvement guidance

This is not just a Q&A chatbot. It is an interview simulator with session memory, dynamic follow-ups, and actionable coaching output.

---

## Tech Stack

### Frontend
- React (Vite)
- Tailwind CSS

### Backend
- FastAPI (Python)
- Gemini API (LLM)

### Deployment
- Backend: Render
- Frontend: Vercel

---

## Features

- Live AI interview simulation
- Domain-based interview tracks (AI/ML, Frontend, Backend, etc.)
- Dynamic question generation via Gemini
- Answer evaluation across:
  - Technical correctness
  - Clarity of explanation
  - Depth of understanding
- Cross-questioning / follow-up logic based on previous answers
- Skip handling for unanswered questions
- Final coaching report with:
  - Expected answers
  - Explanations
  - Key points
  - Example responses
  - Personalized improvement plan

---

## Architecture

### High-level flow

1. User starts interview from frontend
2. Frontend calls backend session start endpoint
3. Backend creates interview session state
4. Gemini generates contextual question(s)
5. User submits answer
6. Backend evaluates answer and decides next step:
   - next question
   - follow-up question
   - end interview
7. At completion, backend compiles final learning report
8. Frontend renders report and recommendations

### Frontend <-> Backend communication

- Frontend communicates with backend via REST endpoints
- Interview state is driven by backend responses
- Frontend updates UI phase (`starting`, `question`, `recording`, `processing`, `complete`) based on API payloads

### LLM integration (Gemini)

Gemini is used for:

- adaptive question generation
- answer scoring and critique
- expected answer generation
- explanation and improvement guidance
- final report synthesis

### Session management

Backend maintains per-session context, including:

- role/domain
- round progression
- prior question/answer history
- interim evaluation data
- final report object

---

## Project Structure

```bash
ai-interview-trainer/
├── backend/
│   ├── src/
│   │   ├── main.py               # FastAPI deploy entrypoint (uvicorn src.main:app)
│   │   ├── api/                  # API routes (interview, evaluation, health, etc.)
│   │   ├── interview/            # Interview session and orchestration logic
│   │   ├── llm_engine/           # Gemini client, prompting, report generation
│   │   ├── evaluation/           # Scoring and feedback composition
│   │   ├── pipeline/             # Video analysis pipeline modules
│   │   ├── cv_engine/            # Local CV runtime pipeline (separate from API entrypoint)
│   │   └── utils/                # Config, logging, shared helpers
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── pages/                # Landing, interview flow, results views
    │   ├── hooks/                # Interview/audio/analysis state hooks
    │   ├── services/             # API client layer
    │   ├── components/           # Reusable UI + layout components
    │   └── App.jsx               # Route composition
    └── package.json
```

---

## Run Locally

## 1) Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create backend environment variable:

```bash
export GEMINI_API_KEY=your_key     # Windows PowerShell: $env:GEMINI_API_KEY="your_key"
```

Run FastAPI:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Backend health check:

```bash
http://127.0.0.1:8000/health
```

## 2) Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:

```bash
http://127.0.0.1:5173
```

---

## Deployment

### Backend (Render)

- Runtime: Python
- Root directory: `backend`
- Build command:
  - `pip install -r requirements.txt`
- Start command:
  - `uvicorn src.main:app --host 0.0.0.0 --port $PORT`

### Frontend (Vercel)

- Framework: Vite
- Root directory: `frontend`
- Build command:
  - `npm run build`
- Output directory:
  - `dist`

---

## Environment Variables

Set the following variable for backend:

```bash
GEMINI_API_KEY=your_key
```

---

## Screenshots

Add product screenshots here:

- Interview page (live Q&A flow)
- Final report page (score + coaching insights)

Example placeholders:

```markdown
![Interview Page](./docs/screenshots/interview-page.png)
![Final Report Page](./docs/screenshots/final-report-page.png)
```

---

## Future Improvements

- Voice-first interview mode (enhanced speech-to-text pipeline)
- Webcam + behavioral analysis integration in live interview scoring
- User authentication and profile-based progress tracking
- Analytics dashboard (history, strengths/weakness trends, role-wise performance)
- Recruiter mode with rubric customization and exportable reports

---

## Why this project stands out

This project demonstrates:

- Full-stack AI product engineering
- LLM orchestration beyond prompt demos
- Structured evaluation/report generation workflows
- Production-oriented deployment thinking (Render + Vercel)

It is built to showcase real engineering depth for recruiters, internships, and AI-focused product roles.
