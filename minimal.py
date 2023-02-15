"""

Simple implementation of a websocket interface to whisper.cpp, intended
to act like the "kaldi-gstreamer" voice recognition server for use with
Konele app clients from Android phones.

example of open from konele. note the user-id in the url, which we send back with responses:

"GET /client/ws/speech?lang=und&user-agent=RecognizerIntentActivity%2F1.8.14%3B+Google%2Fbarbet%2Flineage_barbet-userdebug+13+TQ1A.230105.001.A2+48648b48b6%3B+null%2Fnull&calling-package=null&user-id=066be6e0-3e5e-4d58-b2e5-fabdd7b549d3&partial=true&content-type=audio%2Fx-raw%2C+layout%3D%28string%29interleaved%2C+rate%3D%28int%2916000%2C+format%3D%28string%29S16LE%2C+channels%3D%28int%291 HTTP/1.1"

what lib can se use to parse that url?

client.py is a program in the kaldi-gstreamer github (link: FIXME) that is used to test the server

when client.py connects, this is written by this program (or sublibrary) to stderr:
    192.168.1.211 - - [30/Jan/2023 10:42:33] "GET /client/ws/speech?content-type=audio%2Fx-raw%2C+layout%3D%28string%29interleaved%2C+rate%3D%28int%2916000%2C+format%3D%28string%29S16LE%2C+channels%3D%28int%291 HTTP/1.1" 101 46
when konele connects, this is written by this program (or sublibrary) to stderr:
    192.168.1.144 - - [30/Jan/2023 10:44:37] "GET /client/ws/speech?lang=und&user-agent=RecognizerIntentActivity%2F1.8.14%3B+Google%2Fbarbet%2Flineage_barbet-userdebug+13+TQ1A.230105.001.A2+48648b48b6%3B+null%2Fnull&calling-package=null&user-id=066be6e0-3e5e-4d58-b2e5-fabdd7b549d3&partial=true&content-type=audio%2Fx-raw%2C+layout%3D%28string%29interleaved%2C+rate%3D%28int%2916000%2C+format%3D%28string%29S16LE%2C+channels%3D%28int%291 HTTP/1.1" 101 46
    SO: konele is sending x-raw audio, interleaved, rate 16000, S16LE, channels 1
    with this rate, the audio will be 8000 samples/second (16 bits per sample)

the audio encoding is present in both, but only konele sends the "user-id" info which is presumably sent back by server on each communication?

WHO is writing that URL?

limitations:
    audio must be 8k samples/second, each sample 16 bits signed, so 16KB/s of data
    only one request at a time
    no incremental results yet
    no authentication on connection

"""

from wsocket import WSocketApp, WebSocketError, logger, run
import subprocess
import re

__author__ = "Rich Drewes"
__version__ = "1.0"
__license__ = "MIT"

audfn="audio.raw"           # file where incoming audio is dumped, for analysis by ggeranov whisper.cpp

transcmd="sox -t raw -r 16k -b 16 -c 1 -e signed audio.raw audio.wav rate 16000; /root/voicerec-whisper/whisper.cpp/main -m /root/voicerec-whisper/whisper.cpp/models/ggml-tiny.en.bin -t 4 -nt audio.wav 2> /dev/null"

logger.setLevel(10)  # for debugging

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
    with open(audfn, "wb") as audf:
        audf.close()

def on_message(message, client):
    #print(repr(client) + " : " + repr(message))
    # class 'bytearray' becomes class 'str' for EOS message, but this code was not working to detect that.
    # instead, just catch exception and call the audio transmission complete
    #print("RPD: type is", type(message))
    #if type(message)==type(str):
    #    if message=='EOS':
    #        print("RPD: got EOS! starting analysis")
    #else:
    try:
        with open(audfn, "ab") as audf:
            audf.write(message)
    except:
        # what if this takes so long the client gives up? should send incremental results,
        # or a least pretend results, while we process
        print("RPD: exception writing audio, probably done, final message is hopefully EOS:", repr(message))
        m=subprocess.check_output(transcmd, shell=True).decode("utf-8").strip()
        m=i=re.sub(r'\[.*\]', '', m)
        print("recognition result", m)
        # send json result to konele client:
        msg='{"status": 0, "segment": 0, "result": {"hypotheses": [{"transcript": "%s"}], "final": true}, "id": "1aacc69d-3674-438a-b3c5-fc0ed51769a5"}' % m
        print("msg is", msg)
        client.send(msg)
        client.close()

    try:
        # Here we could attempt to do partial recogntion and send a
        # partial recognition result back to client.
        # client.send("you said: " + message)
        # Do we need to send a status message back every time we get a message?
        # Probably not. And what is the deal with the id code? some kind of
        # session id presumably, konele seems to send one but
        # test client.py does not send one
        #client.send("""{"status": 0, "segment": 0, "result": {"hypotheses": [{"transcript": "one."}], "final": false}, "id": "1aacc69d-3674-438a-b3c5-fc0ed51769a5"}""")
        pass

    except WebSocketError:
        pass

app = WSocketApp()
app.onconnect += on_connect
app.onmessage += on_message
app.onclose += on_close

run(app, host="0.0.0.0", port=9001)
