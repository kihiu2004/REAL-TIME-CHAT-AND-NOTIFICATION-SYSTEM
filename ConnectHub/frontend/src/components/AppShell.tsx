import { useState } from "react";

import { useChat } from "../context/ChatContext";
import { ChatWindow } from "./ChatWindow";
import { NewChatModal } from "./NewChatModal";
import { NotificationsPanel } from "./NotificationsPanel";
import { ProfileModal } from "./ProfileModal";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  const { activeId, selectConversation } = useChat();
  const [newChatOpen, setNewChatOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <div className={`app-shell ${activeId ? "app-shell--conversation" : ""}`}>
      <Sidebar
        onNewChat={() => setNewChatOpen(true)}
        onProfile={() => setProfileOpen(true)}
      />
      <ChatWindow
        onBack={() => void selectConversation(null)}
        onNewChat={() => setNewChatOpen(true)}
      />
      <NotificationsPanel />
      <NewChatModal open={newChatOpen} onClose={() => setNewChatOpen(false)} />
      <ProfileModal open={profileOpen} onClose={() => setProfileOpen(false)} />
    </div>
  );
}
