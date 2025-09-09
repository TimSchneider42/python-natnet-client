import time

from natnet import DataDescriptions, DataFrame, NatNetClient


def receive_new_frame(data_frame: DataFrame):
    global num_frames
    num_frames += 1


def receive_new_desc(desc: DataDescriptions):
    print("Received data descriptions.")


num_frames = 0
if __name__ == "__main__":
    streaming_client = NatNetClient(
        server_ip_address="127.0.0.1", local_ip_address="127.0.0.1", use_multicast=False
    )
    streaming_client.on_data_description_received_event.handlers.append(
        receive_new_desc
    )
    streaming_client.on_data_frame_received_event.handlers.append(receive_new_frame)

    with streaming_client:
        streaming_client.request_modeldef()

        for i in range(10):
            time.sleep(1)
            streaming_client.update_sync()
            print(f"Received {num_frames} frames in {i + 1}s")
