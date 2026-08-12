import { UserLayout } from "./layouts/UserLayout";
import { ChatPage } from "./pages/user/Chat";

export default function App() {
  return (
    <UserLayout>
      <ChatPage />
    </UserLayout>
  );
}
