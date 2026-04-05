import { useEffect, useState } from "react";
import {
  captureFingerprint,
  deleteUser,
  enrollUser,
  fetchAttendance,
  fetchHealth,
  fetchUsers,
  verifyFingerprint,
} from "./api";

const initialRegistration = {
  id: "",
  name: "",
  fingerprintTemplate: "",
};

function App() {
  const [activeTab, setActiveTab] = useState("register");
  const [registration, setRegistration] = useState(initialRegistration);
  const [attendanceForm, setAttendanceForm] = useState({ id: "" });
  const [attendanceData, setAttendanceData] = useState({ records: [], summary: null });
  const [users, setUsers] = useState([]);
  const [health, setHealth] = useState(null);
  const [message, setMessage] = useState({ type: "", text: "" });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [usersResult, attendanceResult, healthResult] = await Promise.all([
        fetchUsers(),
        fetchAttendance(),
        fetchHealth(),
      ]);
      setUsers(usersResult.users || []);
      setAttendanceData({
        records: attendanceResult.records || [],
        summary: attendanceResult.summary || null,
      });
      setHealth(healthResult);
    } catch (error) {
      setMessage({
        type: "error",
        text: readError(error, "Unable to load initial data. Check whether the backend is running."),
      });
    }
  };

  const handleCaptureForEnrollment = async () => {
    if (!registration.id || !registration.name) {
      setMessage({ type: "error", text: "Enter both user ID and name before scanning." });
      return;
    }

    setLoading(true);
    setMessage({ type: "", text: "" });

    try {
      const result = await captureFingerprint({
        userId: registration.id,
        name: registration.name,
      });
      setRegistration((current) => ({
        ...current,
        fingerprintTemplate: result.template,
      }));
      setMessage({
        type: "success",
        text: `Fingerprint captured successfully using ${result.scannerSource}.`,
      });
    } catch (error) {
      setMessage({ type: "error", text: readError(error, "Fingerprint capture failed.") });
    } finally {
      setLoading(false);
    }
  };

  const handleEnroll = async (event) => {
    event.preventDefault();
    if (!registration.fingerprintTemplate) {
      setMessage({ type: "error", text: "Capture a fingerprint before submitting enrollment." });
      return;
    }

    setLoading(true);
    setMessage({ type: "", text: "" });

    try {
      const result = await enrollUser(registration);
      setRegistration(initialRegistration);
      setMessage({
        type: "success",
        text: `Enrollment complete for ${result.user.name} (${result.user.id}).`,
      });
      await refreshUsersAndAttendance();
    } catch (error) {
      setMessage({ type: "error", text: readError(error, "Enrollment failed.") });
    } finally {
      setLoading(false);
    }
  };

  const handleCaptureForAttendance = async () => {
    if (!attendanceForm.id) {
      setMessage({ type: "error", text: "Select or enter a user ID before scanning." });
      return;
    }

    setLoading(true);
    setMessage({ type: "", text: "" });

    try {
      const captureResult = await captureFingerprint({ userId: attendanceForm.id });
      // Verification stays server-side so the browser never handles matching logic directly.
      const verifyResult = await verifyFingerprint({
        id: attendanceForm.id,
        fingerprintTemplate: captureResult.template,
      });

      setMessage({
        type: "success",
        text: `${verifyResult.user.name} verified successfully. Attendance marked at ${formatDate(
          verifyResult.attendance.timestamp
        )}.`,
      });
      await refreshUsersAndAttendance();
    } catch (error) {
      setMessage({ type: "error", text: readError(error, "Verification failed.") });
    } finally {
      setLoading(false);
    }
  };

  const refreshUsersAndAttendance = async () => {
    const [usersResult, attendanceResult] = await Promise.all([fetchUsers(), fetchAttendance()]);
    setUsers(usersResult.users || []);
    setAttendanceData({
      records: attendanceResult.records || [],
      summary: attendanceResult.summary || null,
    });
  };

  const handleDeleteUser = async (user) => {
    const confirmed = window.confirm(
      `Delete ${user.name} (${user.id}) and all of their attendance records?`
    );
    if (!confirmed) {
      return;
    }

    setLoading(true);
    setMessage({ type: "", text: "" });

    try {
      const result = await deleteUser(user.id);
      setMessage({
        type: "success",
        text: result.message,
      });
      if (attendanceForm.id === user.id) {
        setAttendanceForm({ id: "" });
      }
      await refreshUsersAndAttendance();
    } catch (error) {
      setMessage({ type: "error", text: readError(error, "Unable to delete user.") });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <header className="hero">
        <div>
          <h1>Attendance System</h1>
        </div>
        <div className="status-strip">
          <span>Backend: {health?.status || "Unknown"}</span>
          <span>Mode: {health?.mockScannerEnabled ? "Demo" : "Live"}</span>
        </div>
      </header>

      <main className="main-layout">
        <nav className="tab-list">
          <button
            className={activeTab === "register" ? "active" : ""}
            onClick={() => setActiveTab("register")}
          >
            Users
          </button>
          <button
            className={activeTab === "attendance" ? "active" : ""}
            onClick={() => setActiveTab("attendance")}
          >
            Attendance
          </button>
          <button
            className={activeTab === "records" ? "active" : ""}
            onClick={() => setActiveTab("records")}
          >
            Records
          </button>
        </nav>

        <section className="content">
        {message.text ? <div className={`message ${message.type}`}>{message.text}</div> : null}

        {activeTab === "register" ? (
          <section className="panel">
            <h2>Add User</h2>
            <form className="form-grid" onSubmit={handleEnroll}>
              <label>
                User ID
                <input
                  value={registration.id}
                  onChange={(event) => setRegistration({ ...registration, id: event.target.value })}
                  placeholder="USER001"
                />
              </label>
              <label>
                Name
                <input
                  value={registration.name}
                  onChange={(event) => setRegistration({ ...registration, name: event.target.value })}
                  placeholder="Alex Morgan"
                />
              </label>
              <label className="full-width">
                Fingerprint template
                <textarea
                  rows="5"
                  readOnly
                  value={registration.fingerprintTemplate}
                  placeholder="Template will appear here after scan"
                />
              </label>
              <div className="actions full-width">
                <button type="button" onClick={handleCaptureForEnrollment} disabled={loading}>
                  {loading ? "Scanning..." : "Scan"}
                </button>
                <button type="submit" className="secondary" disabled={loading}>
                  Save User
                </button>
              </div>
            </form>

            <div className="user-list">
              <div className="user-list-header">
                <h3>Saved Users</h3>
                <span>{users.length}</span>
              </div>
              {users.length === 0 ? (
                <p className="empty-copy">No users added yet.</p>
              ) : (
                users.map((user) => (
                  <div className="user-row" key={user.id}>
                    <div>
                      <strong>{user.name}</strong>
                      <p>
                        {user.id} | Added {formatDate(user.created_at)}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="danger"
                      disabled={loading}
                      onClick={() => handleDeleteUser(user)}
                    >
                      Delete
                    </button>
                  </div>
                ))
              )}
            </div>
          </section>
        ) : null}

        {activeTab === "attendance" ? (
          <section className="panel">
            <h2>Mark Attendance</h2>
            <div className="form-grid">
              <label className="full-width">
                Select user
                <select
                  value={attendanceForm.id}
                  onChange={(event) => setAttendanceForm({ id: event.target.value })}
                >
                  <option value="">Choose a user</option>
                  {users.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.name} ({user.id})
                    </option>
                  ))}
                </select>
              </label>
              <div className="actions full-width">
                <button onClick={handleCaptureForAttendance} disabled={loading}>
                  {loading ? "Checking..." : "Scan and Mark"}
                </button>
              </div>
            </div>

            {attendanceData.summary ? (
              <div className="stats-grid">
                <article className="stat-card">
                  <span>Total users</span>
                  <strong>{attendanceData.summary.total_users}</strong>
                </article>
                <article className="stat-card">
                  <span>Total attendance</span>
                  <strong>{attendanceData.summary.total_attendance}</strong>
                </article>
                <article className="stat-card">
                  <span>Today</span>
                  <strong>{attendanceData.summary.today_attendance}</strong>
                </article>
              </div>
            ) : null}
          </section>
        ) : null}

        {activeTab === "records" ? (
          <section className="panel">
            <h2>Attendance Records</h2>
            <div className="table-shell">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>User ID</th>
                    <th>Name</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {attendanceData.records.length === 0 ? (
                    <tr>
                      <td colSpan="4" className="empty-state">
                        No attendance records yet.
                      </td>
                    </tr>
                  ) : (
                    attendanceData.records.map((record) => (
                      <tr key={record.id}>
                        <td>{record.id}</td>
                        <td>{record.user_id}</td>
                        <td>{record.name}</td>
                        <td>{formatDate(record.timestamp)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}
        </section>
      </main>
    </div>
  );
}

function readError(error, fallback) {
  return error?.response?.data?.message || fallback;
}

function formatDate(value) {
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return value;
  }
}

export default App;
