import json
from pipeline import download_episode, transcribe_episode

EPISODES_FILE = "episodes.json"


def load_episodes():
    with open(EPISODES_FILE) as f:
        return json.load(f)


def save_episodes(episodes):
    with open(EPISODES_FILE, "w") as f:
        json.dump(episodes, f, indent=2)


def run(limit=None):
    episodes = load_episodes()
    pending = [e for e in episodes if e["status"] == "pending"]
    if limit:
        pending = pending[:limit]

    for ep in pending:
        print(f"Processing: {ep['url']}")
        try:
            video_id = download_episode(ep["url"])
            ep["video_id"] = video_id
            transcribe_episode(video_id)
            ep["status"] = "done"
            print(f"  -> done ({video_id})")
        except Exception as e:
            ep["status"] = "failed"
            ep["error"] = str(e)
            print(f"  -> FAILED: {e}")

        save_episodes(episodes)  # persist progress after every episode


if __name__ == "__main__":
    run(limit=5)  # process just the first 5 for now