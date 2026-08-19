import { useState } from "react";
import { UserLayout } from "./layouts/UserLayout";
import { ChatPage } from "./pages/user/Chat";
import { SplashScreen } from "./components/branding/SplashScreen";
import { useTheme } from "./hooks/useTheme";

export default function App() {
  const [showSplash, setShowSplash] = useState(true);
  const { theme, toggleTheme } = useTheme();

  return (
    <>
      {showSplash && <SplashScreen theme={theme} onFinished={() => setShowSplash(false)} />}
      <UserLayout theme={theme} toggleTheme={toggleTheme}>
        <ChatPage />
      </UserLayout>
    </>
  );
}
