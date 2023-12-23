"""

Simple implementation of a websocket interface to faster-whisper or
whisper.cpp, intended to act like the "kaldi-gstreamer" voice recognition
server for use with Konele app clients from Android phones.

This uses faster-whisper, which can be installed like this:

pip install faster-whisper

This version keeps all received audio data in memory rather than temp file.

This version also incorporates some simple corrections by regex. For
example, if you are talking to someone named "Conor" and
whisper keeps writing this as "Conner" or "Connor" you can have the
transcription automatically change that. See "corrections" below.

example of open from konele. note the user-id in the url, which we send
back with responses:

"GET /client/ws/speech?lang=und&user-agent=RecognizerIntentActivity%2F1.8.14%3B+Google%2Fbarbet%2Flineage_barbet-userdebug+13+TQ1A.230105.001.A2+48648b48b6%3B+null%2Fnull&calling-package=null&user-id=066be6e0-3e5e-4d58-b2e5-fabdd7b549d3&partial=true&content-type=audio%2Fx-raw%2C+layout%3D%28string%29interleaved%2C+rate%3D%28int%2916000%2C+format%3D%28string%29S16LE%2C+channels%3D%28int%291 HTTP/1.1"

what lib can se use to parse that url?

client.py is a program in the kaldi-gstreamer github (link: FIXME) that
is used to test the server.

when client.py connects, this is written by program (or sublibrary) to stderr:
    192.168.1.211 - - [30/Jan/2023 10:42:33] "GET /client/ws/speech?content-type=audio%2Fx-raw%2C+layout%3D%28string%29interleaved%2C+rate%3D%28int%2916000%2C+format%3D%28string%29S16LE%2C+channels%3D%28int%291 HTTP/1.1" 101 46
when konele connects, this is written by this program (or sublibrary) to stderr:
    192.168.1.144 - - [30/Jan/2023 10:44:37] "GET /client/ws/speech?lang=und&user-agent=RecognizerIntentActivity%2F1.8.14%3B+Google%2Fbarbet%2Flineage_barbet-userdebug+13+TQ1A.230105.001.A2+48648b48b6%3B+null%2Fnull&calling-package=null&user-id=066be6e0-3e5e-4d58-b2e5-fabdd7b549d3&partial=true&content-type=audio%2Fx-raw%2C+layout%3D%28string%29interleaved%2C+rate%3D%28int%2916000%2C+format%3D%28string%29S16LE%2C+channels%3D%28int%291 HTTP/1.1" 101 46
    SO: konele is sending x-raw audio, interleaved, rate 16000, S16LE, channels 1
    with this rate, the audio will be 8000 samples/second (16 bits per sample)

the audio encoding is present in both, but only konele sends the
"user-id" info which is presumably sent back by server on each communication?

WHO is writing that URL?

limitations:
    audio must be 8k samples/second, each sample 16 bits signed, so 16KB/s of data
    only one request at a time
    no incremental results yet
    no authentication on connection

"""

from wsocket import WSocketApp, WebSocketError, run
import re
import numpy as np

from faster_whisper import WhisperModel

__author__ = "Rich Drewes"
__version__ = "1.0"
__license__ = "MIT"

model_size = "base.en"

# for some reason "tiny" model duplicates recognition output on my test file
# the "base" model does not have this problem

#logger.setLevel(10)  # for debugging

# RPD: later versions of wsocket want the "client" argument to on_close,
# but wsocket installed from pip right now does not want that arg
#def on_close(self, message, client):
def on_close(self, message):
    #print(repr(client) + " : " + message)
    print("close, message:" , message)

# does this override the on_connect in wsocket? or in addition to that (+=)?
def on_connect(client):
    # RPD: how print full URL of the connect?
    print("RPD: on_connect in minimal.py, client:", repr(client) + " connected")
    print("RPD: on_connect in minimal.py client path:", client.path)
    #exit()
    client.abuf=[]         # list of binary data segments that will be joined

model = WhisperModel(model_size, device="cpu", compute_type="int8")

# always make the following user-specific corrections
# for example, 99% of the time when I say Conor Drewes I am referring to
# my son Conor Drewes not Connor Drews!
corrections=[
        (r"Conner", "Conor"),
        (r"Connor", "Conor"),
        (r"Collin", "Colin"),
        (r"Drews", "Drewes")
        ]

def on_message(message, client):
    #print(repr(client) + " : " + repr(message))
    # messages with class 'bytearray' becomes class 'str' for EOS message
    #print(type(message))
    try:
        if isinstance(message, str):        # "EOS" message
            # what if this takes so long the client gives up? should send incremental results,
            # or a least pretend results, while we process
            audio_data = b"".join(client.abuf)
            print(f"audio buffer had {len(client.abuf)} segments, final length {len(audio_data)}")
            audio_np=np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            segments, _ = model.transcribe(audio_np)
            rr=[]
            for segment in segments:
                rr.append(segment.text)
            m=" ".join(rr)
            print("recognition result before strip:", m)
            m=m.strip()
            # sometimes whisper puts in commentary like [soft music] and we strip that out:
            print("recognition result before bracket re:", m)
            m=re.sub(r"\[.*\]", "", m)
            print("recognition result after bracket re:", m)
            # was having problems with things like "He said hello" which became He said, "Hello"
            m=re.sub(r'"', '\\"', m)          # convert " to \\"
            print("recognition result after quoting:", m)
            for a, b in corrections:
                m=re.sub(a, b, m)
            print("recognition result after site local corrections:", m)
            # send json result to konele client:
            msg=f'{{"status": 0, "segment": 0, "result": {{"hypotheses": [{{"transcript": "{m}"}}], "final": true}}, "id": "1aacc69d-3674-438a-b3c5-fc0ed51769a5"}}'
            print("msg is", msg)
            client.send(msg)
            client.close()
        else:   # hopefully message is <class 'bytearray'>, and we just accummulate audio data
            client.abuf.append(message)
            print(f"audio buf now has {len(client.abuf)} segments")

    except WebSocketError:
        print("WebSocketError")
        pass

app = WSocketApp()
app.onconnect += on_connect
app.onmessage += on_message
app.onclose += on_close

run(app, host="0.0.0.0", port=9002)
