"""Images events routes for real-time image change notifications via SSE."""

from __future__ import (
    annotations,
)

import json
import logging
import queue
import threading
from collections.abc import (
    Callable,
)
from datetime import (
    datetime,
    timezone,
)
from typing import (
    TYPE_CHECKING,
    Any,
)

from flask import (
    Response,
    stream_with_context,
)

if TYPE_CHECKING:
    from flask import (
        Flask,
    )

    from pumaguard.web_ui import (
        WebUI,
    )

logger = logging.getLogger(__name__)


def register_images_events_routes(
    app: "Flask",
    webui: "WebUI",  # pylint: disable=unused-argument
) -> Callable[[str, dict[str, Any]], None]:
    """
    Register image events SSE endpoint.

    Provides a Server-Sent Events stream that notifies connected clients
    whenever images are added to or deleted from watched/classification
    directories.

    Args:
        app: The Flask application instance.
        webui: The WebUI instance (reserved for future use).

    Returns:
        A callback function ``notify_image_change(event_type, image_data)``
        that callers invoke to push events to all connected SSE clients.
    """

    # Queue-per-client pattern (same as camera events in dhcp.py)
    sse_clients: list[queue.Queue[dict[str, Any]]] = []
    sse_clients_lock = threading.Lock()

    def notify_image_change(
        event_type: str, image_data: dict[str, Any]
    ) -> None:
        """
        Notify all connected SSE clients about an image change.

        Args:
            event_type: One of ``"image_added"`` or ``"image_deleted"``.
            image_data: Arbitrary dict describing the change (e.g. path /
                        folder information).
        """
        message: dict[str, Any] = {
            "type": event_type,
            "data": image_data,
            "timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }

        with sse_clients_lock:
            disconnected: list[queue.Queue[dict[str, Any]]] = []
            for client_queue in sse_clients:
                try:
                    client_queue.put(message, block=False)
                except queue.Full:
                    # The client is not draining its queue – mark for removal.
                    disconnected.append(client_queue)

            for client_queue in disconnected:
                sse_clients.remove(client_queue)
                logger.debug("Removed stale image SSE client (queue full)")

    @app.route("/api/images/events", methods=["GET"])
    def image_events():
        """
        Server-Sent Events endpoint for real-time image change notifications.

        Clients receive a stream of newline-delimited JSON events:

        .. code-block:: json

            {
                "type": "image_added",
                "data": {
                    "path": "/abs/path/to/image.jpg",
                    "folder": "/abs/path/to/classification/folder"
                },
                "timestamp": "2024-01-01T00:00:00Z"
            }

        Supported ``type`` values:

        * ``connected``   – Sent once when the client first connects.
        * ``image_added`` – A new image was classified and placed in a folder.
        * ``image_deleted`` – An image was removed via the REST API.

        A ``: keepalive`` comment is emitted every 30 seconds to prevent
        proxy/browser timeouts when no real events have occurred.
        """

        def event_stream():
            client_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=10)

            with sse_clients_lock:
                sse_clients.append(client_queue)

            logger.info(
                "Image SSE client connected, total clients: %d",
                len(sse_clients),
            )

            try:
                # Send an initial "connected" event so the client knows the
                # stream is live before any real events arrive.
                initial_msg: dict[str, Any] = {
                    "type": "connected",
                    "timestamp": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                }
                yield f"data: {json.dumps(initial_msg)}\n\n"

                while True:
                    try:
                        message = client_queue.get(timeout=30)
                        yield f"data: {json.dumps(message)}\n\n"
                    except queue.Empty:
                        # Send a keepalive comment to prevent proxy/browser
                        # from closing an idle connection.
                        yield ": keepalive\n\n"

            except GeneratorExit:
                logger.info("Image SSE client disconnected (GeneratorExit)")
            finally:
                with sse_clients_lock:
                    if client_queue in sse_clients:
                        sse_clients.remove(client_queue)
                logger.info(
                    "Image SSE client removed, remaining clients: %d",
                    len(sse_clients),
                )

        return Response(
            stream_with_context(event_stream()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    return notify_image_change
