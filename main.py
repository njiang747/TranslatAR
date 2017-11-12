import io
import struct
import _thread
import time
import uuid
import pyaudio
import websocket
import numpy as np
import cv2
import json
from AppKit import NSScreen

screenwidth = int(NSScreen.mainScreen().frame().size.width)
screenheight = int(NSScreen.mainScreen().frame().size.height)


def get_wave_header(frame_rate):
    """
    Generate WAV header that precedes actual audio data sent to the speech translation service.

    :param frame_rate: Sampling frequency (8000 for 8kHz or 16000 for 16kHz).
    :return: binary string
    """
    if frame_rate not in [8000, 16000]:
        raise ValueError("Sampling frequency, frame_rate, should be 8000 or 16000.")

    nchannels = 1
    bytes_per_sample = 2

    output = io.BytesIO()
    output.write(str.encode('RIFF'))
    output.write(struct.pack('<L', 0))
    output.write(str.encode('WAVE'))
    output.write(str.encode('fmt '))
    output.write(struct.pack('<L', 18))
    output.write(struct.pack('<H', 0x0001))
    output.write(struct.pack('<H', nchannels))
    output.write(struct.pack('<L', frame_rate))
    output.write(struct.pack('<L', frame_rate * nchannels * bytes_per_sample))
    output.write(struct.pack('<H', nchannels * bytes_per_sample))
    output.write(struct.pack('<H', bytes_per_sample * 8))
    output.write(struct.pack('<H', 0))
    output.write(str.encode('data'))
    output.write(struct.pack('<L', 0))

    data = output.getvalue()

    output.close()

    return data


if __name__ == "__main__":
    client_secret = '7a403254d0ea4998af9b03a836361618'
    text = ''

    # Setup functions for the Websocket connection
    def on_open_wrapper(device_id):
        def on_open(ws):
            """
            Callback executed once the Websocket connection is opened.
            This function handles streaming of audio to the server.

            :param ws: Websocket client.
            """
            print('Connected. Server generated request ID = ', ws.sock.headers['x-requestid'])

            def run(*args):
                """Background task which streams audio."""

                # Send input data from the mic to be translated
                msg_width = 2
                channels = 1
                framerate = 16000

                # Send WAVE header to provide audio format information
                data = get_wave_header(framerate)
                ws.send(data, websocket.ABNF.OPCODE_BINARY)

                p = pyaudio.PyAudio()

                def callback(in_data, frame_count, time_info, status):
                    ws.send(in_data, websocket.ABNF.OPCODE_BINARY)
                    return (in_data, pyaudio.paContinue)

                stream = p.open(format=p.get_format_from_width(msg_width),
                                channels=channels,
                                rate=framerate,
                                input=True,
                                output=False,
                                input_device_index=device_id,
                                stream_callback=callback)

                stream.start_stream()

                while stream.is_active():
                    time.sleep(0.1)

                stream.stop_stream()
                stream.close()

                p.terminate()

            _thread.start_new_thread(run, ())
        return on_open

    def on_close(ws):
        """
        Callback executed once the Websocket connection is closed.

        :param ws: Websocket client.
        """
        print('Connection closed...')


    def on_error(ws, error):
        """
        Callback executed when an issue occurs during the connection.

        :param ws: Websocket client.
        """
        print(error)

    # make a wrapper to generate different on_data functions that change different text
    def on_data(ws, message, message_type, fin):
        """
        Callback executed when Websocket messages are received from the server.

        :param ws: Websocket client.
        :param message: Message data as utf-8 string.
        :param message_type: Message type: ABNF.OPCODE_TEXT or ABNF.OPCODE_BINARY.
        :param fin: Websocket FIN bit. If 0, the data continues.
        """
        global text

        data = json.loads(message)
        text = data['translation']
        print('\n', message, '\n')


    # Languages: en-Us, zh-Hans, es, hi
    translations = [ ('en-Us', 'zh-Hans', 2), ('es', 'en-Us', 0)] #[('en-Us', 'fr')]  # ('zh-Hans', 'en-Us'), ('es', 'en-Us')

    # Features requested by the client.
    features = 'Partial'

    for translate_from, translate_to, device_id in translations:
        client_trace_id = str(uuid.uuid4())
        request_url = "wss://dev.microsofttranslator.com/speech/translate?from={0}&to={1}&features={2}&api-version=1.0".format(
            translate_from, translate_to, features)

        ws_client = websocket.WebSocketApp(
            request_url,
            header=[
                'Ocp-Apim-Subscription-Key: ' + client_secret,
                'X-ClientTraceId: ' + client_trace_id,
            ],
            on_open=on_open_wrapper(device_id),
            on_data=on_data,
            on_error=on_error,
            on_close=on_close
        )
        _thread.start_new_thread(ws_client.run_forever, ())

    # start video capture
    left = cv2.VideoCapture(0)
    right = cv2.VideoCapture(0)
    while True:
        _, left_img = left.read()
        _, right_img = right.read()

        height, width, _ = left_img.shape
        scaledheight = screenheight
        scaledwidth = int(width * screenheight / height)

        left_img = cv2.resize(left_img, (scaledwidth, scaledheight))
        right_img = cv2.resize(right_img, (scaledwidth, scaledheight))

        cutoff = int(scaledwidth / 2 - screenwidth / 4)

        comb = np.concatenate((left_img[:, cutoff:-cutoff, :], right_img[:, cutoff:-cutoff, :]), axis=1)

        cv2.putText(comb, text, (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, 255)

        cv2.imshow('dongLe', comb)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
