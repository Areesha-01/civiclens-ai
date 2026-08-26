# CivicLens AI — Backend

Flask API that receives citizen civic reports and stores them in PostgreSQL.

## 1. Create a free PostgreSQL database (Neon.tech)

No local installation needed — this takes about 2 minutes.

1. Go to https://neon.tech and sign up (free)
2. Click "Create a project" — name it `civiclens`
3. Once created, find the **Connection String** (looks like
   `postgresql://user:password@ep-xxxx.neon.tech/civiclens?sslmode=require`)
4. Copy it

## 2. Set up environment variables

1. Copy `.env.example` to a new file named `.env`
2. Paste your Neon connection string into `DATABASE_URL`

## 3. Install dependencies and run

```bash
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
# or: venv\Scripts\activate    # Windows CMD

pip install -r requirements.txt
python app.py
```

Server runs at `http://localhost:5000`. The reports table is created
automatically on first run.

## 4. Test it

Open `http://localhost:5000/health` in your browser — you should see
`{"status": "ok", ...}`.

## Endpoints

- `POST /submit-report` — multipart form: `photo`, `description`, `category`, `lat`, `lng`
- `GET /reports` — returns all reports as JSON
- `GET /uploads/<filename>` — serves uploaded photos
