#!/usr/bin/env python3
"""
File Transcription Script
Transcribes audio/video files using OpenAI Whisper API
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import openai
from openai import OpenAI

class FileTranscriber:
    def __init__(self, base_dir=None):
        if base_dir is None:
            # Find the project root
            current_dir = Path(__file__).parent.parent
            while current_dir != current_dir.parent:
                if (current_dir / '.git').exists() or (current_dir / 'CLAUDE.md').exists():
                    base_dir = current_dir
                    break
                current_dir = current_dir.parent
            else:
                base_dir = Path(__file__).parent.parent

        self.base_dir = Path(base_dir)
        self.output_dir = self.base_dir / "programs" / "video_summarizer" / "transcriptions"
        self.logs_dir = self.base_dir / "programs" / "video_summarizer" / "logs"

        # Ensure directories exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self._setup_logging()

        # Initialize OpenAI client
        self._setup_openai()

    def _setup_logging(self):
        """Setup logging to both console and file"""
        timestamp = datetime.now().strftime('%Y%m%d')
        log_file = self.logs_dir / f"file_transcription_{timestamp}.log"

        self.logger = logging.getLogger('FileTranscriber')
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - [TRANSCRIPTION] - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # Log startup
        self.logger.info("=" * 80)
        self.logger.info(f"FILE TRANSCRIPTION SESSION STARTED")
        self.logger.info(f"Session Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Log File: {log_file}")
        self.logger.info("=" * 80)

    def _setup_openai(self):
        """Setup OpenAI client with API key"""
        try:
            # Try to get API key from environment
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                # Try to load from .env file
                env_file = self.base_dir / '.env'
                if env_file.exists():
                    with open(env_file, 'r') as f:
                        for line in f:
                            if line.startswith('OPENAI_API_KEY='):
                                api_key = line.split('=', 1)[1].strip().strip('"\'')
                                break

            if not api_key:
                raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable or add it to .env file")

            self.client = OpenAI(api_key=api_key)
            self.logger.info("✅ OpenAI client initialized successfully")

        except Exception as e:
            self.logger.error(f"❌ Error setting up OpenAI client: {e}")
            raise

    def _validate_file(self, file_path):
        """Validate input file exists and is supported format"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check file size (OpenAI Whisper limit is 25MB)
        file_size = file_path.stat().st_size
        max_size = 25 * 1024 * 1024  # 25MB in bytes

        if file_size > max_size:
            raise ValueError(f"File size ({file_size / 1024 / 1024:.1f}MB) exceeds OpenAI Whisper limit of 25MB")

        # Check supported formats
        supported_formats = {
            '.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm',
            '.flac', '.aac', '.ogg', '.wma', '.3gp', '.amr', '.aiff'
        }

        if file_path.suffix.lower() not in supported_formats:
            self.logger.warning(f"⚠️ File format '{file_path.suffix}' may not be supported. Supported formats: {', '.join(supported_formats)}")

        self.logger.info(f"📁 File: {file_path}")
        self.logger.info(f"📏 Size: {file_size / 1024 / 1024:.1f}MB")
        self.logger.info(f"🎵 Format: {file_path.suffix}")

        return file_path

    def transcribe_file(self, file_path, language=None):
        """Transcribe audio/video file using OpenAI Whisper"""
        try:
            file_path = self._validate_file(file_path)

            self.logger.info(f"🚀 Starting transcription...")
            self.logger.info(f"🎯 Language: {language or 'auto-detect'}")

            # Prepare transcription parameters
            transcribe_params = {
                "model": "whisper-1",
                "response_format": "verbose_json",  # Includes timestamps and word-level data
                "timestamp_granularities": ["word", "segment"]
            }

            if language:
                transcribe_params["language"] = language

            # Open and transcribe file
            with open(file_path, "rb") as audio_file:
                self.logger.info("📡 Sending file to OpenAI Whisper API...")

                transcript = self.client.audio.transcriptions.create(
                    file=audio_file,
                    **transcribe_params
                )

            self.logger.info("✅ Transcription completed successfully")

            # Process the transcript data
            transcript_data = {
                "source_file": str(file_path),
                "file_size_mb": file_path.stat().st_size / 1024 / 1024,
                "transcribed_at": datetime.now().isoformat(),
                "language": transcript.language,
                "duration": getattr(transcript, 'duration', None),
                "text": transcript.text,
                "segments": getattr(transcript, 'segments', []),
                "words": getattr(transcript, 'words', [])
            }

            # Save transcript to file
            output_file = self._save_transcript(transcript_data, file_path)

            # Log summary
            self.logger.info("=" * 60)
            self.logger.info("📊 TRANSCRIPTION SUMMARY")
            self.logger.info("=" * 60)
            self.logger.info(f"📁 Source: {file_path.name}")
            self.logger.info(f"🗣️ Language: {transcript.language}")
            self.logger.info(f"📝 Text length: {len(transcript.text):,} characters")
            self.logger.info(f"🎬 Segments: {len(getattr(transcript, 'segments', []))}")
            self.logger.info(f"💾 Saved to: {output_file}")
            self.logger.info("=" * 60)

            return output_file

        except Exception as e:
            self.logger.error(f"❌ Transcription failed: {e}")
            raise

    def _save_transcript(self, transcript_data, source_file):
        """Save transcript data to JSON file"""
        try:
            # Generate output filename
            source_name = Path(source_file).stem
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = self.output_dir / f"{source_name}_transcript_{timestamp}.json"

            # Save transcript
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(transcript_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"💾 Transcript saved: {output_file}")
            return output_file

        except Exception as e:
            self.logger.error(f"❌ Error saving transcript: {e}")
            raise

    def create_summary_from_transcript(self, transcript_file):
        """Create summary using existing video summarizer logic"""
        try:
            # Import the existing summarizer
            sys.path.append(str(self.base_dir / "programs" / "video_summarizer" / "scripts"))
            from video_article_summarizer import VideoArticleSummarizer

            # Load transcript
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript_data = json.load(f)

            self.logger.info(f"🎯 Creating summary from transcript...")

            # Initialize summarizer
            summarizer = VideoArticleSummarizer()

            # Format transcript for analysis (similar to YouTube transcript format)
            formatted_transcript = ""
            if transcript_data.get('segments'):
                for segment in transcript_data['segments']:
                    start_time = segment.get('start', 0)
                    text = segment.get('text', '').strip()
                    if text:
                        formatted_transcript += f"[{start_time:.1f}s] {text}\n"
            else:
                # Fallback to plain text
                formatted_transcript = transcript_data.get('text', '')

            # Create article data structure
            article_data = {
                'title': f"Transcript: {Path(transcript_data['source_file']).stem}",
                'url': f"file://{transcript_data['source_file']}",
                'video_id': None,
                'platform': 'local_file',
                'transcript': formatted_transcript,
                'has_transcript': True
            }

            # Generate summary
            summary_html = summarizer._generate_summary_with_claude(article_data)

            if summary_html:
                # Save summary
                summary_file = self._save_summary(summary_html, transcript_data, transcript_file)
                self.logger.info(f"✅ Summary created: {summary_file}")
                return summary_file
            else:
                self.logger.error("❌ Failed to generate summary")
                return None

        except Exception as e:
            self.logger.error(f"❌ Error creating summary: {e}")
            return None

    def _save_summary(self, summary_html, transcript_data, transcript_file):
        """Save HTML summary"""
        try:
            source_name = Path(transcript_data['source_file']).stem
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # Save to output directory
            summary_file = self.base_dir / "programs" / "video_summarizer" / "output" / "article_summaries" / f"{source_name}_transcript_summary_{timestamp}.html"
            summary_file.parent.mkdir(parents=True, exist_ok=True)

            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary_html)

            return summary_file

        except Exception as e:
            self.logger.error(f"❌ Error saving summary: {e}")
            raise

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python transcribe_file.py <audio_or_video_file> [language]")
        print("Example: python transcribe_file.py /path/to/audio.mp3")
        print("Example: python transcribe_file.py /path/to/video.mp4 en")
        sys.exit(1)

    file_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        transcriber = FileTranscriber()

        # Transcribe file
        transcript_file = transcriber.transcribe_file(file_path, language)

        # Ask if user wants to create summary
        print("\n" + "="*60)
        create_summary = input("🤔 Create AI summary from transcript? (y/n): ").lower().strip()

        if create_summary in ('y', 'yes'):
            summary_file = transcriber.create_summary_from_transcript(transcript_file)
            if summary_file:
                print(f"🎉 Summary created: {summary_file}")

        print(f"\n✅ Transcription complete!")
        print(f"📁 Transcript: {transcript_file}")

    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()