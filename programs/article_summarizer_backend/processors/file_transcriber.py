#!/usr/bin/env python3
"""
File Transcriber - Refactored version using BaseProcessor
Transcribes audio/video files using DeepGram API
"""

import json
from datetime import datetime
from pathlib import Path
from deepgram import DeepgramClient

# Import our base class and config
import sys
sys.path.append(str(Path(__file__).parent.parent))
from core.base import BaseProcessor
from core.config import Config


class FileTranscriber(BaseProcessor):
    def __init__(self):
        super().__init__("file_transcriber")

        # Setup specific directories for this processor - use logs dir for temp files
        self.transcriptions_dir = self.base_dir / "programs" / "article_summarizer" / "logs" / "transcriptions"
        self.transcriptions_dir.mkdir(parents=True, exist_ok=True)

        # Initialize DeepGram client
        self._setup_deepgram()

    def _setup_deepgram(self):
        """Setup DeepGram client with API key"""
        try:
            # Get API key from config
            api_keys = Config.get_api_keys()
            api_key = api_keys.get('deepgram')

            if not api_key:
                raise ValueError("DeepGram API key not found. Please set DEEPGRAM_API_KEY environment variable or add it to .env file")

            # Initialize DeepGram client
            self.client = DeepgramClient(api_key=api_key)
            self.logger.info("✅ DeepGram client initialized successfully")

        except Exception as e:
            self.logger.error(f"❌ Error setting up DeepGram client: {e}")
            raise

    def _validate_file(self, file_path):
        """Validate input file exists and is supported format"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check file size (DeepGram can handle larger files than Whisper)
        file_size = file_path.stat().st_size
        max_size = Config.MAX_WHISPER_FILE_SIZE_MB * 1024 * 1024

        if file_size > max_size:
            self.logger.warning(f"⚠️ File size ({file_size / 1024 / 1024:.1f}MB) is large. DeepGram can handle it but processing may take time.")

        # Check supported formats
        supported_formats = Config.get_supported_audio_formats()

        if file_path.suffix.lower() not in supported_formats:
            self.logger.warning(f"⚠️ File format '{file_path.suffix}' may not be supported. Supported formats: {', '.join(supported_formats)}")

        self.logger.info(f"📁 File: {file_path}")
        self.logger.info(f"📏 Size: {file_size / 1024 / 1024:.1f}MB")
        self.logger.info(f"🎵 Format: {file_path.suffix}")

        return file_path

    def transcribe_file(self, file_path, language=None):
        """Transcribe audio/video file using DeepGram"""
        try:
            file_path = self._validate_file(file_path)

            self.logger.info(f"🚀 Starting transcription...")
            self.logger.info(f"🎯 Language: {language or 'auto-detect'}")

            # Read file
            with open(file_path, "rb") as audio_file:
                buffer_data = audio_file.read()

            self.logger.info("📡 Sending file to DeepGram API...")

            # Prepare transcription options
            options = {
                "model": "nova-2",
                "smart_format": True,
                "utterances": True,
                "punctuate": True,
                "paragraphs": True,
                "diarize": False
            }

            if language:
                options["language"] = language

            # Transcribe using DeepGram
            response = self.client.listen.v1.media.transcribe_file(
                request=buffer_data,
                **options
            )

            self.logger.info("✅ Transcription completed successfully")

            # Extract transcript data from DeepGram response
            result = response.results.channels[0].alternatives[0]

            # Get full transcript text
            transcript_text = result.transcript

            # Extract words with timestamps
            words_data = []
            if hasattr(result, 'words') and result.words:
                for word in result.words:
                    word_dict = {
                        'word': word.word,
                        'start': word.start,
                        'end': word.end,
                        'confidence': word.confidence
                    }
                    words_data.append(word_dict)

            # Extract paragraphs (similar to segments)
            segments_data = []
            if hasattr(result, 'paragraphs') and result.paragraphs:
                for idx, paragraph in enumerate(result.paragraphs.paragraphs):
                    seg_dict = {
                        'id': idx,
                        'start': paragraph.start,
                        'end': paragraph.end,
                        'text': ' '.join([sentence.text for sentence in paragraph.sentences]),
                        'num_words': paragraph.num_words
                    }
                    segments_data.append(seg_dict)

            # Get detected language and duration
            metadata = response.results.channels[0]
            detected_language = getattr(metadata, 'detected_language', language or 'en')

            # Calculate duration from last word
            duration = words_data[-1]['end'] if words_data else 0

            transcript_data = {
                "source_file": str(file_path),
                "file_size_mb": file_path.stat().st_size / 1024 / 1024,
                "transcribed_at": datetime.now().isoformat(),
                "language": detected_language,
                "duration": duration,
                "text": transcript_text,
                "segments": segments_data,
                "words": words_data,
                "provider": "deepgram"
            }

            # Save transcript to file (temporarily for logging)
            output_file = self._save_transcript(transcript_data, file_path)

            # Log summary using base class method
            self.log_session_summary(
                source_file=file_path.name,
                language=detected_language,
                text_length=f"{len(transcript_text):,} characters",
                segments_count=len(segments_data),
                output_file=str(output_file)
            )

            # Return both the data and file path so caller can delete after use
            return {
                'transcript_data': transcript_data,
                'output_file': output_file
            }

        except Exception as e:
            self.logger.error(f"❌ Transcription failed: {e}")
            raise

    def _save_transcript(self, transcript_data, source_file):
        """Save transcript data to JSON file"""
        try:
            # Generate output filename
            source_name = Path(source_file).stem
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = self.transcriptions_dir / f"{source_name}_transcript_{timestamp}.json"

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
            summary_file = (self.base_dir / "programs" / "video_summarizer" / "output" /
                          "article_summaries" / f"{source_name}_transcript_summary_{timestamp}.html")
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
        print("Usage: python file_transcriber.py <audio_or_video_file> [language]")
        print("Example: python file_transcriber.py /path/to/audio.mp3")
        print("Example: python file_transcriber.py /path/to/video.mp4 en")
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