import { mockChatService } from "./mock/mockChatService";
import { httpChatService } from "./http/httpChatService";

/**
 * This is the ONLY file the rest of the app imports from.
 *
 * While there's no backend, VITE_API_BASE_URL is unset, so every call
 * is routed to the in-memory mock. Once the backend is ready:
 *
 *   1. Add VITE_API_BASE_URL=https://your-backend-url to a .env file
 *   2. Nothing else changes — components already call `chatService`,
 *      not the mock or http implementation directly.
 *
 * See README.md → "Connecting the real backend" for the full checklist.
 */
const useMock = !import.meta.env.VITE_API_BASE_URL;

export const chatService = useMock ? mockChatService : httpChatService;
