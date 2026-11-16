import { Icon } from "./Icons";

export function EmptyState({ onNewChat }: { onNewChat: () => void }) {
  return (
    <div className="empty-chat">
      <div className="empty-chat__art" aria-hidden="true">
        <span className="empty-chat__bubble empty-chat__bubble--one">
          <Icon name="chat" size={22} />
        </span>
        <span className="empty-chat__bubble empty-chat__bubble--two">
          <Icon name="bell" size={18} />
        </span>
        <span className="empty-chat__bubble empty-chat__bubble--three">
          <Icon name="users" size={18} />
        </span>
      </div>
      <h2>Pick a conversation</h2>
      <p>
        Choose a chat on the left, or start a new direct or group conversation.
        New messages and notifications arrive here instantly.
      </p>
      <button type="button" className="button button--primary" onClick={onNewChat}>
        <Icon name="plus" size={17} />
        New conversation
      </button>
      <div className="empty-chat__hints">
        <span>
          <Icon name="checkCheck" size={15} /> Read receipts
        </span>
        <span>
          <Icon name="spark" size={15} /> Live typing
        </span>
        <span>
          <Icon name="bell" size={15} /> Instant alerts
        </span>
      </div>
    </div>
  );
}
