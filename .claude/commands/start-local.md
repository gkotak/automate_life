Start both the article summarizer backend (FastAPI) and frontend (Next.js) servers for local development.

Backend will run on http://localhost:8000
Frontend will run on http://localhost:3000 (or 3001/3002 if taken)

Open two terminals and run:

Terminal 1 (Backend):
```bash
cd programs/article_summarizer_backend
./run_local.sh
```

Terminal 2 (Frontend):
```bash
cd web-apps/article-summarizer
npm run dev
```

Then open http://localhost:3000/admin in your browser.

Note: You need to run these in separate terminals since both are long-running processes.
