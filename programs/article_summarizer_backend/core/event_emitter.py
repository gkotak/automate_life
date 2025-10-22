"""
Event Emitter for Server-Sent Events (SSE)

Allows the article processor to emit real-time progress updates
that are streamed to the frontend via SSE.
"""

import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ProcessingEventEmitter:
    """
    Manages events for article processing progress.
    Uses asyncio queues to pass events from processor to SSE stream.
    """

    # Global registry of active processing jobs
    _active_jobs: Dict[str, asyncio.Queue] = {}

    def __init__(self, job_id: str):
        self.job_id = job_id
        self.queue = asyncio.Queue()
        self.start_time = datetime.now()

        # Register this job
        ProcessingEventEmitter._active_jobs[job_id] = self.queue

        logger.info(f"📡 [SSE] Created event emitter for job {job_id}")

    async def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        """
        Emit an event to be streamed via SSE

        Args:
            event_type: Type of event (e.g., 'fetch_start', 'media_detected')
            data: Additional data to include in the event
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()

        event = {
            'type': event_type,
            'elapsed': int(elapsed),
            'timestamp': datetime.now().isoformat(),
            'data': data or {}
        }

        await self.queue.put(event)
        logger.info(f"📡 [SSE] Emitted {event_type} for job {self.job_id}")

        # CRITICAL: Give control to event loop so generator can consume
        await asyncio.sleep(0)

    async def complete(self):
        """Mark processing as complete and close the event stream"""
        await self.emit('complete', {'message': 'Processing finished'})
        await self.queue.put(None)  # Sentinel to close stream

        # Cleanup after a delay to allow final events to be sent
        asyncio.create_task(self._cleanup_after_delay())

    async def error(self, error_message: str):
        """Emit an error event"""
        await self.emit('error', {'message': error_message})
        await self.queue.put(None)
        asyncio.create_task(self._cleanup_after_delay())

    async def _cleanup_after_delay(self):
        """Remove job from registry after a delay"""
        await asyncio.sleep(5)  # Wait 5 seconds before cleanup
        if self.job_id in ProcessingEventEmitter._active_jobs:
            del ProcessingEventEmitter._active_jobs[self.job_id]
            logger.info(f"📡 [SSE] Cleaned up job {self.job_id}")

    @classmethod
    def get_emitter(cls, job_id: str) -> Optional['ProcessingEventEmitter']:
        """Get an existing event emitter by job ID"""
        queue = cls._active_jobs.get(job_id)
        if queue:
            emitter = cls.__new__(cls)
            emitter.job_id = job_id
            emitter.queue = queue
            return emitter
        return None

    @classmethod
    async def stream_events(cls, job_id: str):
        """
        Generator that yields SSE-formatted events for a job

        This is used by the FastAPI SSE endpoint to stream events
        """
        queue = cls._active_jobs.get(job_id)
        if not queue:
            logger.warning(f"📡 [SSE] No active job found for {job_id}")
            yield {
                "event": "error",
                "data": json.dumps({"message": "Job not found"})
            }
            return

        logger.info(f"📡 [SSE] Started streaming events for job {job_id}")

        # Send a ping event immediately to test connection
        # Add padding to force Railway proxy to flush the response
        logger.info(f"📡 [SSE] Sending initial ping for job {job_id}")
        padding = " " * 2048  # 2KB padding to force flush
        yield {
            "event": "ping",
            "data": json.dumps({
                "message": "SSE connection established",
                "_padding": padding  # Forces proxy to flush
            })
        }
        await asyncio.sleep(0)  # Give control back to event loop

        # Keep-alive heartbeat to prevent connection timeout
        last_heartbeat = datetime.now()

        while True:
            try:
                # Wait for event with timeout to send periodic heartbeats
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
            except asyncio.TimeoutError:
                # No event received in 15 seconds, send heartbeat
                logger.debug(f"📡 [SSE] Sending heartbeat for job {job_id}")
                padding = " " * 2048
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "_padding": padding
                    })
                }
                await asyncio.sleep(0)  # Give control back to event loop
                continue

            if event is None:  # Sentinel value means stream is done
                logger.info(f"📡 [SSE] Stream closed for job {job_id}")
                break

            # Log each event being sent
            logger.info(f"📡 [SSE] Streaming event '{event['type']}' for job {job_id}")

            # Format as SSE event with padding to force Railway to flush
            padding = " " * 2048  # 2KB padding
            yield {
                "event": event['type'],
                "data": json.dumps({
                    'elapsed': event['elapsed'],
                    'timestamp': event['timestamp'],
                    **event['data'],
                    '_padding': padding  # Forces nginx to flush immediately
                })
            }

            # CRITICAL: Give control back to event loop to actually send the event
            # Without this, all events get consumed from queue instantly before sending
            await asyncio.sleep(0)
