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
        self.logs_dir = base_dir / "programs" / "article_summarizer" / "logs"
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

            # Call Claude CLI via pipe (echo/cat method)
            # Direct stdin fails with large prompts, but piping through cat/echo works
            # This is a workaround for a Claude CLI stdin handling issue
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8')
            temp_file.write(prompt)
            temp_file.close()

            try:
                # Use cat to pipe the prompt - this works where direct stdin doesn't
                shell_cmd = f"cat {temp_file.name} | {self.claude_cmd} --print --output-format text"
                self.logger.info(f"   🔧 [DEBUG] Running command: cat [temp] | {self.claude_cmd} --print --output-format text")
                self.logger.info(f"   🔧 [DEBUG] Prompt length: {len(prompt)} chars, using cat pipe")

                result = subprocess.run(
                    shell_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    timeout=300
                )
            finally:
                # Clean up temp file
                import os
                try:
                    os.unlink(temp_file.name)
                except:
                    pass

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
                return f"Error calling Claude API: {stderr}"

            if not response:
                self.logger.warning(f"   ⚠️ Claude API returned empty response (stderr: {stderr[:200]})")

            return response

        except subprocess.TimeoutExpired:
            self.logger.error("   ❌ Claude API call timed out after 300 seconds")
            return "Claude API call timed out after 300 seconds"
        except Exception as e:
            self.logger.error(f"   ❌ Exception in Claude API call: {str(e)}")
            return f"Error in Claude API call: {str(e)}"
