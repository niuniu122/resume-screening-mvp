# Frontend Static Export Deployment

This frontend is configured for Next.js static export and is intended to be hosted as static assets on OSS/CDN.

## Build Output

Run the production build from `frontend/`:

```bash
npm run build
```

With `output: "export"` enabled, Next.js writes the static site to `frontend/out/`.

## Hosting Notes

- Upload the contents of `frontend/out/` to OSS or another static object store.
- Put a CDN in front of the bucket for faster access and better stability.
- Set the API base URL at build time with `NEXT_PUBLIC_API_BASE_URL`.
- Keep the backend CORS allowlist limited to the deployed frontend origin.

## Required Environment Variable

Create a production env file based on `frontend/.env.production.example`:

```bash
NEXT_PUBLIC_API_BASE_URL=https://api.example.com
```

## Local Preview

If you want to verify the exported files locally, serve `frontend/out/` with any static server of your choice.

## Integration Checklist

- Confirm the API domain is reachable from the browser.
- Confirm the backend allows the frontend origin in CORS.
- Confirm uploaded resume files and generated reports are handled by the backend, not by Next.js.
- Confirm the deployed site is served over HTTPS.
