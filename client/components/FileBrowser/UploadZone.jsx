import React, { useRef, useState, useCallback } from "react";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export function UploadZone({ userId, token, onUpload }) {
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const uploadFile = useCallback(async (file) => {
    if (file.size > MAX_FILE_SIZE) {
      alert(`File too large. Maximum size is ${MAX_FILE_SIZE / 1024 / 1024}MB`);
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("/api/files/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      onUpload();
    } catch (err) {
      console.error("Upload failed:", err);
      alert("File upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  }, [userId, token, onUpload]);

  const handleFileSelect = useCallback(async (files) => {
    if (!files || files.length === 0) return;
    for (const file of files) {
      await uploadFile(file);
    }
  }, [uploadFile]);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  return (
    <div
      className={`m-2 p-4 border-2 border-dashed rounded text-center transition-colors ${
        dragOver ? "border-blue-400 bg-blue-50" : "border-gray-300 hover:border-gray-400"
      }`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => handleFileSelect(e.target.files)}
      />
      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={isUploading}
        className="text-sm text-gray-600 hover:text-gray-800 disabled:opacity-50"
      >
        {isUploading ? "Uploading..." : "Drop files here or click to upload"}
      </button>
    </div>
  );
}