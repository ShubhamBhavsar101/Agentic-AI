# Agentic-AI

A curated collection of DevOps learning resources and tools.

## DevOps Learning Hub

The main attraction — `devops-learning-hub.html` — is a hand-curated directory of the best DevOps learning resources across the internet: courses, books, certifications, YouTube channels, communities, roadmaps, GitHub repos, and more.

### Running with Favourites Support

The HTML file includes a **Favourites** feature (star any resource, see them collected in the Favourites section). Favourites are persisted via a lightweight Python server and synced to Git automatically.

**To run:**

```bash
cd Agentic-AI
python3 favourites-service.py
```

Then open: http://localhost:8000/devops-learning-hub.html

**How it works:**
- Star any resource by clicking the ☆ button in the top-right of its card
- Favourites are saved to `.favourites.json` and auto-committed/pushed to Git
- Open the page on any machine (after `git pull`) and your favourites come with it
- No database, no accounts, no cloud — just a JSON file and Git

**Requirements:** Python 3.12+ (stdlib only — no pip installs needed)
