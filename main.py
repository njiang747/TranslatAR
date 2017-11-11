"""
Python sample demonstrating use of Microsoft Translator Speech Translation API.
"""

import os
import io
import struct
import _thread
import time
import uuid
import wave
import sys
import pyaudio

import websocket


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


class WaveFileAudioSource(object):
    """
    Provides a way to read audio from the DATA section of a WAV file in chunks of
    a specified duration.
    """

    def __init__(self, path, chunk_length, silence_duration):
        """
        :param path: Path to WAV file. Acceptable WAV files use PCM single channel
            with 16-bit samples and sampling frequency of 8 kHz or 16 kHz.
        :param chunk_length: Length of chunk in milliseconds. The chunk length should
            be a multiple of 10ms and in the range from 100ms to 1000ms.
        :param silence_duration: Optionally follow audio from the file with silence.
            Speech recognizer uses silence to find end of utterances. Silence duration
            is given in milliseconds.
        """
        self.input = wave.open(path, 'rb')

        if self.input.getnchannels() != 1:
            raise ValueError("Input audio file should have a single channel.")
        if self.input.getframerate() not in [8000, 16000]:
            raise ValueError("Input audio file should have sampling frequency of 8 or 16 kHz.")
        if self.input.getsampwidth() != 2:
            raise ValueError("Input audio file should have 16-bit samples.")
        if chunk_length % 10 != 0 or chunk_length < 100 or chunk_length > 1000:
            raise ValueError("Chunk length is too small, too large or not a multiple of 10 ms.")

        self.chunk_length = chunk_length
        self.chunk_size = int(self.input.getframerate() / (1000.0 / chunk_length))
        self.silence_duration = silence_duration
        self.silence_chunk = [0] * (2 * self.chunk_size)
        self.eof_reached = False

    def getframerate(self):
        return self.input.getframerate()

    def close(self):
        self.input.close()

    def __iter__(self):
        return self

    def __next__(self):
        if not self.eof_reached:
            data = self.input.readframes(self.chunk_size)
            if len(data) > 0:
                return data
            self.eof_reached = True
        if self.silence_duration > 0:
            self.silence_duration -= self.chunk_length
            return self.silence_chunk
        raise StopIteration


if __name__ == "__main__":
    client_secret = '7a403254d0ea4998af9b03a836361618'

    # Audio file(s) to transcribe
    audio_file = 'audio_files/CHI101-Lesson1.wav'
    audio_source = WaveFileAudioSource(audio_file, 100, 2000)
    # Translate from this language. The language must match the source audio.
    # Supported languages are given by the 'speech' scope of the supported languages API.
    translate_from = 'zh-Hans'
    # Translate to this language.
    # Supported languages are given by the 'text' scope of the supported languages API.
    translate_to = 'en-US'
    # Features requested by the client.
    features = 'Partial'


    # Setup functions for the Websocket connection
    def on_open(ws):
        """
        Callback executed once the Websocket connection is opened.
        This function handles streaming of audio to the server.

        :param ws: Websocket client.
        """
        print('Connected. Server generated request ID = ', ws.sock.headers['x-requestid'])

        def run(*args):
            """Background task which streams audio."""

            # Send WAVE header to provide audio format information
            data = get_wave_header(audio_source.getframerate())
            ws.send(data, websocket.ABNF.OPCODE_BINARY)

            # Send input data from the mic to be translated
            WIDTH = 2
            CHANNELS = 1
            RATE = 16000

            p = pyaudio.PyAudio()

            def callback(in_data, frame_count, time_info, status):
                ws.send(in_data, websocket.ABNF.OPCODE_BINARY)
                return (in_data, pyaudio.paContinue)

            stream = p.open(format=p.get_format_from_width(WIDTH),
                            channels=CHANNELS,
                            rate=RATE,
                            input=True,
                            output=True,
                            stream_callback=callback)

            stream.start_stream()

            while stream.is_active():
                time.sleep(0.1)

            stream.stop_stream()
            stream.close()

            p.terminate()

        _thread.start_new_thread(run, ())


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


    def on_data(ws, message, message_type, fin):
        """
        Callback executed when Websocket messages are received from the server.

        :param ws: Websocket client.
        :param message: Message data as utf-8 string.
        :param message_type: Message type: ABNF.OPCODE_TEXT or ABNF.OPCODE_BINARY.
        :param fin: Websocket FIN bit. If 0, the data continues.
        """
        print('\n', message, '\n')
        # if message_type == websocket.ABNF.OPCODE_TEXT:
        #     print('\n', message, '\n')
        # else:
        #     tts_count = tts_state['count']
        #     tts_file = tts_state.get('file', None)
        #     if tts_file is None:
        #         tts_count += 1
        #         tts_state['count'] = tts_count

        #         fname = "tts_{0}.wav".format(tts_count)
        #         print("\nTTS segment #{0} begins (file name: '{1}').\n".format(tts_count, fname))
        #         if not os.path.exists(output_folder):
        #             os.makedirs(output_folder)
        #         tts_file = open(os.path.join(output_folder, fname), 'wb')
        #         tts_state['file'] = tts_file
        #     tts_file.write(message)
        #     if fin:
        #         print('\n', "TTS segment #{0} ends.'.".format(tts_count), '\n')
        #         tts_file.close()
        #         del tts_state['file']


    client_trace_id = str(uuid.uuid4())
    request_url = "wss://dev.microsofttranslator.com/speech/translate?from={0}&to={1}&features={2}&api-version=1.0".format(
        translate_from, translate_to, features)

    print("Ready to connect...")
    print("Request URL      = {0})".format(request_url))
    print("ClientTraceId    = {0}".format(client_trace_id))

    ws_client = websocket.WebSocketApp(
        request_url,
        header=[
            'Ocp-Apim-Subscription-Key: ' + client_secret,
            'X-ClientTraceId: ' + client_trace_id
        ],
        on_open=on_open,
        on_data=on_data,
        on_error=on_error,
        on_close=on_close
    )
    ws_client.run_forever()
