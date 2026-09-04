import { useState, useMemo, useEffect, useRef } from 'react'
import Waveform from './components/Waveform.jsx'
import ResultCard from './components/ResultCard.jsx'
import EmptyState from './components/EmptyState.jsx'
import SkeletonCard from './components/SkeletonCard.jsx'

const API_URL = 'http://localhost:8000/search'
const PAGE_SIZE = 50

const PLACEHOLDERS = [
  "Boston PD! Get that child out of your mouth!",
  "Slime ragebaiting a racist guy at the airport",
  "Atrioc being a whale",
  "Yingling regressing into a beast animal child",
  "The child pageant for adults only",
]

const TYPE_SPEED_MS = 55
const DELETE_SPEED_MS = 30
const PAUSE_BEFORE_DELETE_MS = 1400
const PAUSE_BEFORE_NEXT_MS = 400

const HISTORY_KEY = 'yard-search-history'
const MAX_HISTORY = 10

function todayISO() {
  return new Date().toISOString().slice(0, 10)
}

// --- localStorage history: lightweight metadata only (query/dates/sort/
// timestamp/result count), never the actual result payloads. This is what
// keeps it small and immune to going stale -- a saved search is just a
// shortcut to re-run, not a cached answer that could rot. ---
function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveToHistory(entry) {
  const existing = loadHistory()
  const key = `${entry.query}|${entry.dateFrom}|${entry.dateTo}`
  const deduped = existing.filter(
    (e) => `${e.query}|${e.dateFrom}|${e.dateTo}` !== key
  )
  const updated = [entry, ...deduped].slice(0, MAX_HISTORY)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
  return updated
}

// --- sessionStorage cache: full result payloads, scoped to this tab.
// Naturally expires when the tab closes, so unlike localStorage there's
// no long-term staleness risk -- it's just avoiding a duplicate paid
// embed+rerank call if you search the same thing twice in one session
// (e.g. clicking back/forward). ---
function cacheKey(query, dateFrom, dateTo) {
  return `yard-search-cache:${query}|${dateFrom}|${dateTo}`
}

function getCachedResults(query, dateFrom, dateTo) {
  try {
    const raw = sessionStorage.getItem(cacheKey(query, dateFrom, dateTo))
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function setCachedResults(query, dateFrom, dateTo, results) {
  try {
    sessionStorage.setItem(cacheKey(query, dateFrom, dateTo), JSON.stringify(results))
  } catch {
    // sessionStorage full or unavailable -- caching is a nice-to-have,
    // fail silently rather than breaking the search itself
  }
}

// --- URL param helpers ---
function readParamsFromURL() {
  const params = new URLSearchParams(window.location.search)
  return {
    query: params.get('q') || '',
    dateFrom: params.get('from') || '2021-07-01',
    dateTo: params.get('to') || todayISO(),
    sortBy: params.get('sort') || 'score',
  }
}

function writeParamsToURL({ query, dateFrom, dateTo, sortBy }, { push }) {
  const params = new URLSearchParams()
  if (query) params.set('q', query)
  if (dateFrom) params.set('from', dateFrom)
  if (dateTo) params.set('to', dateTo)
  if (sortBy && sortBy !== 'score') params.set('sort', sortBy)

  const url = `${window.location.pathname}?${params.toString()}`
  if (push) {
    window.history.pushState(null, '', url)
  } else {
    window.history.replaceState(null, '', url)
  }
}

export default function App() {
  const initial = readParamsFromURL()

  const [query, setQuery] = useState(initial.query)
  const [dateFrom, setDateFrom] = useState(initial.dateFrom)
  const [dateTo, setDateTo] = useState(initial.dateTo)
  const [sortBy, setSortBy] = useState(initial.sortBy)
  const [results, setResults] = useState(null)
  const [searchedQuery, setSearchedQuery] = useState(initial.query)
  const [page, setPage] = useState(0)
  const [loading, setLoading] = useState(false)
  const [showSkeletons, setShowSkeletons] = useState(false)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState(() => loadHistory())

  const [focused, setFocused] = useState(false)
  const [displayedPlaceholder, setDisplayedPlaceholder] = useState('')
  const phraseIndexRef = useRef(0)
  const inputRef = useRef(null)

  useEffect(() => {
    if (focused || query) {
      setDisplayedPlaceholder('')
      return
    }

    let charIndex = 0
    let deleting = false
    let timeoutId

    const tick = () => {
      const phrase = PLACEHOLDERS[phraseIndexRef.current]

      if (!deleting) {
        charIndex += 1
        setDisplayedPlaceholder(phrase.slice(0, charIndex))
        if (charIndex >= phrase.length) {
          deleting = true
          timeoutId = setTimeout(tick, PAUSE_BEFORE_DELETE_MS)
          return
        }
        timeoutId = setTimeout(tick, TYPE_SPEED_MS)
      } else {
        charIndex -= 1
        setDisplayedPlaceholder(phrase.slice(0, charIndex))
        if (charIndex <= 0) {
          deleting = false
          phraseIndexRef.current = (phraseIndexRef.current + 1) % PLACEHOLDERS.length
          timeoutId = setTimeout(tick, PAUSE_BEFORE_NEXT_MS)
          return
        }
        timeoutId = setTimeout(tick, DELETE_SPEED_MS)
      }
    }

    timeoutId = setTimeout(tick, TYPE_SPEED_MS)
    return () => clearTimeout(timeoutId)
  }, [focused, query])

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key !== '/') return
      const active = document.activeElement
      const isTyping = active && (
        active.tagName === 'INPUT' ||
        active.tagName === 'TEXTAREA' ||
        active.isContentEditable
      )
      if (isTyping) return
      e.preventDefault()
      inputRef.current?.focus()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Core search logic, decoupled from the form submit event so it can
  // also run on initial mount (restoring a shared/bookmarked URL) and
  // when clicking a history entry.
  async function runSearch(q, from, to, { pushHistoryEntry = true, updateURL = true } = {}) {
    const trimmed = q.trim()
    if (!trimmed) return

    setError(null)
    setPage(0)

    const cached = getCachedResults(trimmed, from, to)
    if (cached) {
      setResults(cached)
      setSearchedQuery(trimmed)
      if (updateURL) writeParamsToURL({ query: trimmed, dateFrom: from, dateTo: to, sortBy }, { push: true })
      return
    }

    setLoading(true)
    setShowSkeletons(true)

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: trimmed, date_from: from || null, date_to: to || null }),
      })

      if (!response.ok) throw new Error(`Server returned ${response.status}`)

      const data = await response.json()

      setTimeout(() => {
        setResults(data.results)
        setSearchedQuery(trimmed)
        setLoading(false)
        setShowSkeletons(false)
      }, 150)

      setCachedResults(trimmed, from, to, data.results)

      if (updateURL) {
        writeParamsToURL({ query: trimmed, dateFrom: from, dateTo: to, sortBy }, { push: true })
      }

      if (pushHistoryEntry) {
        const entry = {
          query: trimmed,
          dateFrom: from,
          dateTo: to,
          sortBy,
          resultCount: data.results.length,
          timestamp: Date.now(),
        }
        setHistory(saveToHistory(entry))
      }
    } catch (err) {
      setError(err.message)
      setResults(null)
      setLoading(false)
      setShowSkeletons(false)
    }
  }

  // Restore a search from the URL on first load (shared/bookmarked link).
  useEffect(() => {
    if (initial.query) {
      runSearch(initial.query, initial.dateFrom, initial.dateTo, { pushHistoryEntry: false, updateURL: false })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Support the browser's back/forward buttons.
  useEffect(() => {
    function handlePopState() {
      const params = readParamsFromURL()
      setQuery(params.query)
      setDateFrom(params.dateFrom)
      setDateTo(params.dateTo)
      setSortBy(params.sortBy)
      if (params.query) {
        runSearch(params.query, params.dateFrom, params.dateTo, { pushHistoryEntry: false, updateURL: false })
      } else {
        setResults(null)
      }
    }
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleSubmit(e) {
    e.preventDefault()
    runSearch(query, dateFrom, dateTo)
  }

  function handleHistoryClick(entry) {
    setQuery(entry.query)
    setDateFrom(entry.dateFrom)
    setDateTo(entry.dateTo)
    setSortBy(entry.sortBy)
    runSearch(entry.query, entry.dateFrom, entry.dateTo)
  }

  function clearHistory() {
    localStorage.removeItem(HISTORY_KEY)
    setHistory([])
  }

  // Sort stays client-side (no refetch), but still reflected in the URL
  // via replaceState -- doesn't create a new back-button entry since it's
  // not a new search, just a different view of the same results.
  function handleSortChange(newSort) {
    setSortBy(newSort)
    setPage(0)
    writeParamsToURL({ query, dateFrom, dateTo, sortBy: newSort }, { push: false })
  }

  const sortedResults = useMemo(() => {
    if (!results) return null
    const copy = [...results]
    if (sortBy === 'latest') {
      copy.sort((a, b) => (b.published_ts || 0) - (a.published_ts || 0))
    } else if (sortBy === 'oldest') {
      copy.sort((a, b) => (a.published_ts || 0) - (b.published_ts || 0))
    }
    return copy
  }, [results, sortBy])

  const totalPages = sortedResults ? Math.ceil(sortedResults.length / PAGE_SIZE) : 0
  const pageResults = sortedResults
    ? sortedResults.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
    : []

  return (
    <main>
      <header className="hero">
        <p className="eyebrow">The Yard Archive</p>
        <h1>
          Find your favorite bits
          <br />
          from your favorite episodes...
        </h1>
      </header>

      <div className="filters-row">
        <label className="filter-field">
          <span>From</span>
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        </label>
        <label className="filter-field">
          <span>To</span>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </label>
      </div>

      <form className="search-bar" onSubmit={handleSubmit}>
        <Waveform active={loading} />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={displayedPlaceholder}
          autoComplete="off"
        />
        <button type="submit" disabled={loading}>
          Search
        </button>
      </form>

      {history.length > 0 && (
        <div className="history-row">
          <span className="history-label">Recent:</span>
          {history.map((entry) => (
            <button
              key={`${entry.query}-${entry.timestamp}`}
              className="history-chip"
              onClick={() => handleHistoryClick(entry)}
              title={`${entry.dateFrom} to ${entry.dateTo}`}
            >
              {entry.query}
            </button>
          ))}
          <button className="history-clear" onClick={clearHistory}>Clear</button>
        </div>
      )}

      <section className="status" aria-live="polite">
        <span>
          {error && `Something went wrong: ${error}`}
          {!error && loading && 'Searching...'}
          {!error && !loading && results && (
            results.length === 0
              ? ''
              : `${results.length} strong match${results.length === 1 ? '' : 'es'}`
          )}
        </span>

        {!loading && results && results.length > 0 && (
          <label className="sort-select">
            Sort by
            <select value={sortBy} onChange={(e) => handleSortChange(e.target.value)}>
              <option value="score">Relevance</option>
              <option value="latest">Latest</option>
              <option value="oldest">Oldest</option>
            </select>
          </label>
        )}
      </section>

      <section className="results">
        {!loading && results && (
          results.length === 0 ? (
            <EmptyState message="No strong matches. Try rephrasing the question or widening the date range." />
          ) : (
            pageResults.map((hit) => (
              <ResultCard key={hit.chunk_id} hit={hit} query={searchedQuery} />
            ))
          )
        )}

        {showSkeletons && (
          Array.from({ length: PAGE_SIZE }).map((_, i) => (
            <SkeletonCard key={i} />
          ))
        )}
      </section>

      {totalPages > 1 && (
        <nav className="pagination">
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            ← Previous
          </button>
          <span>Page {page + 1} of {totalPages}</span>
          <button
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
          >
            Next →
          </button>
        </nav>
      )}
    </main>
  )
}