import React, { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload } from "lucide-react";
import { uploadDocument } from "../utils/api";

const ACCEPT = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/markdown": [".md"],
  "text/plain": [".txt"],
};

export default function FileUpload({ onUploaded, onError }) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState("");

  const onDrop = useCallback(
    async (files) => {
      if (!files.length) return;
      const file = files[0];
      setUploading(true);
      setProgress(`Uploading ${file.name}...`);
      try {
        const doc = await uploadDocument(file);
        setProgress("");
        onUploaded(doc);
      } catch (err) {
        setProgress("");
        onError(err.message);
      } finally {
        setUploading(false);
      }
    },
    [onUploaded, onError]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024,
    disabled: uploading,
  });

  return (
    <div>
      <div
        {...getRootProps()}
        className={`dropzone ${isDragActive ? "dropzone--active" : ""}`}
      >
        <input {...getInputProps()} />
        <Upload size={28} className="dropzone__icon" />
        <div className="dropzone__text">
          <strong>Drop a file</strong> or click to upload
        </div>
        <div className="dropzone__hint">PDF, DOCX, MD, TXT — up to 50 MB</div>
      </div>
      {uploading && (
        <div className="upload-progress">
          <div className="upload-progress__bar-bg">
            <div
              className="upload-progress__bar"
              style={{ width: "60%" }}
            />
          </div>
          <div className="upload-progress__text">{progress}</div>
        </div>
      )}
    </div>
  );
}
