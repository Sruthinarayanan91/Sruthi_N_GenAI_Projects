# RFP Supplier Evaluation

Mini-project for supplier proposal evaluation using OpenRouter, Pydantic, SQLite and Streamlit.

## Architecture
PDF -> PDF service -> Evaluation Agent -> Pydantic validation -> deterministic scoring -> PPI/ranking -> SQLite -> Streamlit.

## VS Code local test

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `.env` from `.env.example` and set `OPENROUTER_API_KEY`.

Put PDFs in `data/suppliers/`, then:

```powershell
python scripts/init_db.py
streamlit run app/streamlit_app.py
```

Open http://localhost:8501.

## GitHub

```powershell
git init
git add .
git commit -m "Initial RFP supplier evaluation project"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/rfp-supplier-evaluation.git
git push -u origin main
```

Never commit `.env`, API keys, secrets.toml, or confidential supplier PDFs.

## Streamlit Community Cloud

Deploy repository entrypoint:

`app/streamlit_app.py`

Add the secret:

```toml
OPENROUTER_API_KEY = "your-key"
```

The application expects supplier PDFs in `data/suppliers/`.

For a public GitHub repository, only publish supplier PDFs if you are authorized to do so.
