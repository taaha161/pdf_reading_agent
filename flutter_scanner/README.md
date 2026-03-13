# Flutter Scanner Embed

This Flutter web app provides the **results table** and **Validate AI** (GenUI) experience for the PDF reading agent. It is embedded in the React scanner page via an iframe.

## Development

```bash
flutter pub get
flutter run -d chrome
```

When running standalone, pass query params for the backend: `?apiBase=http://localhost:8000&jobId=<uuid>`.

## Build for production (embed in React)

```bash
flutter build web --base-href "/flutter-scanner/"
```

Then copy the build output to the frontend's public folder so Vite serves it:

```bash
cp -R build/web/* ../frontend/public/flutter-scanner/
```

The React app loads the embed at `/flutter-scanner/?jobId=...&apiBase=...` and sends the auth token via `postMessage` after load.

## Features

- **Results table**: Loads job data from `GET /api/jobs/:id`, supports inline edit (PATCH), CSV download.
- **Validate AI**: GenUI-backed chat that sends messages to `POST /api/jobs/:id/validate`. When the backend returns `transactions_updated`, the table updates and the confirmation message is shown in the conversation.
