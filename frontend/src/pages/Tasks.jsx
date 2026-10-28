import { useEffect, useState } from 'react'
import { api } from '../api'

const TASK_STATUSES = ['todo', 'doing', 'done']
const FILTERS = ['all', 'open', 'done']

export default function Tasks() {
  const [tasks, setTasks] = useState(null)
  const [filter, setFilter] = useState('all')
  const [openCount, setOpenCount] = useState(0)
  const [doneCount, setDoneCount] = useState(0)
  const [title, setTitle] = useState('')
  const [sourceGap, setSourceGap] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function load(currentFilter) {
    api.tasks(currentFilter)
      .then((data) => {
        setTasks(data.tasks)
        setOpenCount(data.open_count)
        setDoneCount(data.done_count)
      })
      .catch((err) => setError(err.message))
  }

  useEffect(() => load(filter), [filter])

  async function handleCreate(event) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await api.createTask(title, sourceGap)
      setTitle('')
      setSourceGap('')
      load(filter)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function changeTask(task, fields) {
    setError('')
    try {
      await api.updateTask(task.id, fields)
      load(filter)
    } catch (err) {
      setError(err.message)
    }
  }

  // The HTML toggle rule: done -> back to todo, anything else -> done.
  function toggle(task) {
    changeTask(task, { status: task.status === 'done' ? 'todo' : 'done' })
  }

  return (
    <section>
      <h1>Gap tasks</h1>
      <p className="muted">
        {openCount} open · {doneCount} done. Tasks pushed from JD gaps and
        interview weakest areas land here; duplicates are skipped.
      </p>

      <form onSubmit={handleCreate}>
        <label>
          Task
          <input value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label>
          Why this task (optional)
          <textarea value={sourceGap} onChange={(e) => setSourceGap(e.target.value)} rows={2} />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? 'Saving…' : 'Add task'}
        </button>
      </form>
      {error && <p className="error">{error}</p>}

      <p>
        {FILTERS.map((f) => (
          <span key={f}>
            {f === filter ? (
              <strong>{f}</strong>
            ) : (
              <button onClick={() => setFilter(f)}>{f}</button>
            )}{' '}
          </span>
        ))}
      </p>

      {tasks === null ? (
        <p>Loading…</p>
      ) : tasks.length === 0 ? (
        <p className="muted">Nothing here yet.</p>
      ) : (
        <ul className="list">
          {tasks.map((task) => (
            <li key={task.id} className="card">
              <label>
                <input
                  type="checkbox"
                  checked={task.status === 'done'}
                  onChange={() => toggle(task)}
                />{' '}
                <strong>{task.title}</strong>
              </label>
              {task.source_gap && <p className="muted">{task.source_gap}</p>}
              <select
                value={task.status}
                onChange={(e) => changeTask(task, { status: e.target.value })}
              >
                {TASK_STATUSES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
