import threading
import json
import logging
import urllib.request
import urllib.error
from typing import Any

# Create a logger for the SDK
# Users can configure this logger using: logging.getLogger('telemetry_taco')
logger = logging.getLogger('telemetry_taco')


class TelemetryTaco:
    """
    TelemetryTaco SDK for capturing events.
    
    This SDK sends events to the TelemetryTaco backend in a non-blocking manner
    using background threads. Threads are non-daemon to prevent data loss on exit.
    Use flush() or the context manager to ensure all events are sent before program exit.
    
    Logging:
        The SDK uses Python's logging module. Configure the logger using:
        
        ```python
        import logging
        logging.getLogger('telemetry_taco').setLevel(logging.WARNING)
        ```
        
        Or configure logging globally:
        
        ```python
        import logging
        logging.basicConfig(level=logging.INFO)
        ```
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the TelemetryTaco client.
        
        Args:
            base_url: Base URL of the TelemetryTaco backend (default: http://localhost:8000)
        """
        self.base_url = base_url.rstrip('/')
        self.capture_url = f"{self.base_url}/api/capture"
        self._active_threads: list[threading.Thread] = []
        self._threads_lock = threading.Lock()
    
    def capture(
        self,
        distinct_id: str,
        event_name: str,
        properties: dict[str, Any] | None = None
    ) -> None:
        """
        Capture an event in a background thread.
        
        This method runs the HTTP POST request in a separate thread, ensuring
        it doesn't block the main application thread. The thread is non-daemon
        to prevent data loss on program exit. Use flush() to wait for completion.
        
        Args:
            distinct_id: Unique identifier for the user/entity
            event_name: Name of the event being captured
            properties: Optional dictionary of event properties (default: {})
        """
        if properties is None:
            properties = {}
        
        # Create a non-daemon thread to handle the HTTP request
        # Non-daemon threads ensure events are sent before program exit
        thread = threading.Thread(
            target=self._send_event_with_cleanup,
            args=(distinct_id, event_name, properties),
            daemon=False  # Non-daemon to prevent data loss on exit
        )
        
        with self._threads_lock:
            self._active_threads.append(thread)
        
        thread.start()
    
    def _send_event_with_cleanup(
        self,
        distinct_id: str,
        event_name: str,
        properties: dict[str, Any]
    ) -> None:
        """
        Wrapper method that sends the event and removes thread from active list.
        
        Args:
            distinct_id: Unique identifier for the user/entity
            event_name: Name of the event being captured
            properties: Dictionary of event properties
        """
        try:
            self._send_event(distinct_id, event_name, properties)
        finally:
            # Remove this thread from active threads list
            current_thread = threading.current_thread()
            with self._threads_lock:
                if current_thread in self._active_threads:
                    self._active_threads.remove(current_thread)
    
    def _send_event(
        self,
        distinct_id: str,
        event_name: str,
        properties: dict[str, Any]
    ) -> None:
        """
        Internal method to send the event via HTTP POST.
        
        This method runs in a background thread and handles the actual
        HTTP request to the backend.
        
        Args:
            distinct_id: Unique identifier for the user/entity
            event_name: Name of the event being captured
            properties: Dictionary of event properties
        """
        payload = {
            "distinct_id": distinct_id,
            "event_name": event_name,
            "properties": properties
        }
        
        try:
            # Serialize payload to JSON
            json_data = json.dumps(payload).encode('utf-8')
            
            # Create HTTP request
            req = urllib.request.Request(
                self.capture_url,
                data=json_data,
                headers={
                    'Content-Type': 'application/json',
                    'Content-Length': str(len(json_data))
                },
                method='POST'
            )
            
            # Send request (non-blocking in this thread)
            with urllib.request.urlopen(req, timeout=5) as response:
                # Read response to ensure request completes
                response.read()
                
        except urllib.error.HTTPError as e:
            logger.error(
                "HTTP error capturing event: %s - %s",
                e.code,
                e.reason,
                extra={
                    'event_name': event_name,
                    'distinct_id': distinct_id,
                    'status_code': e.code
                }
            )
        except urllib.error.URLError as e:
            logger.warning(
                "Network error capturing event: %s",
                e.reason,
                extra={
                    'event_name': event_name,
                    'distinct_id': distinct_id
                },
                exc_info=True
            )
        except Exception as e:
            logger.error(
                "Unexpected error capturing event: %s",
                e,
                extra={
                    'event_name': event_name,
                    'distinct_id': distinct_id
                },
                exc_info=True
            )
    
    def flush(self, timeout: float | None = None) -> None:
        """
        Wait for all pending event threads to complete.
        
        This method blocks until all active background threads have finished
        sending their events. Use this before program exit to ensure no data loss.
        
        Args:
            timeout: Maximum time to wait in seconds (None = wait indefinitely)
        
        Raises:
            TimeoutError: If timeout is exceeded and threads are still active
        """
        # Make a copy of active threads to avoid modification during iteration
        with self._threads_lock:
            threads_to_wait = list(self._active_threads)
        
        for thread in threads_to_wait:
            thread.join(timeout=timeout)
            if thread.is_alive():
                # Count remaining active threads
                with self._threads_lock:
                    remaining_count = len(self._active_threads)
                raise TimeoutError(
                    f"Timeout waiting for event thread to complete. "
                    f"{remaining_count} threads still active."
                )
    
    def __enter__(self) -> "TelemetryTaco":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - ensures all events are sent before exit."""
        self.flush()


if __name__ == '__main__':
    # Example usage - Method 1: Using flush() explicitly
    client = TelemetryTaco()
    
    # Capture a simple event
    client.capture(
        distinct_id="user_123",
        event_name="button_clicked",
        properties={
            "button_name": "signup",
            "page": "homepage"
        }
    )
    
    # Capture another event with different properties
    client.capture(
        distinct_id="user_456",
        event_name="page_view",
        properties={
            "page_url": "/dashboard",
            "referrer": "google.com"
        }
    )
    
    # The capture calls are non-blocking, so this will print immediately
    print("Events sent in background threads!")
    
    # Wait for all events to be sent before exit (prevents data loss)
    client.flush()
    print("All events sent successfully!")
    
    # Example usage - Method 2: Using context manager (recommended)
    print("\n--- Using context manager ---")
    with TelemetryTaco() as client2:
        client2.capture(
            distinct_id="user_789",
            event_name="test_event",
            properties={"test": True}
        )
        print("Event queued, will be sent before context exit")
    # All events are automatically flushed when exiting the context
    print("Context exited, all events sent!")
