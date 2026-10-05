import { useEffect, useRef, useState } from 'react'
import { enrollEmployee } from '../services/api'

interface EnrollmentTabProps {
  onEnrolled: () => void
}

type SubmissionMessage = { type: 'success' | 'error'; text: string } | null

function nameFromFilename(filename: string): string {
  const withoutExtension = filename.replace(/\.[^.]+$/, '')
  return withoutExtension
    .replace(/[-_]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function EnrollmentTab({ onEnrolled }: EnrollmentTabProps) {
  const [name, setName] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [consented, setConsented] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState<SubmissionMessage>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  const selectFile = (selectedFile: File) => {
    if (!['image/jpeg', 'image/png'].includes(selectedFile.type)) {
      setMessage({ type: 'error', text: 'Choose a JPG or PNG image.' })
      return
    }
    if (selectedFile.size > 5 * 1024 * 1024) {
      setMessage({ type: 'error', text: 'The image must be 5 MB or smaller.' })
      return
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setFile(selectedFile)
    setPreviewUrl(URL.createObjectURL(selectedFile))
    if (!name.trim()) setName(nameFromFilename(selectedFile.name))
    setMessage(null)
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!file || !name.trim() || !consented) return
    setSubmitting(true)
    setMessage(null)
    try {
      const employee = await enrollEmployee(name.trim(), file)
      setMessage({
        type: 'success',
        text: `${employee.name} was enrolled successfully as ${employee.employee_id}.`,
      })
    } catch (error) {
      setMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Enrollment failed.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="panel" aria-labelledby="enrollment-title">
      <div className="panel-header">
        <div>
          <h2 id="enrollment-title">Enroll an employee</h2>
          <p>Add one clear, front-facing photo for reliable recognition.</p>
        </div>
        <span className="step-pill">One face only</span>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="form-fields">
            <label className="field-label" htmlFor="employee-name">
              Employee name
            </label>
            <input
              id="employee-name"
              className="text-input"
              value={name}
              maxLength={120}
              placeholder="e.g. Alice Nguyen"
              autoComplete="off"
              onChange={(event) => setName(event.target.value)}
            />
            <p className="field-help">
              We prefill this from the filename. You can edit it before saving.
            </p>

            <label className="consent-box">
              <input
                type="checkbox"
                checked={consented}
                onChange={(event) => setConsented(event.target.checked)}
              />
              <span>
                I confirm the employee has consented to storing their biometric face
                encoding for attendance.
              </span>
            </label>

            <button
              className="primary-button"
              type="submit"
              disabled={!file || !name.trim() || !consented || submitting}
            >
              {submitting ? <span className="spinner" /> : null}
              {submitting ? 'Encoding face…' : 'Enroll employee'}
            </button>

            {message ? (
              <div className={`message ${message.type}`} role="status">
                {message.text}
                {message.type === 'success' ? (
                  <button className="message-action" type="button" onClick={onEnrolled}>
                    Open attendance camera →
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>

          <label
            className={`upload-zone${dragging ? ' dragging' : ''}${previewUrl ? ' has-preview' : ''}`}
            htmlFor="face-image"
            onDragEnter={(event) => {
              event.preventDefault()
              setDragging(true)
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault()
              setDragging(false)
              const droppedFile = event.dataTransfer.files[0]
              if (droppedFile) selectFile(droppedFile)
            }}
          >
            <input
              ref={inputRef}
              id="face-image"
              type="file"
              accept="image/jpeg,image/png,.jpg,.jpeg,.png"
              onChange={(event) => {
                const selectedFile = event.target.files?.[0]
                if (selectedFile) selectFile(selectedFile)
              }}
            />
            {previewUrl && file ? (
              <>
                <img className="image-preview" src={previewUrl} alt="Employee preview" />
                <span className="preview-overlay">
                  <span>{file.name}</span>
                  <span>Change photo</span>
                </span>
              </>
            ) : (
              <div className="upload-copy">
                <span className="upload-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <path d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 14.5V19h14v-4.5" />
                  </svg>
                </span>
                <strong>Drop an image here or choose a file</strong>
                <span>JPG or PNG · Maximum 5 MB</span>
              </div>
            )}
          </label>
        </div>
      </form>
    </section>
  )
}
