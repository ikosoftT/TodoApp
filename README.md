# Flask Todo App

A small Flask todo application backed by Neon Postgres and ready for Vercel.

## Local development

Create a virtual environment, install the dependencies, and provide a Neon
connection string as `DATABASE_URL`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='your-pooled-neon-connection-string'
flask --app app run --debug
```

Never commit the real connection string. The application creates its `todos`
table and index automatically on first use.

## Deploy to Vercel

1. Import the repository into Vercel.
2. Add a Neon Postgres integration to the project.
3. Confirm that the integration provides `DATABASE_URL`.
4. Redeploy the project.

Vercel detects the Flask `app` exported from `app.py`; no custom build command
or `vercel.json` file is required.
