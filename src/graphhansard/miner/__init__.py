"""Layer 1 — The Miner: Audio Ingestion Pipeline.

Discovers, downloads, catalogues, and archives House of Assembly session
recordings from YouTube using yt-dlp.
"""

from graphhansard.miner.catalogue import AudioCatalogue, DownloadStatus, SessionAudio
from graphhansard.miner.downloader import SessionDownloader

__all__ = ["AudioCatalogue", "DownloadStatus", "SessionAudio", "SessionDownloader"]
