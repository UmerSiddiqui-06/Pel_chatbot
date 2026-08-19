# PEL AI — Knowledge Assistant (Chat Frontend)

User-facing chat interface for the PEL AI Knowledge Agent, built with **React + TypeScript + Vite + Tailwind CSS**, per the Frontend Requirements doc.

This is the **chat / User Portal only**. The Admin Portal is not included yet.

Right now there is no backend, so the app runs against an in-memory mock service
(`src/api/mock/mockChatService.ts`) that simulates network delay and returns
canned answers. Everything is structured so connecting a real backend later
is a small, contained change — see **"Connecting the real backend"** below.

---

## 1. Prerequisites

- [Node.js](https://nodejs.org) v18 or later (v20+ recommended)
- npm (comes with Node)

Check your versions:

```bash
node -v
npm -v
```

## 2. Setup

```bash
cd pel-ai-chat
npm install
npm run dev
```

Open the URL it prints (usually `http://localhost:5173`).

You should see the chat UI with three pre-loaded conversations (Warranty
Policy, Leave Policy, Product Info) in the sidebar. Try asking things like:

- "What's the warranty on the CoolPro AC?"
- "How many leaves do I get?"
- Anything else → you'll see the "couldn't find a confident answer" state

## 3. Available scripts

| Command           | What it does                                  |
|-------------------|------------------------------------------------|
| `npm run dev`     | Start the dev server with hot reload            |
| `npm run build`   | Type-check and build a production bundle to `dist/` |
| `npm run preview` | Serve the production build locally to sanity-check it |
| `npm run lint`    | Run the linter (oxlint)                         |

## 4. Project structure

```
src/
├── assets/              PEL logo
├── api/
│   ├── chatService.ts   the ONLY file components import from
│   ├── mock/             in-memory mock backend (active for now)
│   └── http/              real backend implementation (inactive until wired up)
├── components/
│   ├── chat/             message bubble, sidebar, composer, sources, typing indicator
│   └── ui/                generic button, etc.
├── hooks/
│   └── useChat.ts        all chat state + calls into chatService
├── layouts/
│   └── UserLayout.tsx    header/shell with PEL branding
├── pages/user/
│   └── Chat.tsx          composes the chat screen
└── types/
    └── chat.ts           shared types matching the backend API contract
```

## 5. Design notes

- Brand color `#007DC6` (sampled from the PEL logo) is registered as the
  `pel` color scale in `tailwind.config.js` (`pel-50` ... `pel-950`). Use
  `bg-pel-600`, `text-pel-700`, etc. rather than hardcoding hex values.
- Status/feedback colors use Tailwind's default `emerald`/`amber`/`red` —
  keep that convention if you add the Admin Portal later (documents,
  processing jobs, and data source statuses all use the same pattern).

---

## Connecting the real backend

When the backend team has an API available, matching the contract in
section 25 of the Frontend Requirements doc (`POST /chat`,
`GET /conversations`, etc.):

1. **Copy `.env.example` to `.env`** and set the base URL:

   ```
   VITE_API_BASE_URL=https://api.pel-ai.example.com
   ```

   That's it for the seam itself — `src/api/chatService.ts` automatically
   switches from the mock to `src/api/http/httpChatService.ts` the moment
   this variable is set. No component changes needed.

2. **Check the real response shapes against `src/types/chat.ts`.**
   If the backend's JSON doesn't match exactly (e.g. different field
   names), either adjust the types or map the response inside
   `httpChatService.ts` — keep that mapping contained to that one file.

3. **Wire up authentication.** `httpChatService.ts` has a `TODO` where the
   auth header goes. Once login exists (see step 4), attach the token
   there, e.g.:

   ```ts
   Authorization: `Bearer ${getAccessToken()}`
   ```

4. **Build the auth screens.** This build intentionally skipped
   `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` (section 4 of
   the requirements doc) since there's nothing to authenticate against
   yet. Once the backend exists, add `src/pages/auth/Login.tsx` and a
   simple session check that gates the chat UI, matching the wireframe
   already in the requirements doc.

5. **Remove or keep the mock.** You don't have to delete
   `src/api/mock/`. It's useful for local development and demos even
   after the backend exists — just don't let `VITE_API_BASE_URL` leak
   into production accidentally pointing at the wrong thing.

6. **Test the real error paths.** The mock always "succeeds" (aside from
   the deliberately-unhelpful fallback answer). Once real network calls
   are in play, verify:
   - A dropped connection shows the "Unable to send your message" error banner
     (already implemented in `useChat.ts` / `Chat.tsx`)
   - An expired session redirects to login rather than hanging
   - Slow responses still show the typing indicator correctly

7. **Next feature slice: the Admin Portal.** Once the chat + auth flow is
   solid against the real backend, the natural next build is the Admin
   Portal (Dashboard, Documents, FAQs, Data Sources, Processing Jobs,
   Activity Logs, Users & Roles, Settings) from sections 10-24 of the
   requirements doc — happy to scaffold that the same way when you're
   ready.
