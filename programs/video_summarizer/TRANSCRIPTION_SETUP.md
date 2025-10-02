# File Transcription Setup Guide

## Overview

The file transcription feature allows you to transcribe local audio/video files using OpenAI's Whisper API, then optionally generate AI-powered summaries with timestamps.

## Features

- **Multiple format support**: MP3, MP4, WAV, M4A, FLAC, WebM, OGG, and more
- **Automatic language detection** or specify language
- **Timestamp-accurate transcripts** with word and segment-level timing
- **AI summary generation** using existing Claude integration
- **File size limit**: 25MB (OpenAI Whisper API limit)

## Setup Instructions

### 1. Install Dependencies

```bash
# Install OpenAI Python package
pip3 install openai
```

### 2. Set up OpenAI API Key

You need an OpenAI API key to use Whisper. Get one from [platform.openai.com](https://platform.openai.com/api-keys).

**Option A: Environment variable**
```bash
export OPENAI_API_KEY="your-api-key-here"
```

**Option B: Create .env file**
```bash
# In the video_summarizer directory
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

### 3. Make scripts executable

```bash
chmod +x scripts/transcribe_file.sh
```

## Usage

### Basic Transcription

```bash
# Transcribe with auto-language detection
./scripts/transcribe_file.sh /path/to/audio.mp3

# Transcribe with specific language
./scripts/transcribe_file.sh /path/to/video.mp4 en

# Other examples
./scripts/transcribe_file.sh recording.wav es
./scripts/transcribe_file.sh podcast.m4a fr
```

### Language Codes

Common language codes for the `language` parameter:
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `it` - Italian
- `pt` - Portuguese
- `ru` - Russian
- `ja` - Japanese
- `ko` - Korean
- `zh` - Chinese

### Output Files

The tool creates two types of output:

1. **Transcript JSON**: `transcriptions/{filename}_transcript_{timestamp}.json`
   - Complete transcript with timestamps
   - Word-level and segment-level timing data
   - Metadata about the source file

2. **AI Summary HTML** (optional): `output/article_summaries/{filename}_transcript_summary_{timestamp}.html`
   - AI-generated summary with key insights
   - Clickable timestamps linked to transcript
   - Same format as video summaries

## Workflow Integration

### Standalone Usage
```bash
# Just transcribe
./scripts/transcribe_file.sh meeting_recording.mp3

# Transcribe and create summary (prompted)
./scripts/transcribe_file.sh interview.wav
# When prompted: y (to create summary)
```

### Batch Processing
```bash
# Process multiple files
for file in *.mp3; do
    ./scripts/transcribe_file.sh "$file"
done
```

## Cost Estimation

OpenAI Whisper API pricing:
- **$0.006 per minute** of audio
- Examples:
  - 10-minute recording: ~$0.06
  - 1-hour podcast: ~$0.36
  - 3-hour meeting: ~$1.08

## File Size Limits

- **Maximum**: 25MB per file (OpenAI limit)
- **Workaround for large files**:
  - Split large files using tools like `ffmpeg`
  - Consider using local Whisper for unlimited file sizes

## Troubleshooting

### Common Issues

1. **"OpenAI API key not found"**
   - Set `OPENAI_API_KEY` environment variable or add to `.env` file

2. **"File size exceeds 25MB limit"**
   - Compress the file or split into smaller chunks
   - Use lower quality encoding for audio

3. **"File format not supported"**
   - Convert to supported format using `ffmpeg`:
   ```bash
   ffmpeg -i input.avi output.mp3
   ```

4. **"ModuleNotFoundError: No module named 'openai'"**
   - Install the package: `pip3 install openai`

### Supported Formats

Audio: MP3, WAV, FLAC, M4A, AAC, OGG, WMA, AMR, AIFF
Video: MP4, WebM, 3GP, MPEG

## Examples

### Meeting Recording
```bash
./scripts/transcribe_file.sh team_meeting_2024.m4a en
# Creates transcript + optional summary with key discussion points
```

### Podcast Episode
```bash
./scripts/transcribe_file.sh podcast_ep_42.mp3
# Auto-detects language, creates searchable transcript
```

### Interview
```bash
./scripts/transcribe_file.sh interview_candidate.wav en
# Creates transcript with speaker timing for easy review
```

The transcription tool is a standalone feature that reuses the same AI analysis logic and HTML output format as the video summarizer for consistency, but operates independently from the main workflow.