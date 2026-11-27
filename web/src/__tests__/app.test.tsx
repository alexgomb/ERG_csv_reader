import fs from 'node:fs'
import path from 'node:path'

import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../App'

const EXAMPLE_DIR = path.resolve(__dirname, '../../../example_files')

function mockExampleFetch() {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      const encodedName = url.split('/example_files/')[1]
      const fileName = decodeURIComponent(encodedName)
      const buf = fs.readFileSync(path.join(EXAMPLE_DIR, fileName))
      return {
        ok: true,
        status: 200,
        arrayBuffer: async () =>
          buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength),
      } as Response
    }),
  )
}

describe('nBio ERG-Trace Web UI Integration', () => {
  beforeEach(() => {
    localStorage.clear()
    mockExampleFetch()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('loads bundled examples, switches EN/ES and Light/Dark themes, and updates UMH · nBio SVG', async () => {
    const user = userEvent.setup()
    render(<App />)

    expect(screen.getByRole('heading', { level: 1, name: 'nBio ERG-Trace' })).toBeInTheDocument()

    // Click Examples button in ControlsPanel
    await user.click(document.getElementById('ctrl-load-examples-btn')!)

    await waitFor(() => {
      expect(screen.getByTestId('status-bar')).toHaveTextContent(
        'Loaded 4 trace(s) (4 RIGHT - OD skipped).',
      )
    })

    // First loaded file (alphabetically Dark-Adapted_10) shows exact A1-B1 amplitude 366.53
    expect(screen.getByTestId('metric-a1b1-uv')).toHaveTextContent('366.53')

    // Switch to Spanish & Dark Mode
    await user.click(document.getElementById('ctrl-lang-es-btn')!)
    await user.click(document.getElementById('ctrl-theme-dark-btn')!)

    expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    expect(screen.getByTestId('status-bar')).toHaveTextContent(
      'Cargadas 4 curva(s) (4 de RIGHT - OD omitidas).',
    )
    const bannerImg = screen.getByAltText(/Grupo nBio/i) as HTMLImageElement
    expect(bannerImg.src).toContain('umh_nbio_dark.svg')
  })

  it('supports manual sidebar protocol switching to toggle 30 Hz Flicker analysis bar', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(document.getElementById('ctrl-load-examples-btn')!)
    await waitFor(() => {
      expect(screen.getByTestId('metric-a1b1-uv')).toHaveTextContent('366.53')
    })

    // Initially DA 10 -> no Flicker analysis bar
    expect(screen.queryByTestId('flicker-analysis-bar')).not.toBeInTheDocument()

    // Manually switch protocol dropdown to Flicker 30 Hz
    const protoSelect = document.getElementById('meta-protocol') as HTMLSelectElement
    await user.selectOptions(protoSelect, 'light_adapted_3_flicker')
    expect(screen.getByTestId('flicker-analysis-bar')).toBeInTheDocument()
    expect(document.getElementById('plot-protocol-badge')).toHaveTextContent(
      'LIGHT-ADAPTED 3.0 FLICKER ERG',
    )

    // Switch back to Dark-Adapted 10 -> Flicker bar hides
    await user.selectOptions(protoSelect, 'dark_adapted_10')
    expect(screen.queryByTestId('flicker-analysis-bar')).not.toBeInTheDocument()
  })

  it('opens About modal with Grupo nBio · Instituto de Bioingeniería · Universidad Miguel Hernández and Settings modal', async () => {
    const user = userEvent.setup()
    render(<App />)

    // Open About modal
    await user.click(document.getElementById('ctrl-about-btn')!)
    expect(screen.getByRole('dialog')).toHaveTextContent(
      'Grupo nBio · Instituto de Bioingeniería · Universidad Miguel Hernández',
    )
    expect(screen.getByRole('dialog')).toHaveTextContent('Alejandro Gombau García')
    await user.click(document.getElementById('about-close-btn')!)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    // Open Settings modal, enable RIGHT - OD, apply, and reload examples -> 8 traces loaded
    await user.click(document.getElementById('ctrl-settings-btn')!)
    await user.click(document.getElementById('settings-include-od')!)
    await user.click(document.getElementById('settings-apply-btn')!)

    await user.click(document.getElementById('ctrl-load-examples-btn')!)
    await waitFor(() => {
      expect(screen.getByTestId('status-bar')).toHaveTextContent('Loaded 8 trace(s).')
    })
  })

  it('edits metadata, toggles reference overlays, and clears records cleanly', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(document.getElementById('ctrl-load-examples-btn')!)
    await waitFor(() => {
      expect(screen.getAllByRole('checkbox', { name: /Overlay /i }).length).toBe(4)
    })

    // Edit Mouse ID
    const mouseInput = document.getElementById('meta-mouse-id') as HTMLInputElement
    await user.type(mouseInput, 'C57 P21')
    expect(mouseInput.value).toBe('C57 P21')

    // Enable overlay on second trace then clear overlays
    const checkboxes = screen.getAllByRole('checkbox', { name: /Overlay /i })
    await user.click(checkboxes[1])
    expect(checkboxes[1]).toBeChecked()
    await user.click(document.getElementById('btn-clear-overlays')!)
    expect(checkboxes[1]).not.toBeChecked()

    // Clear all records -> returns cleanly to empty state
    await user.click(document.getElementById('btn-clear-all')!)
    expect(screen.getByTestId('metric-a1b1-uv')).toHaveTextContent('—')
  })

  it('recovers gracefully from corrupt localStorage and handles keyboard shortcuts (G, Ctrl+0, Ctrl+R)', async () => {
    localStorage.setItem('nbio_erg_trace_prefs_v1', '{broken-json!!')
    const user = userEvent.setup()
    render(<App />)

    await user.click(document.getElementById('ctrl-load-examples-btn')!)
    await waitFor(() => {
      expect(screen.getByTestId('metric-a1b1-uv')).toHaveTextContent('366.53')
    })

    const gridCheckbox = document.getElementById('ctrl-grid-checkbox') as HTMLInputElement
    expect(gridCheckbox).toBeChecked()
    await user.keyboard('g')
    expect(gridCheckbox).not.toBeChecked()
    await user.keyboard('g')
    expect(gridCheckbox).toBeChecked()

    // Ctrl+0 resets view and Ctrl+R resets markers without crashing
    await user.keyboard('{Control>}0{/Control}')
    await user.keyboard('{Control>}r{/Control}')
    expect(screen.getByTestId('metric-a1b1-uv')).toHaveTextContent('366.53')
  })
})

