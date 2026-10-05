import { useCallback, useEffect, useState } from 'react'
import { getEmployees } from '../services/api'
import type { EmployeeAttendance } from '../types/face'
import { useCameraRecognition } from '../hooks/useCameraRecognition'
import { CameraView } from './CameraView'
import { EmployeeList } from './EmployeeList'

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
    </section>
  )
}
