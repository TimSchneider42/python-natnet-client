# Python NatNet Client

Python client for Optitrack NatNet streams.

## Installation

Install this package via pip:

```bash
pip install git+https://github.com/TimSchneider42/python-natnet-client
```

## Usage

The following example highlights the basic usage of this package:

```python
import time

from natnet_client import DataDescriptions, DataFrame, NatNetClient


def receive_new_frame(data_frame: DataFrame):
    global num_frames
    num_frames += 1


def receive_new_desc(desc: DataDescriptions):
    print("Received data descriptions.")


num_frames = 0
if __name__ == "__main__":
    streaming_client = NatNetClient(server_ip_address="127.0.0.1", local_ip_address="127.0.0.1", use_multicast=False)
    streaming_client.on_data_description_received_event.handlers.append(receive_new_desc)
    streaming_client.on_data_frame_received_event.handlers.append(receive_new_frame)

    with streaming_client:
        streaming_client.request_modeldef()

        for i in range(10):
            time.sleep(1)
            streaming_client.update_sync()
            print(f"Received {num_frames} frames in {i + 1}s")
```

In this example, we first instantiate `NatNetClient` with the connection parameters and attach one callback function to
each of its events. The `streaming_client.on_data_description_received_event` event is triggered whenever a new data
description packet arrives, while the `streaming_client.on_data_frame_received_event` event is triggered on each
incoming data frame. For the configuration of the NatNet server, please refer to the official documentation.

You can process data synchronously, as in this example, by calling `streaming_client.update_sync()` in your run loop.
Alternatively, you can call `streaming_client.run_async()` once after connecting, which will handle data asynchronously
in two additional threads.

We then use the `streaming_client` instance as a context manager, which is equivalent to
calling `streaming_client.connect()` (and `streaming_client.shutdown()` afterwards). After the client has been
connected, we request the model definitions from the server, which causes it to send a data description packet. Note
that data frames do not have to be explicitly requested, but are continuously streamed once a connection has been
established.

Apart from requesting model definitions, the `NatNetClient` class allows sending arbitrary commands to the NatNet server
via the `send_command` and `send_request` functions. For a list of different commands and requests, please refer to the
official documentations.

## Notes

As of Motive version 2.3, the marker positions of rigid bodies are only transmitted correctly if "Y-up" is selected in
the streaming pane. If "Z-up" is selected, the frame of the rigid bodies is rotated but the marker positions are not,
resulting in wrong positions of the markers relative to the rigid body.
