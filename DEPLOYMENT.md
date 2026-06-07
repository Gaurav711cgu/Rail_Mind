# Deployment Guide — RailMind Full-Stack

This guide outlines the steps to deploy the **FastAPI Backend on Hugging Face Spaces** and the **Vite React Frontend on Vercel**.

---

## 🏗️ Deployment Architecture

We split the application to optimize cost, compute, and startup performance:
1. **Hugging Face Spaces (Backend):** Hosts the FastAPI server in a persistent Docker container. It has a free tier with 16GB RAM and no CPU sleep restrictions, perfect for running NetworkX algorithms and caching scenario states.
2. **Vercel (Frontend):** Serves the static Vite React client globally via their high-speed Edge Network, providing instant page load times.

```
[Browser Client] 
       │
       ├───> (Loads HTML/JS assets) ───> [Vercel CDN Edge]
       │
       └───> (Fetches /api/v1/*) ──────> [Vercel Rewrite Rules] ───> [Hugging Face Spaces Docker Container]
```

---

## 🚀 Step 1: Deploying the Backend on Hugging Face Spaces

1. Create a free account at **[Hugging Face](https://huggingface.co/)**.
2. Click on your profile picture in the top-right corner and select **New Space**.
3. Configure your Space:
   * **Space Name:** `Rail_Mind` (e.g. results in endpoint `https://gaurav711-rail-mind.hf.space`)
   * **License:** `mit` (or preferred)
   * **Space SDK:** Select **Docker** (Very Important).
   * **Docker Template:** Select **Blank** (default).
   * **Space Hardware:** Select **CPU basic (Free)**.
   * **Visibility:** **Public** (required to allow Vercel API fetching).
4. Go to **Settings** > **Variables and Secrets** and configure the following:
   * **Environment Variables:**
     * `SCENARIO_MODE`: `True` *(Enables the presentation engine)*
   * **Secrets:**
     * `SECRET_KEY`: `SUPER_SECRET_SECURITY_HASH_KEY_RAILMIND_2026_GRAND_FINALS` *(Used for JWT signatures)*
5. Push the code inside the `backend/` folder to the Hugging Face Git remote repository (or upload files via the web interface: `Dockerfile`, `requirements.txt`, `app/`, and `scripts/` directly to the Space repository root).
6. Hugging Face will automatically detect the `Dockerfile`, build the container, seed the database, and expose port `7860` as the public endpoint.

---

## ⚡ Step 2: Deploying the Frontend on Vercel

We use a custom `vercel.json` file in the frontend root to proxy API calls in production:

1. Create a free account at **[Vercel](https://vercel.com/)**.
2. Click **Add New** > **Project** and import your Git repository.
3. Configure the Project Settings:
   * **Framework Preset:** Select **Vite** (Vercel will auto-detect this).
   * **Root Directory:** Set to `frontend` (Very Important).
   * **Build Command:** `npm run build`
   * **Output Directory:** `dist`
4. **Environment Variables:**
   * No environment variables are required! The [frontend/vercel.json](file:///Users/gauravkumarnayak/Desktop/resume/railmind/frontend/vercel.json) file handles proxy rewrites dynamically. 
   
   * *Note: If you change your Hugging Face Space name, update the destination URL in [vercel.json](file:///Users/gauravkumarnayak/Desktop/resume/railmind/frontend/vercel.json) to match your new Space endpoint before deploying.*
5. Click **Deploy**. Vercel will compile the React assets and host your dashboard on a public subdomain (e.g. `https://railmind-console.vercel.app`).

---

## 🔒 Verification & Handshake Check

Once both stages are complete, check the connection by loading:
`https://your-vercel-domain.vercel.app/health`

This should route to the backend `/health` endpoint and return:
```json
{
  "status": "healthy",
  "timestamp": "2026-06-07T19:24:15.123Z",
  "service": "RailMind",
  "version": "1.0.0",
  "scenario_mode": true
}
```
This confirms the proxy rewrite is active and the handshake has succeeded!
