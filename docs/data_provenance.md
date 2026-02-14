# Data Provenance

**Document Status:** FINAL  
**Version:** 1.0  
**Last Updated:** February 2026  
**Implements:** NF-15 (Public Data Only)

## Overview

This document provides complete provenance tracking for all data sources used in GraphHansard v1.0. All source data is derived from publicly available parliamentary recordings. No Freedom of Information Act (FOIA) requests, leaked documents, or restricted data are used in this release.

## Data Sources

### Parliamentary Audio Recordings

All audio data processed by GraphHansard originates from the following publicly accessible sources:

#### 1. Official Parliamentary Broadcasts

**Source:** The Bahamas House of Assembly Official YouTube Channel  
**URL:** https://www.youtube.com/@BahamasHouseofAssembly (representative URL)  
**Access Level:** Public  
**License:** Public domain (parliamentary proceedings)  
**Coverage:** 15th Parliament (2021-present)

Parliamentary sessions are broadcast live and archived on the official YouTube channel. Each session is:
- Publicly accessible without authentication
- Available for streaming and download via standard tools (yt-dlp)
- Not subject to copyright restrictions (government proceedings are public domain in The Bahamas)

#### 2. Alternative Public Archives

In cases where official channels are unavailable, the following secondary public sources may be used:

**Source:** News media archives (e.g., Tribune242, Nassau Guardian)  
**Access Level:** Public  
**License:** Fair use for civic transparency purposes  
**Usage:** Limited to clips of parliamentary proceedings embedded in news coverage

**Note:** As of v1.0, all processed audio originates from the official parliamentary YouTube channel. Secondary sources are documented here for completeness and future reference.

## Data Ingestion Pipeline

### Audio Acquisition

Audio files are acquired using the following process:

1. **Discovery**: Session URLs are manually catalogued or discovered via YouTube API search
2. **Download**: Audio is downloaded using `yt-dlp` (open-source tool)
3. **Storage**: Files are stored locally with metadata (session ID, date, source URL)
4. **Verification**: Each file's source URL is recorded in the session metadata

### Traceability

Every processed audio file can be traced back to its original public source through:

1. **Session Metadata**: Each session record includes:
   - `session_id`: Unique identifier (e.g., `20260210_house_session`)
   - `date`: Session date (YYYY-MM-DD format)
   - `source_url`: Original YouTube URL
   - `downloaded_at`: Timestamp of acquisition
   - `source_type`: "youtube_official" or other public source identifier

2. **Golden Record**: The entity knowledge base (`golden_record/mps.json`) contains:
   - MP biographical data from public sources (official parliament website, news media)
   - No private or leaked information
   - All aliases derived from observed usage in public parliamentary proceedings

3. **Transcription Provenance**: Each transcription includes:
   - Source audio file identifier
   - Timestamp ranges mapping transcript segments to original audio
   - Model used (Whisper version, diarization model)
   - Processing date

## Data We Do NOT Use

GraphHansard v1.0 explicitly does NOT process, ingest, or store:

- ❌ Audio from private meetings, closed sessions, or off-the-record discussions
- ❌ Documents obtained via Freedom of Information Act (FOIA) requests
- ❌ Leaked materials, whistleblower submissions, or confidential communications
- ❌ Private social media content, emails, or text messages
- ❌ Non-public committee hearings or caucus meetings
- ❌ Audio recordings from sources requiring authentication or payment
- ❌ Data obtained through web scraping of non-public areas

## Ethical Boundaries

### Public Figures Doctrine

All Members of Parliament (MPs) featured in GraphHansard are:
- Elected public officials acting in their official capacity
- Subject to public scrutiny as a constitutional norm in democratic societies
- Speaking on the record in the House of Assembly (a public forum)

This project applies computational analysis to the same data a citizen could manually review by watching parliamentary proceedings. We automate transparency, but do not surveil private life.

### Children and Non-MP Speakers

If parliamentary audio includes minors (e.g., youth representatives) or non-MP speakers (e.g., witnesses in committee):
- Their speech is included only if part of official parliamentary proceedings
- No additional biographical data is collected beyond what is stated on record
- Privacy considerations are applied to non-elected participants

As of v1.0, the system focuses exclusively on MP-to-MP interactions. Non-MP speakers are not tracked in the network graph.

## Verification

To verify the public nature of any data used in GraphHansard:

1. **Check Session Metadata**: Each session includes `source_url` in its metadata JSON
2. **Validate URL Access**: Visit the source URL in a private/incognito browser window
3. **Confirm Public Availability**: Verify that no login, payment, or authentication is required

### Example Session Record

```json
{
  "session_id": "20260210_house_session",
  "date": "2026-02-10",
  "parliament": "15th Parliament of The Bahamas",
  "source_url": "https://www.youtube.com/watch?v=EXAMPLE123",
  "source_type": "youtube_official",
  "downloaded_at": "2026-02-11T08:30:00Z",
  "duration_seconds": 14400,
  "audio_quality": "good",
  "notes": "Regular session, full attendance"
}
```

Every claim made by GraphHansard can be independently verified by:
1. Visiting the source URL
2. Navigating to the cited timestamp
3. Listening to the original audio

## Compliance

This data provenance framework ensures compliance with:

- **SRD §12.5 (NF-15)**: All source audio is from publicly available parliamentary recordings
- **Bahamian Public Records Act**: No confidential government data is processed
- **International Civic Tech Best Practices**: Transparency in data sourcing
- **Academic Research Standards**: Reproducibility and verifiability

## Updates and Corrections

If you identify a data source that is incorrectly classified as public, or if you believe any data violates privacy norms, please:

1. Open an issue on the GitHub repository: https://github.com/caribdigital/graphhansard/issues
2. Include the specific session ID or data reference
3. Provide reasoning for the concern

We are committed to maintaining the highest ethical standards in civic transparency work.

---

**Document License:** CC-BY-4.0  
**Attribution:** GraphHansard / Carib Digital Labs  
**Contact:** https://github.com/caribdigital/graphhansard
