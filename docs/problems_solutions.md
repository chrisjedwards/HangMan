<!-- DRAFT: review and rewrite in your own words before submitting -->

# Problems and Solutions

Compile this table from the real entries in `docs/devlog.md` at the end of the project.

| Problem | Phase | Cause | Solution | Lesson |
| ------- | ----- | ----- | -------- | ------ |
| PowerShell refused to run `.venv\Scripts\Activate.ps1` | Phase 2 | Windows' default PowerShell execution policy blocks running local/unsigned scripts | Ran `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` before activating, scoped to the current session only | Windows dev setup needs an explicit, session-scoped policy override — worth calling out for anyone following the Mac-written setup steps on Windows |
| Frontend showed `"The server sent an invalid response"` errors while testing | Phase 2 | Frontend was opened via VS Code Live Server on port 5500 while the Flask backend ran on port 5000, so `/api` calls from `script.js` hit the wrong origin | Opened `http://127.0.0.1:5000/` directly instead of Live Server, since Flask's dev server already serves `frontend/` itself | Always run the frontend from the same origin as the backend in dev — it also matches how Nginx will proxy both in production |
