import React, { useCallback } from "react";

export function FileTreeNode({ item, depth, expandedPaths, tree, onToggle, onContextMenu, onInsertPath }) {
  const isExpanded = expandedPaths.has(item.path);
  const children = tree[item.path] || [];
  const hasChildren = item.is_dir && children.length > 0;

  const handleClick = useCallback(() => {
    onToggle(item.path, item.is_dir);
  }, [item, onToggle]);

  const handleContextMenu = useCallback((e) => {
    onContextMenu(e, item.path, item.is_dir);
  }, [item, onContextMenu]);

  const paddingLeft = depth * 16 + 8;

  return (
    <div>
      <div
        className="flex items-center gap-1 px-2 py-1 rounded hover:bg-gray-100 cursor-pointer group"
        style={{ paddingLeft }}
        onClick={handleClick}
        onContextMenu={handleContextMenu}
      >
        {/* Expand arrow for directories */}
        {item.is_dir ? (
          <span className="w-4 h-4 flex items-center justify-center text-xs text-gray-500">
            {isExpanded ? "▼" : "▶"}
          </span>
        ) : (
          <span className="w-4 h-4 flex items-center justify-center text-xs text-gray-400">•</span>
        )}

        {/* Icon */}
        <span className="text-sm">{item.is_dir ? "📁" : "📄"}</span>

        {/* Name */}
        <span className="flex-1 text-sm text-gray-700 truncate">{item.name}</span>

        {/* File size for non-directories */}
        {!item.is_dir && (
          <span className="text-xs text-gray-400 opacity-0 group-hover:opacity-100">
            {item.size ? formatSize(item.size) : ""}
          </span>
        )}
      </div>

      {/* Children */}
      {item.is_dir && isExpanded && children.length > 0 && (
        <div>
          {children.map((child) => (
            <FileTreeNode
              key={child.path}
              item={child}
              depth={depth + 1}
              expandedPaths={expandedPaths}
              tree={tree}
              onToggle={onToggle}
              onContextMenu={onContextMenu}
              onInsertPath={onInsertPath}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function formatSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`;
}