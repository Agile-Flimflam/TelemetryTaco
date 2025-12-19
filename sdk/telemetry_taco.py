import threading
import json
import urllib.request
import urllib.error
from typing import Any


class TelemetryTaco:
    """
    TelemetryTaco SDK for capturing events.
    
    This SDK sends events to the TelemetryTaco backend in a non-blocking manner
    using background threads.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the TelemetryTaco client.
        
        Args:
            base_url: Base URL of the TelemetryTaco backend (default: http://localhost:8000)
        """
        self.base_url = base_url.rstrip('/')
        self.capture_url = f"{self.base_url}/api/capture"
    
    def capture(
        self,
        distinct_id: str,
        event_name: str,
        properties: dict[str, Any] | None = None
    ) -> None:
        """
        Capture an event in a background thread.
        
        This method runs the HTTP POST request in a separate thread, ensuring
        it doesn't block the main application thread.
        
        Args:
            distinct_id: Unique identifier for the user/entity
            event_name: Name of the event being captured
            properties: Optional dictionary of event properties (default: {})
        """
        if properties is None:
            properties = {}
        
        # Create a thread to handle the HTTP request
        thread = threading.Thread(
            target=self._send_event,
            args=(distinct_id, event_name, properties),
            daemon=True  # Daemon thread won't prevent program exit
        )
        thread.start()
    
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
            # Log error (in production, you might want to use logging module)
            print(f"HTTP error capturing event: {e.code} - {e.reason}")
        except urllib.error.URLError as e:
            # Log network error
            print(f"Network error capturing event: {e.reason}")
        except Exception as e:
            # Log any other unexpected errors
            print(f"Unexpected error capturing event: {e}")


if __name__ == '__main__':
    # Example usage
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
    
    # Give threads a moment to complete (optional, for demo purposes)
    import time
    time.sleep(0.5)
