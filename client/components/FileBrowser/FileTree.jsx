import React, { useState, useCallback } from "react";
import { FileTreeNode } from "./FileTreeNode";
import { ContextMenu } from "./ContextMenu";
import { UploadZone } from "./UploadZone";

export function FileTree({ userId, token, workspaceRoot, onInsertPath }) {
  const [tree, setTree] = useState({});
  const [expandedPaths, setExpandedPaths] = useState(new Set());
  const [contextMenu, setContextMenu] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadDirectory = useCallback(async (path) => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/files/list?path=${encodeURIComponent(path)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to load directory");
      const items = await res.json();
      setTree((prev) => ({ ...prev, [path]: items }));
    } catch (err) {
      console.error("Load directory error:", err);
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  const handleToggle = useCallback((path, isDir) => {
    if (!isDir) return;

    const newExpanded = new Set(expandedPaths);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
      // Load children if not already loaded
      if (!tree[path]) {
        loadDirectory(path);
      }
    }
    setExpandedPaths(newExpanded);
  }, [expandedPaths, tree, loadDirectory]);

  const handleContextMenu = useCallback((e, path, isDir) => {
    e.preventDefault();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      path,
      isDir,
    });
  }, []);

  const handleCloseContextMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  const handleRefresh = useCallback(() => {
    // Reload all expanded paths
    expandedPaths.forEach((path) => {
      loadDirectory(path);
    });
    // Also reload root
    loadDirectory(userId);
  }, [expandedPaths, loadDirectory, userId]);

  // Initial load
  React.useEffect(() => {
    loadDirectory(userId);
  }, [userId, loadDirectory]);

  const rootItems = tree[userId] || [];

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200">
        <span className="font-semibold text-gray-700">Files</span>
        <button
          onClick={handleRefresh}
          className="p-1 text-gray-500 hover:text-gray-700"
          title="Refresh"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M23 4v6h-6M1 20v-6h6" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
        </button>
      </div>

      {/* Upload zone */}
      <UploadZone userId={userId} token={token} onUpload={() => loadDirectory(userId)} />

      {/* File tree */}
      <div className="flex-1 overflow-y-auto p-2">
        {isLoading && rootItems.length === 0 ? (
          <div className="p-4 text-center text-gray-500 text-sm">Loading...</div>
        ) : rootItems.length === 0 ? (
          <div className="p-4 text-center text-gray-500 text-sm">No files yet</div>
        ) : (
          <div className="space-y-0.5">
            {rootItems.map((item) => (
              <FileTreeNode
                key={item.path}
                item={item}
                depth={0}
                expandedPaths={expandedPaths}
                tree={tree}
                onToggle={handleToggle}
                onContextMenu={handleContextMenu}
                onInsertPath={onInsertPath}
              />
            ))}
          </div>
        )}
      </div>

      {/* Context menu */}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          path={contextMenu.path}
          isDir={contextMenu.isDir}
          token={token}
          workspaceRoot={workspaceRoot}
          onClose={handleCloseContextMenu}
          onInsertPath={onInsertPath}
          onRefresh={() => {
            loadDirectory(userId);
            handleCloseContextMenu();
          }}
        />
      )}
    </div>
  );
}