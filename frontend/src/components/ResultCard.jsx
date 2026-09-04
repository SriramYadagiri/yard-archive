import { useState, useRef, useEffect } from 'react'

const QUOTE_LIMIT = 180
const HOVER_DELAY_MS = 250

function formatTime(seconds) {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

function escapeRegExp(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// Pull meaningful search terms out of the query -- skip very short/common
// words (a, is, to...) so highlighting doesn't light up half the sentence.
function getQueryTokens(query) {
  if (!query) return []
  return [...new Set(
    query
      .toLowerCase()
      .split(/[^a-z0-9']+/)
      .filter((w) => w.length > 2)
  )]
}

// Find where the EARLIEST matching query term appears in the text, so we
// know whether the default (start-of-text) truncation would cut it off.
function findFirstMatchIndex(text, tokens) {
  if (tokens.length === 0) return -1
  const lower = text.toLowerCase()
  let earliest = -1
  for (const token of tokens) {
    const match = lower.match(new RegExp(`\\b${escapeRegExp(token)}\\b`))
    if (match && (earliest === -1 || match.index < earliest)) {
      earliest = match.index
    }
  }
  return earliest
}

// Builds the truncated preview. If a matched term would otherwise be cut
// off past QUOTE_LIMIT, center a window on it instead of always starting
// from character 0, with ellipses on whichever side got trimmed.
function buildSnippet(text, tokens, limit) {
  if (text.length <= limit) {
    return { snippet: text, leadingEllipsis: false, trailingEllipsis: false }
  }

  const matchIndex = findFirstMatchIndex(text, tokens)

  // No match, or it already falls within the default window -- normal
  // start-based truncation, same as before.
  if (matchIndex === -1 || matchIndex < limit) {
    return {
      snippet: text.slice(0, limit).trim(),
      leadingEllipsis: false,
      trailingEllipsis: true,
    }
  }

  let start = Math.max(0, matchIndex - Math.floor(limit / 2))
  let end = start + limit
  if (end > text.length) {
    end = text.length
    start = Math.max(0, end - limit)
  }

  // Nudge both edges out to the nearest word boundary so we don't slice
  // a word in half -- but never past the match itself.
  if (start > 0) {
    const nextSpace = text.indexOf(' ', start)
    if (nextSpace !== -1 && nextSpace < matchIndex) start = nextSpace + 1
  }
  if (end < text.length) {
    const prevSpace = text.lastIndexOf(' ', end)
    if (prevSpace !== -1 && prevSpace > matchIndex) end = prevSpace
  }

  return {
    snippet: text.slice(start, end).trim(),
    leadingEllipsis: start > 0,
    trailingEllipsis: end < text.length,
  }
}

// Renders text with matched query terms wrapped in <mark>. Splitting on a
// capturing group keeps the matched substrings in the resulting array, so
// we can tell matches from plain text without a stateful global regex.
function highlightText(text, tokens) {
  if (tokens.length === 0) return text
  const tokenSet = new Set(tokens.map((t) => t.toLowerCase()))
  const pattern = new RegExp(`(\\b(?:${tokens.map(escapeRegExp).join('|')})\\b)`, 'gi')
  const parts = text.split(pattern)

  return parts.map((part, i) =>
    tokenSet.has(part.toLowerCase())
      ? <mark className="highlight" key={i}>{part}</mark>
      : part
  )
}

export default function ResultCard({ hit, query }) {
  const [expanded, setExpanded] = useState(false)
  const [isPreviewing, setIsPreviewing] = useState(false)
  const [previewLoaded, setPreviewLoaded] = useState(false)
  const [muted, setMuted] = useState(true)
  const hoverTimer = useRef(null)
  const iframeRef = useRef(null)

  const startSeconds = Math.floor(hit.start)
  const videoLink = `https://www.youtube.com/watch?v=${hit.video_id}&t=${startSeconds}s`
  const thumbnailUrl = `https://img.youtube.com/vi/${hit.video_id}/hqdefault.jpg`
  const embedUrl = `https://www.youtube.com/embed/${hit.video_id}?start=${startSeconds}&autoplay=1&mute=1&modestbranding=1&rel=0&controls=0&enablejsapi=1`

  const tokens = getQueryTokens(query)
  const isLong = hit.text.length > QUOTE_LIMIT

  let rawDisplayText
  if (expanded || !isLong) {
    rawDisplayText = hit.text
  } else {
    const { snippet, leadingEllipsis, trailingEllipsis } = buildSnippet(hit.text, tokens, QUOTE_LIMIT)
    rawDisplayText = `${leadingEllipsis ? '… ' : ''}${snippet}${trailingEllipsis ? ' …' : ''}`
  }

  const displaySpeakers = [...new Set(hit.speakers)]

  function handleMouseEnter() {
    hoverTimer.current = setTimeout(() => {
      setPreviewLoaded(false)
      setIsPreviewing(true)
      setMuted(true)
    }, HOVER_DELAY_MS)
  }

  function handleMouseLeave() {
    clearTimeout(hoverTimer.current)
    setIsPreviewing(false)
    setPreviewLoaded(false)
  }

  function toggleMute() {
    const command = muted ? 'unMute' : 'mute'

    iframeRef.current?.contentWindow?.postMessage(
      JSON.stringify({
        event: 'command',
        func: command,
        args: [],
      }),
      '*'
    )

    setMuted(!muted)
  }

  useEffect(() => {
    if (!isPreviewing) return

    const timer = setTimeout(() => {
      toggleMute()
    }, 1200)

    return () => clearTimeout(timer)
  }, [isPreviewing])

  return (
    <div
      className={`result-card${isPreviewing ? ' previewing' : ''}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <a
        className="thumbnail-link"
        href={videoLink}
        target="_blank"
        rel="noopener noreferrer"
        onClick={(e) => isPreviewing && e.preventDefault()}
      >
        <div className="thumbnail">
          <img
            src={thumbnailUrl}
            alt=""
            loading="lazy"
            className={`thumbnail-image ${previewLoaded ? "fade-out" : ""}`}
          />

          {isPreviewing && (
            <>
              {!previewLoaded && (
                <div className="preview-loading">
                  <div className="spinner" />
                  <span>Loading preview...</span>
                </div>
              )}

              <iframe
                ref={iframeRef}
                src={embedUrl}
                title={`Preview at ${formatTime(hit.start)}`}
                allow="autoplay; encrypted-media"
                frameBorder="0"
                onLoad={() => setPreviewLoaded(true)}
                className={`preview-frame ${
                  previewLoaded ? "visible" : "hidden"
                }`}
              />

              <span className="playing-badge">Playing preview</span>

              <button
                className="mute-toggle"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  toggleMute()
                }}
              >
                {muted ? (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M16.5 12A4.5 4.5 0 0 0 14 8v8a4.5 4.5 0 0 0 2.5-4zM3 9v6h4l5 5V4L7 9H3z" />
                    <line x1="19" y1="6" x2="6" y2="19" stroke="currentColor" strokeWidth="2" />
                  </svg>
                ) : (
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0 0 14 8v8a4.5 4.5 0 0 0 2.5-4z" />
                  </svg>
                )}
              </button>
            </>
          )}
        </div>
      </a>

      <div className="result-body">
        <p className="video-title">{hit.title}</p>
        {hit.chapter && <p className="chapter-tag">{hit.chapter}</p>}
        <p className="result-text">{highlightText(rawDisplayText, tokens)}</p>
        {isLong && (
          <button className="expand-toggle" onClick={() => setExpanded(!expanded)}>
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}

        <div className="result-footer">
          <div className="result-meta">
            {displaySpeakers.map((name, i) => (
              <span className="speaker-tag" key={`${name}-${i}`}>{name}</span>
            ))}
            <span className="timestamp">{formatTime(hit.start)}</span>
            {hit.published_date && (
              <span className="published-date">{hit.published_date}</span>
            )}
          </div>

          <a className="jump-button" href={videoLink} target="_blank" rel="noopener noreferrer">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
            Watch
          </a>
        </div>
      </div>
    </div>
  )
}