import { useCallback, useEffect, useState } from 'react'
import { getEmployees } from '../services/api'
import type { EmployeeAttendance } from '../types/face'
import { useCameraRecognition } from '../hooks/useCameraRecognition'
import { CameraView } from './CameraView'
import { EmployeeList } from './EmployeeList'

function formatAttendanceTime(value: string): string {
  return new Intl.DateTimeFormat('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(value))
}

export function AttendanceTab() {
  const [employees, setEmployees] = useState<EmployeeAttendance[]>([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState<string | null>(null)

  const refreshEmployees = useCallback(async (signal?: AbortSignal) => {
    try {
      const result = await getEmployees(signal)
      setEmployees(result)
      setListError(null)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      setListError(error instanceof Error ? error.message : 'Could not load employees.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    // Loading from the API is the external synchronization owned by this effect.
    // oxlint-disable-next-line react/set-state-in-effect
    void refreshEmployees(controller.signal)
    const interval = window.setInterval(() => void refreshEmployees(), 5000)
    return () => {
      controller.abort()
      window.clearInterval(interval)
    }
  }, [refreshEmployees])

  const camera = useCameraRecognition({
    recognitionEnabled: employees.length > 0,
    onAttendanceUpdated: refreshEmployees,
  })
  const recognizedEmployees = new Map<string, string>()
  for (const face of camera.faces) {
    if (face.employee_id) recognizedEmployees.set(face.employee_id, face.name)
  }
  const showAttendanceResults =
    camera.recognitionState !== 'backend-error' &&
    camera.recognitionState !== 'spoof-detected' &&
    recognizedEmployees.size > 0

  return (
    <section className="panel" aria-labelledby="attendance-title">
      <div className="panel-header">
        <div>
          <h2 id="attendance-title">Attendance camera</h2>
          <p>Employees are checked in automatically after a verified match.</p>
        </div>
        <span className="status-pill">Live session</span>
      </div>

      <div className="camera-layout">
        <CameraView
          videoRef={camera.videoRef}
          cameraState={camera.cameraState}
          recognitionState={camera.recognitionState}
          faces={camera.faces}
          frameSize={camera.frameSize}
          error={camera.error}
          hasEmployees={employees.length > 0}
          onStart={camera.startCamera}
          onStop={camera.stopCamera}
        />
        <EmployeeList employees={employees} loading={loading} error={listError} />
      </div>

      {showAttendanceResults ? (
        <div className="attendance-confirmations" aria-live="polite">
          {[...recognizedEmployees].map(([employeeId, name]) => {
            const employee = employees.find((item) => item.employee_id === employeeId)
            const arrivedAt = employee?.is_arrive ? employee.arrived_at : null

            return (
              <div className="attendance-confirmation" key={employeeId}>
                <span className="attendance-confirmation-check" aria-hidden="true">
                  <svg viewBox="0 0 24 24">
                    <path d="m6.5 12.5 3.5 3.5 7.5-8" />
                  </svg>
                </span>
                <div className="attendance-confirmation-copy">
                  <strong>{name}</strong>
                  <span>
                    {arrivedAt
                      ? `Checked in at ${formatAttendanceTime(arrivedAt)}`
                      : 'Recording attendance time…'}
                  </span>
                </div>
                <span className="attendance-confirmation-badge">
                  {arrivedAt ? 'Checked in' : 'Saving'}
                </span>
              </div>
            )
          })}
        </div>
      ) : null}
    </section>
  )
}
