import { useState } from "react";
import { UserLayout } from "./layouts/UserLayout";
import { ChatPage } from "./pages/user/Chat";
import { SplashScreen, type SplashMode } from "./components/branding/SplashScreen";
import { useTheme } from "./hooks/useTheme";

// Flip this to "fade" to try the quieter exit instead — both are fully
// built, this is the only line that decides which one ships.
const SPLASH_MODE: SplashMode = "disintegrate";

export default function App() {
  const [showSplash, setShowSplash] = useState(true);
  const { theme, toggleTheme } = useTheme();

  return (
    <>
      {showSplash && (
        <SplashScreen theme={theme} mode={SPLASH_MODE} onFinished={() => setShowSplash(false)} />
      )}
      <UserLayout theme={theme} toggleTheme={toggleTheme}>
        <ChatPage />
      </UserLayout>
    </>
  );
}
