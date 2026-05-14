import React, { useEffect, useRef, useCallback } from "react";

export function ContextMenu({ x, y, path, isDir, token, workspaceRoot, onClose, onInsertPath, onRefresh }) {
  const menuRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  const handleAddToChat = useCallback(() => {
    const absolutePath = workspaceRoot ? `${workspaceRoot}/${path}` : path;
    onInsertPath(absolutePath);
    onClose();
  }, [path, workspaceRoot, onInsertPath, onClose]);

  const handleDownload = useCallback(async () => {
    try {
      const res = await fetch(`/api/files/download?path=${encodeURIComponent(path)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = path.split("/").pop();
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Download error:", err);
      alert("Failed to download");
    }
    onClose();
  }, [path, token, onClose]);

  const handleDelete = useCallback(async () => {
    if (!confirm("Delete this file?")) return;
    try {
      const res = await fetch(`/api/files?path=${encodeURIComponent(path)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Delete failed");
      onRefresh();
    } catch (err) {
      console.error("Delete error:", err);
      alert("Failed to delete");
    }
    onClose();
  }, [path, token, onRefresh, onClose]);

  const handleRename = useCallback(async () => {
    const newName = prompt("Enter new name:", path.split("/").pop());
    if (!newName || newName === path.split("/").pop()) return;

    const oldPath = path;
    const parts = path.split("/");
    parts[parts.length - 1] = newName;
    const newPath = parts.join("/");

    try {
      const res = await fetch("/api/files/rename", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ old_path: oldPath, new_path: newPath }),
      });
      if (!res.ok) throw new Error("Rename failed");
      onRefresh();
    } catch (err) {
      console.error("Rename error:", err);
      alert("Failed to rename");
    }
    onClose();
  }, [path, token, onRefresh, onClose]);

  const handleMkdir = useCallback(async () => {
    const name = prompt("Enter folder name:");
    if (!name) return;

    const newPath = path ? `${path}/${name}` : `${name}`;
    try {
      const res = await fetch("/api/files/mkdir", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ path: newPath }),
      });
      if (!res.ok) throw new Error("Mkdir failed");
      onRefresh();
    } catch (err) {
      console.error("Mkdir error:", err);
      alert("Failed to create folder");
    }
    onClose();
  }, [path, token, onRefresh, onClose]);

  // Position menu, keep it on screen
  const style = {
    position: "fixed",
    left: Math.min(x, window.innerWidth - 200),
    top: Math.min(y, window.innerHeight - 200),
  };

  return (
    <div
      ref={menuRef}
      style={style}
      className="bg-white border border-gray-200 rounded shadow-lg py-1 w-48 z-50"
    >
      <MenuItem onClick={handleAddToChat}>Add to chat</MenuItem>
      <MenuItem onClick={handleDownload}>Download</MenuItem>
      <Divider />
      <MenuItem onClick={handleRename}>Rename</MenuItem>
      {isDir && <MenuItem onClick={handleMkdir}>New folder</MenuItem>}
      <MenuItem onClick={handleDelete} danger>Delete</MenuItem>
    </div>
  );
}

function MenuItem({ children, onClick, danger }) {
  return (
    <button
      onClick={onClick}
      className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-100 ${
        danger ? "text-red-600" : "text-gray-700"
      }`}
    >
      {children}
    </button>
  );
}

function Divider() {
  return <div className="border-t border-gray-100 my-1" />;
}