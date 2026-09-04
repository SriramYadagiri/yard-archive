export default function SkeletonCard() {
  return (
    <div className="result-card skeleton">
      <div className="thumbnail skeleton-block" />

      <div className="result-body">
        <div className="skeleton-title" />

        <div className="skeleton-chapter" />

        <div className="skeleton-text">
          <div className="skeleton-line" />
          <div className="skeleton-line" />
          <div className="skeleton-line short" />
        </div>

        <div className="result-footer">
          <div className="result-meta">
            <div className="skeleton-speaker" />
            <div className="skeleton-speaker" />
            <div className="skeleton-time" />
          </div>

          <div className="skeleton-watch" />
        </div>
      </div>
    </div>
  )
}