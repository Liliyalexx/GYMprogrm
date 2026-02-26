import React, { useState } from 'react'

const BADGE_COLORS = {
  glutes: '#9d174d',
  legs: '#5b21b6',
  back: '#065f46',
  chest: '#991b1b',
  shoulders: '#0c4a6e',
  arms: '#92400e',
  core: '#166534',
  cardio: '#9a3412',
  full_body: '#334155',
}

function MediaBlock({ photoUrl, name }) {
  if (!photoUrl) {
    return (
      <div style={{ height: 200, background: '#f1f5f9', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '3rem' }}>
        💪
      </div>
    )
  }
  if (photoUrl.endsWith('.mp4')) {
    return (
      <div style={{ height: 200, background: '#f1f5f9', overflow: 'hidden' }}>
        <video
          src={photoUrl}
          autoPlay muted loop playsInline
          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          onError={e => { e.target.parentElement.innerHTML = '<div style="height:100%;display:flex;align-items:center;justify-content:center;font-size:3rem;">💪</div>' }}
        />
      </div>
    )
  }
  return (
    <div style={{ height: 200, background: '#f1f5f9', overflow: 'hidden' }}>
      <img
        src={photoUrl}
        alt={name}
        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
        onError={e => { e.target.parentElement.innerHTML = '<div style="height:100%;display:flex;align-items:center;justify-content:center;font-size:3rem;">💪</div>' }}
      />
    </div>
  )
}

function ExerciseCard({ ex, onConfirm, onSkip }) {
  const [sets, setSets] = useState(ex.sets)
  const [reps, setReps] = useState(ex.reps)
  const [weight, setWeight] = useState('')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)

  const muscleColor = BADGE_COLORS[ex.muscle_group?.toLowerCase().replace(' ', '_')] || '#334155'
  const displayName = ex.name_ru || ex.name

  return (
    <div style={{
      background: '#fff', borderRadius: 12, border: '1px solid #e2e8f0',
      boxShadow: '0 2px 8px rgba(0,0,0,.08)', overflow: 'hidden', marginBottom: '1.25rem',
    }}>
      <MediaBlock photoUrl={ex.photo_url} name={displayName} />

      <div style={{ padding: '1.25rem' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '.75rem', gap: '.5rem' }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0 }}>{displayName}</h3>
            {ex.name_ru && <div style={{ fontSize: '.78rem', color: '#94a3b8', marginTop: '.15rem' }}>{ex.name}</div>}
          </div>
          <span style={{
            background: muscleColor + '22', color: muscleColor, borderRadius: 999,
            padding: '.2rem .65rem', fontSize: '.75rem', fontWeight: 600,
            textTransform: 'uppercase', whiteSpace: 'nowrap',
          }}>
            {ex.muscle_group}
          </span>
        </div>

        {/* Day */}
        <div style={{ fontSize: '.82rem', color: '#64748b', marginBottom: '.5rem' }}>📅 {ex.day_name}</div>

        {/* AI reason in Russian */}
        {(ex.reason_ru || ex.reason) && (
          <div style={{
            background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8,
            padding: '.65rem .85rem', fontSize: '.83rem', color: '#1e40af', marginBottom: '1rem',
          }}>
            🎯 <strong>Почему это упражнение:</strong> {ex.reason_ru || ex.reason}
          </div>
        )}

        {/* Sets / Reps / Weight inputs */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '.75rem', marginBottom: '1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '.78rem', fontWeight: 600, color: '#64748b', marginBottom: '.3rem' }}>ПОДХОДЫ</label>
            <input
              type="number" min="1" max="20" value={sets}
              onChange={e => setSets(e.target.value)}
              style={{ width: '100%', padding: '.45rem .65rem', border: '1.5px solid #e2e8f0', borderRadius: 7, fontSize: '.95rem' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '.78rem', fontWeight: 600, color: '#64748b', marginBottom: '.3rem' }}>ПОВТОРЕНИЯ</label>
            <input
              type="text" value={reps}
              onChange={e => setReps(e.target.value)}
              placeholder="напр. 10-12"
              style={{ width: '100%', padding: '.45rem .65rem', border: '1.5px solid #e2e8f0', borderRadius: 7, fontSize: '.95rem' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: '.78rem', fontWeight: 600, color: '#64748b', marginBottom: '.3rem' }}>ВЕС (кг)</label>
            <input
              type="number" step="0.5" min="0" value={weight}
              onChange={e => setWeight(e.target.value)}
              placeholder="необязательно"
              style={{ width: '100%', padding: '.45rem .65rem', border: '1.5px solid #e2e8f0', borderRadius: 7, fontSize: '.95rem' }}
            />
          </div>
        </div>

        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', fontSize: '.78rem', fontWeight: 600, color: '#64748b', marginBottom: '.3rem' }}>ЗАМЕТКИ (необязательно)</label>
          <input
            type="text" value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="напр. использовать резинку, медленный темп..."
            style={{ width: '100%', padding: '.45rem .65rem', border: '1.5px solid #e2e8f0', borderRadius: 7, fontSize: '.9rem' }}
          />
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: '.75rem' }}>
          <button
            onClick={() => { setLoading(true); onConfirm(ex.id, sets, reps, weight, notes) }}
            disabled={loading}
            style={{
              flex: 1, padding: '.65rem', background: '#16a34a', color: '#fff',
              border: 'none', borderRadius: 8, fontWeight: 700, fontSize: '.95rem', cursor: 'pointer',
            }}
          >
            ✓ Добавить в программу
          </button>
          <button
            onClick={() => { setLoading(true); onSkip(ex.id) }}
            disabled={loading}
            style={{
              padding: '.65rem 1.1rem', background: 'transparent', color: '#64748b',
              border: '1.5px solid #e2e8f0', borderRadius: 8, fontWeight: 600, fontSize: '.9rem', cursor: 'pointer',
            }}
          >
            Пропустить
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ExerciseConfirm({ suggestions, confirmUrl, skipUrl, programUrl, csrf }) {
  const [remaining, setRemaining] = useState(suggestions)
  const [done, setDone] = useState([])
  const [error, setError] = useState(null)

  const post = async (url, body) => {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error('Request failed')
    return res.json()
  }

  const handleConfirm = async (id, sets, reps, weight, notes) => {
    try {
      await post(confirmUrl, { id, sets, reps, weight_kg: weight || null, notes })
      setDone(d => [...d, { id, action: 'confirmed' }])
      setRemaining(r => r.filter(e => e.id !== id))
    } catch {
      setError('Ошибка сохранения. Попробуйте ещё раз.')
    }
  }

  const handleSkip = async (id) => {
    try {
      await post(skipUrl, { id })
      setDone(d => [...d, { id, action: 'skipped' }])
      setRemaining(r => r.filter(e => e.id !== id))
    } catch {
      setError('Ошибка. Попробуйте ещё раз.')
    }
  }

  if (remaining.length === 0) {
    const confirmed = done.filter(d => d.action === 'confirmed').length
    return (
      <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎉</div>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '.75rem' }}>Программа готова!</h2>
        <p style={{ color: '#64748b', marginBottom: '1.5rem' }}>
          {confirmed} упражнени{confirmed === 1 ? 'е добавлено' : confirmed < 5 ? 'я добавлено' : 'й добавлено'} в программу.
        </p>
        <a href={programUrl} style={{
          display: 'inline-block', padding: '.75rem 1.75rem',
          background: '#2563eb', color: '#fff', borderRadius: 8,
          fontWeight: 700, textDecoration: 'none', fontSize: '1rem',
        }}>
          Открыть программу →
        </a>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 560, margin: '0 auto' }}>
      {error && (
        <div style={{ background: '#fee2e2', color: '#991b1b', border: '1px solid #fca5a5', borderRadius: 8, padding: '.75rem 1rem', marginBottom: '1rem', fontSize: '.9rem' }}>
          {error}
        </div>
      )}

      <div style={{ fontSize: '.9rem', color: '#64748b', marginBottom: '1.25rem' }}>
        Осталось проверить: {remaining.length} · Подтверждено: {done.filter(d => d.action === 'confirmed').length}
      </div>

      {remaining.map(ex => (
        <ExerciseCard
          key={ex.id}
          ex={ex}
          onConfirm={handleConfirm}
          onSkip={handleSkip}
        />
      ))}
    </div>
  )
}
