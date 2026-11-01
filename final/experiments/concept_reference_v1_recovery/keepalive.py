"""One recorded notebook keepalive per20minutes, following private endpoint updates."""
import threading

from final.pipeline import save
from .model import QwenModel, TransportError


class KeepAlive:
    def __init__(self, output_directory):
        self.output_directory = output_directory
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *arguments):
        self.stop_event.set()
        self.thread.join(timeout=2)

    def run(self):
        existing_indices = []
        for record_path in (self.output_directory / "keepalive").glob("*.json"):
            if record_path.stem.isdigit():
                existing_indices.append(int(record_path.stem))
        sequence_number = max(existing_indices, default=-1) + 1
        while not self.stop_event.wait(1200):
            record_path = self.output_directory / "keepalive" / f"{sequence_number:04d}.json"
            sequence_number += 1
            completion_started = False
            try:
                model = QwenModel(timeout=60)
                model.check_endpoint()
                prepared = model.prepare_generation([{"role": "user", "content": "ping"}], 1)
                completion_started = True
                save(record_path, {"state": "started", "completion_started": True})
                response = model.generate_prepared(prepared, temperature=0, seed=0)
                save(record_path, {"state": "received", "completion_started": True, "usage": response.usage})
            except TransportError as error:
                save(record_path, {"state": "unknown" if completion_started else "not_sent",
                                   "completion_started": completion_started, "error": error.details()})
