import React from 'react'
import { createRoot } from 'react-dom/client'
import ExerciseConfirm from './ExerciseConfirm'

const container = document.getElementById('exercise-confirm-root')
if (container) {
  const suggestions = JSON.parse(container.dataset.suggestions || '[]')
  const confirmUrl = container.dataset.confirmUrl
  const skipUrl = container.dataset.skipUrl
  const programUrl = container.dataset.programUrl
  const csrf = container.dataset.csrf

  createRoot(container).render(
    <ExerciseConfirm
      suggestions={suggestions}
      confirmUrl={confirmUrl}
      skipUrl={skipUrl}
      programUrl={programUrl}
      csrf={csrf}
    />
  )
}
