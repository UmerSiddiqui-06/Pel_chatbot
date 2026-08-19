import { useState } from "react";
import { UserLayout } from "./layouts/UserLayout";
import { ChatPage } from "./pages/user/Chat";
import { SplashScreen } from "./components/branding/SplashScreen";

export default function App() {
  const [showSplash, setShowSplash] = useState(true);

  return (
    <>
      {showSplash && <SplashScreen onFinished={() => setShowSplash(false)} />}
      <UserLayout>
        <ChatPage />
      </UserLayout>
    </>
  );
}
