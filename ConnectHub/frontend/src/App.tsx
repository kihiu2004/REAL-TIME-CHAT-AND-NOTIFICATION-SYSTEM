import { AuthPage } from "./components/AuthPage";
import { AppShell } from "./components/AppShell";
import { Icon } from "./components/Icons";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ChatProvider } from "./context/ChatContext";
import { ToastProvider } from "./context/ToastContext";

function Splash() {
  return (
    <div className="splash">
      <div className="splash__mark">
        <Icon name="chat" size={30} />
      </div>
      <div className="splash__text">
        <strong>ConnectHub</strong>
        <span>Connecting to your conversations…</span>
      </div>
      <span className="spinner spinner--large" />
    </div>
  );
}

function Root() {
  const { status } = useAuth();

  if (status === "loading") return <Splash />;
  if (status === "anonymous") return <AuthPage />;

  return (
    <ChatProvider>
      <AppShell />
    </ChatProvider>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <Root />
      </ToastProvider>
    </AuthProvider>
  );
}
