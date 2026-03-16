import { useCallback, useRef, useState } from 'react'

interface UploadAreaProps {
  accept?: string
  multiple?: boolean
  onFiles: (files: File[]) => void
  label?: string
  hint?: string
  loading?: boolean
}

export default function UploadArea({
  accept,
  multiple = false,
  onFiles,
  label = 'Upload File',
  hint,
  loading = false,
}: UploadAreaProps) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return
      onFiles(Array.from(files))
    },
    [onFiles]
  )

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(true)
  }

  const onDragLeave = () => setDragging(false)

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  return (
    <div
      className={`upload-area cursor-pointer transition-all duration-200 ${
        dragging ? 'border-primary bg-primary-light' : ''
      } ${loading ? 'opacity-60 pointer-events-none' : ''}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />

      <div className="flex flex-col items-center gap-2 pointer-events-none">
        {loading ? (
          <svg
            className="animate-spin h-8 w-8 text-primary"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          <svg
            className={`h-8 w-8 ${dragging ? 'text-primary' : 'text-text-tertiary'}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
        )}

        <p className={`text-sm font-semibold ${dragging ? 'text-primary' : 'text-text-secondary'}`}>
          {loading ? 'Uploading...' : label}
        </p>
        {hint && <p className="text-xs text-text-tertiary">{hint}</p>}
        {!loading && (
          <p className="text-xs text-text-tertiary">
            or{' '}
            <span className="text-primary font-semibold underline-offset-2 hover:underline">
              browse files
            </span>
          </p>
        )}
      </div>
    </div>
  )
}
