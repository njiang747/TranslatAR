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
from PIL import Image, ImageFont, ImageDraw
from AppKit import NSScreen
import textwrap

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
    speaker_num = 0


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


    def on_data_wrapper(sp_num):
        def on_data(ws, message, message_type, fin):
            """
            Callback executed when Websocket messages are received from the server.

            :param ws: Websocket client.
            :param message: Message data as utf-8 string.
            :param message_type: Message type: ABNF.OPCODE_TEXT or ABNF.OPCODE_BINARY.
            :param fin: Websocket FIN bit. If 0, the data continues.
            """
            global text, speaker_num

            data = json.loads(message)
            if data['type'] == 'final':
                speaker_num = sp_num
                text = data['translation']
            else:
                text = text + '.'
            print('\n', message, '\n')
        return on_data

    # translate_from, translate_to, device_id
    translations = [('zh-Hans', 'en-Us', 2)] # , [('en-Us', 'fr')]  # ('zh-Hans', 'en-Us'), ('es', 'en-Us')

    # Features requested by the client.
    features = 'Partial'

    for i in range(0, len(translations)):
        translate_from, translate_to, device_id = translations[i]
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
            on_data=on_data_wrapper(i),
            on_error=on_error,
            on_close=on_close
        )
        _thread.start_new_thread(ws_client.run_forever, ())

    # start video capture
    img_capture = cv2.VideoCapture(1)
    while True:
        _, img = img_capture.read()

        height, width, _ = img.shape
        scaledheight = screenheight
        scaledwidth = int(width * screenheight / height)

        img = cv2.resize(img, (scaledwidth, scaledheight))

        cutoff = int(scaledwidth / 2 - screenwidth / 4)
        cropped = img[:, cutoff:-cutoff, :]

        cropped = Image.fromarray(np.uint8(cropped))
        draw = ImageDraw.Draw(cropped)
        font = ImageFont.truetype("/Library/Fonts/Impact.ttf", 42, encoding="unic")
        margin = 70
        offset = screenheight - 10 * 40
        shadowcolor = "black"
        fillcolor = "white" if speaker_num == 0 else "cyan"

        for line in textwrap.wrap(text, width=35):
            draw.text((margin - 1, offset + 1), line, font=font, fill=shadowcolor)
            draw.text((margin - 1, offset - 1), line, font=font, fill=shadowcolor)
            draw.text((margin + 1, offset - 1), line, font=font, fill=shadowcolor)
            draw.text((margin + 1, offset + 1), line, font=font, fill=shadowcolor)
            draw.text((margin, offset), line, font=font, fill=fillcolor)

            offset += font.getsize(line)[1]

        cropped = np.array(cropped)
        comb = np.concatenate((cropped, cropped), axis=1)

        cv2.imshow('TranslatAR', comb)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
