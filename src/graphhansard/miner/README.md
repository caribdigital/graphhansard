# GraphHansard Miner — YouTube Audio Ingestion Pipeline

The Miner is a robust, rate-limited, resumable audio ingestion pipeline that discovers, downloads, catalogues, and archives House of Assembly session recordings from YouTube using yt-dlp.

## Features

- **MN-1**: Discovers all House of Assembly videos from the Bahamas Parliament YouTube channel
- **MN-2**: Downloads audio-only streams in highest quality (opus/m4a, 128kbps+)
- **MN-3**: Handles YouTube authentication via exported browser cookies
- **MN-4**: Configurable rate limiting (default: 1 req per 5 seconds, max 50 downloads per session)
- **MN-5**: Resumable downloads using yt-dlp's `--download-archive` feature

## Installation

Install the miner dependencies:

```bash
pip install -e ".[miner]"
```

This will install:
- `yt-dlp` - YouTube downloader
- `pydantic` - Data validation
- Core dependencies

## Usage

### Command-Line Interface

The miner provides a CLI with three main commands:

#### 1. Scrape Command

Download sessions from YouTube:

```bash
# Incremental scrape (default) - only download new sessions
python -m graphhansard.miner.cli scrape

# Full scrape - download all available sessions
python -m graphhansard.miner.cli scrape --full

# With cookies for authentication
python -m graphhansard.miner.cli scrape --cookies /path/to/cookies.txt
```

#### 2. Status Command

View download statistics:

```bash
python -m graphhansard.miner.cli status
```

Output example:
```
============================================================
GraphHansard Miner — Download Statistics
============================================================

Total entries:        25
  Downloaded:         23
  Failed:             1
  Skipped/Duplicate:  1

Total audio duration: 45.50 hours

Catalogue location:   /path/to/archive/catalogue.json
============================================================
```

#### 3. Add Manual Command

Add a non-YouTube audio file to the catalogue:

```bash
python -m graphhansard.miner.cli add-manual /path/to/audio.opus \
  --date 2024-01-15 \
  --title "House of Assembly - Budget Debate"
```

### Python API

You can also use the miner programmatically:

```python
from graphhansard.miner.downloader import SessionDownloader

# Initialize downloader
downloader = SessionDownloader(
    archive_dir="archive",
    cookies_path="cookies.txt",  # Optional
    sleep_interval=5,            # Seconds between downloads
    max_downloads=50,            # Max downloads per session
)

# Discover sessions
channel_url = "https://www.youtube.com/@BahamasParliament/videos"
videos = downloader.discover_sessions(channel_url)
print(f"Found {len(videos)} videos")

# Run incremental scrape
downloader.run_incremental_scrape(channel_url)

# Or download a specific video
result = downloader.download_session("https://youtube.com/watch?v=VIDEO_ID")
```

### Working with the Catalogue

```python
from graphhansard.miner.catalogue import AudioCatalogue

# Load catalogue
catalogue = AudioCatalogue("archive/catalogue.json")

# Get all entries
entries = catalogue.get_all_entries()

# Check for duplicates
is_dup = catalogue.is_duplicate("VIDEO_ID")

# Add a manual entry
from graphhansard.miner.catalogue import SessionAudio, DownloadStatus
from datetime import datetime

entry = SessionAudio(
    video_id="custom123",
    title="Special Session",
    upload_date=datetime(2024, 1, 15).date(),
    duration_seconds=3600,
    audio_format="opus",
    audio_bitrate_kbps=128,
    file_path="archive/2024/20240115/custom123.opus",
    file_hash_sha256="abc123...",
    download_timestamp=datetime.now(),
    source_url="manual:custom123",
    status=DownloadStatus.DOWNLOADED,
)

catalogue.add_entry(entry)
```

## Cookie Authentication

For age-restricted or consent-gated videos, you'll need to export browser cookies:

### Option 1: Export from Browser (Recommended)

Use a browser extension like "Get cookies.txt LOCALLY" to export cookies in Netscape format.

1. Install the extension in Firefox/Chrome
2. Navigate to youtube.com while logged in
3. Click the extension and export cookies to `cookies.txt`
4. Store the file securely (it's excluded from git via `.gitignore`)

### Option 2: Use yt-dlp's Browser Cookie Import

```bash
# yt-dlp can read cookies directly from your browser
# This is used internally but not yet exposed in the CLI
```

## Rate Limiting

The miner enforces rate limiting to avoid IP bans:

- **Default**: 1 request per 5 seconds
- **Max downloads per session**: 50 (configurable)
- **Sleep interval**: Configurable via constructor

This ensures responsible scraping of YouTube content.

## Resumability

The miner uses yt-dlp's `--download-archive` feature to track completed downloads:

- Downloads are tracked in `archive/download_archive.txt`
- On interruption, the next run resumes from the last incomplete file
- The catalogue also maintains metadata for deduplication

## Directory Structure

Downloaded audio files are organized hierarchically:

```
archive/
├── catalogue.json           # Metadata catalogue
├── download_archive.txt     # yt-dlp resumability tracker
└── 2024/
    ├── 20240115/
    │   ├── VIDEO_ID1.opus
    │   └── VIDEO_ID1.info.json
    └── 20240116/
        └── VIDEO_ID2.opus
```

## Output Format

- **Preferred format**: Opus (best quality/size ratio)
- **Fallback**: M4A
- **Bitrate**: 128kbps minimum
- **Info JSON**: Metadata saved alongside audio

## Security Notes

⚠️ **IMPORTANT**: YouTube cookies files contain authentication credentials.

- Cookies are excluded from git via `.gitignore`
- Never commit `cookies.txt`, `*.cookies`, or the `cookies/` directory
- Store cookies securely and rotate them periodically
- See `.gitignore` for full list of excluded patterns

## Error Handling

The miner handles common errors gracefully:

- **Network failures**: Logged and recorded in catalogue with `status: failed`
- **Max downloads reached**: Stops gracefully after configured limit
- **Duplicate detection**: Skips already-downloaded videos
- **Invalid cookies**: Falls back to unauthenticated download when possible

## Testing

Run the test suite:

```bash
pytest tests/test_miner.py -v
```

Tests cover:
- SessionAudio schema validation
- AudioCatalogue operations
- SessionDownloader discovery and download
- CLI argument parsing

## References

- **SRD §7**: Layer 1 — The Miner specification
- **SRD §15**: Milestone M-1.2 (Download 10+ sessions)
- [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp)
