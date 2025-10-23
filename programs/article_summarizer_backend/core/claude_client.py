#!/usr/bin/env python3
"""
Claude CLI Client
Handles all interactions with Claude CLI
"""

import subprocess
import logging
from pathlib import Path
from typing import Optional


class ClaudeClient:
    """Client for interacting with Claude CLI"""

    def __init__(self, claude_cmd: str, base_dir: Path, logger: logging.Logger):
        """
        Initialize Claude client

        Args:
            claude_cmd: Path to Claude CLI executable
            base_dir: Base directory for log files
            logger: Logger instance
        """
        self.claude_cmd = claude_cmd
        self.base_dir = base_dir
        self.logger = logger
        self.logs_dir = base_dir / "programs" / "article_summarizer_backend" / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def call_api(self, prompt: str) -> str:
        """
        Call Claude CLI API with a prompt

        Args:
            prompt: The prompt to send to Claude

        Returns:
            Claude's response as a string
        """
        try:
            # Log prompt details
            prompt_length = len(prompt)
            self.logger.info(f"   🤖 [CLAUDE API] Sending prompt ({prompt_length} chars)")

            # Save prompt to debug file
            debug_file = self.logs_dir / "debug_prompt.txt"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            self.logger.info(f"   💾 [DEBUG] Full prompt saved to: {debug_file}")

            # Use Anthropic Python SDK directly instead of CLI
            # Claude CLI has issues with large prompts via stdin
            self.logger.info(f"   🔧 [DEBUG] Using Anthropic Python SDK")
            self.logger.info(f"   🔧 [DEBUG] Prompt length: {len(prompt)} chars")

            import anthropic
            import os
            from dotenv import load_dotenv

            # Load environment variables from root .env.local
            env_file = self.base_dir / '.env.local'
            load_dotenv(env_file)

            # Get API key from environment
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")

            client = anthropic.Anthropic(api_key=api_key)

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            response = message.content[0].text

            result = type('Result', (), {
                'returncode': 0,
                'stdout': response,
                'stderr': ''
            })()

            # Log result details
            self.logger.info(f"   🔧 [DEBUG] Return code: {result.returncode}")
            self.logger.info(f"   🔧 [DEBUG] STDOUT length: {len(result.stdout)} chars")
            self.logger.info(f"   🔧 [DEBUG] STDERR length: {len(result.stderr)} chars")

            # Save response and stderr for debugging
            response_file = self.logs_dir / "debug_response.txt"
            stderr_file = self.logs_dir / "debug_stderr.txt"

            response = result.stdout.strip()
            stderr = result.stderr.strip()

            with open(response_file, 'w', encoding='utf-8') as f:
                f.write(f"=== CLAUDE RESPONSE ({len(response)} chars) ===\n")
                f.write(response)
                f.write(f"\n=== END RESPONSE ===\n")

            with open(stderr_file, 'w', encoding='utf-8') as f:
                f.write(f"=== STDERR (return code: {result.returncode}) ===\n")
                f.write(stderr)
                f.write(f"\n=== END STDERR ===\n")

            self.logger.info(f"   💾 [DEBUG] Response saved to: {response_file}")
            self.logger.info(f"   💾 [DEBUG] Stderr saved to: {stderr_file}")

            # Check for errors
            if result.returncode != 0:
                self.logger.error(f"   ❌ Claude API failed with return code {result.returncode}")
                self.logger.error(f"   ❌ Stderr: {stderr[:500]}")
                raise RuntimeError(f"Claude API failed with return code {result.returncode}: {stderr}")

            if not response:
                self.logger.warning(f"   ⚠️ Claude API returned empty response (stderr: {stderr[:200]})")
                raise RuntimeError(f"Claude API returned empty response: {stderr}")

            return response

        except subprocess.TimeoutExpired as e:
            self.logger.error("   ❌ Claude API call timed out after 300 seconds")
            raise TimeoutError("Claude API call timed out after 300 seconds") from e
        except Exception as e:
            self.logger.error(f"   ❌ Exception in Claude API call: {str(e)}")
            # Re-raise the exception instead of returning error string
            raise
