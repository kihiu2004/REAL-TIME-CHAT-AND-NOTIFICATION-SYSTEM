import { useEffect, useState, type FormEvent } from "react";

import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { formatRelative } from "../lib/format";
import { Avatar } from "./Avatar";
import { Icon } from "./Icons";
import { Modal } from "./Modal";

export function ProfileModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { user, updateUser } = useAuth();
  const { toast } = useToast();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [picture, setPicture] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !user) return;
    setFullName(user.full_name);
    setEmail(user.email);
    setPicture(user.profile_picture_url ?? "");
    setError(null);
  }, [open, user]);

  if (!user) return null;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (saving) return;
    setError(null);

    if (!fullName.trim()) {
      setError("Full name cannot be empty.");
      return;
    }
    if (!email.trim()) {
      setError("Email cannot be empty.");
      return;
    }
    if (picture.trim() && !/^https?:\/\//i.test(picture.trim())) {
      setError("Picture URL must start with http:// or https://");
      return;
    }

    setSaving(true);
    try {
      const updated = await api.updateProfile({
        full_name: fullName.trim(),
        email: email.trim(),
        profile_picture_url: picture.trim() || null,
      });
      updateUser(updated);
      toast("Profile updated", "success");
      onClose();
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : "Could not update your profile",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="My profile"
      subtitle="How you appear to other members"
      icon={<Icon name="user" size={19} />}
      size="md"
    >
      <div className="profile-preview">
        <Avatar
          name={fullName || user.full_name}
          src={picture || user.profile_picture_url}
          size="xl"
          online
        />
        <div>
          <h3>{fullName || user.full_name}</h3>
          <p>@{user.username}</p>
          <span className={`status-badge status-badge--${user.account_status}`}>
            {user.account_status}
          </span>
        </div>
        <div className="profile-preview__meta">
          <span>Member {formatRelative(user.created_at)}</span>
          <span>{user.is_online ? "Online" : "Offline"}</span>
        </div>
      </div>

      {error && (
        <div className="form-error" role="alert">
          <Icon name="warning" size={16} />
          <span>{error}</span>
        </div>
      )}

      <form className="profile-form" onSubmit={submit}>
        <label className="field">
          <span className="field__label">Full name</span>
          <span className="field__control">
            <Icon name="user" size={17} />
            <input
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              maxLength={120}
              placeholder="Your name"
            />
          </span>
        </label>

        <label className="field">
          <span className="field__label">Email</span>
          <span className="field__control">
            <Icon name="mail" size={17} />
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
            />
          </span>
        </label>

        <label className="field">
          <span className="field__label">Profile picture URL</span>
          <span className="field__control">
            <Icon name="image" size={17} />
            <input
              value={picture}
              onChange={(event) => setPicture(event.target.value)}
              placeholder="https://example.com/avatar.png"
              maxLength={500}
            />
          </span>
        </label>

        <div className="profile-form__facts">
          <span>
            <Icon name="at" size={14} /> Username cannot be changed
          </span>
          <span>
            <Icon name="lock" size={14} /> Password is stored as a bcrypt hash
          </span>
        </div>

        <div className="modal__footer modal__footer--inline">
          <button type="button" className="button button--ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            className="button button--primary"
            disabled={saving}
          >
            {saving ? <span className="spinner" /> : <Icon name="check" size={16} />}
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
