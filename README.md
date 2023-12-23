# whisper-websocket-server

This is a demonstration Python websockets program to run on your own server that will accept audio input from a client Android phone and transcribe it to text using whisper.cpp voice recognition, and return the text string results to the phone for insertion into text message or email or use as command or a web search.

An open source app on the client Android phones called Kõnele acts as the input service which sends the audio to this server. Kõnele acts as an Android input device, like a keyboard.

Basically, together the system acts like Google's voice input service or voice search, but you self host it so your data stays under your control. It works great for de-Googled open Android phones like LineageOS or Graphene. It seems to work better than Siri or Ok Google in recognition accuracy in my experience, though those services provide more than just voice recognition.

Though written as a simple test, this works so well that it has been part of my regular daily-driver phone usage for a year!

New features:
- Switched the default recogntion from whisper.cpp to faster-whisper for much improved performance. The new default model is "base.en" and both recogntion accuracy and speed are improved compared to whisper.cpp with "tiny.en"!
- Implemented completely in memory with no temporary file, so performance is better and multiple simultaneous recognitions are supported. No more using system() to shell to convert audio and invoke whisper.cpp, also improving speed and security.
- A Dockerfile is provided to help you set up your own docker image if you prefer to run it that way.

This program uses these other software systems:
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for audio to voice transcription, install to server with pip (see below)
- [Kõnele](https://f-droid.org/en/packages/ee.ioc.phon.android.speak/) client Android app; install to phone via f-droid repo is recommended
- [wsocket](https://github.com/ksenginew/WSocket) Python websocket library, install to server with pip (see below)

The setup is pretty simple, with a few things on the server side and a few on the client side (Android phone).

For instructions on using the older whisper.cpp implementation, refer to README-old.md in this repository.

---
## Demo video

Both recogntions here were done using the "tiny" model using whisper.cpp. The new preferred recognizer is faster-whisper instead of whisper.cpp, but the recognition results have only improved in accuracy and speed.


https://user-images.githubusercontent.com/10035429/219758618-c6c05a27-059d-427a-9e13-550fedbc281a.mp4


https://user-images.githubusercontent.com/10035429/219812393-9a4adbc6-09b3-41ec-aa3a-dfb84b60730e.mp4

---
## Server side setup (Python websocket server using faster-whisper library)

On your server machine where the voice recognition will be performed, install faster-whisper with pip as explained as they direct. Link above.

Your server should have a well-known IP address. You could probably also use dynamic DNS of some sort, instead of a fixed IP address.

Install faster-whisper library. Use a venv if you like:
````
    pip install faster-whisper
````

Install wsocket library. Use a venv if you like:
````
    pip install wsocket
````

Install "minimal-fw-mem.py" from this repo into your working directory and edit the host and port in the run(). The "host" should be the IP address of the interface on the local machine that the program should listen for service requests. This might be "localhost", or possibly "0.0.0.0" to listen on all interfaces on the server. The "port" can be most anything but must agree with whatever you set up on the client side (below). I used port 9002. The recognition result from faster-whisper is sent back over the websocket to Kõnele on the phone side for insertion into the text message, email, or command.

Start the server running from the command line and be ready to watch output:
````
    python3 minimal-fw-mem.py
````

Eventually you will set this up to start automatically, like in /etc/rc.local or using systemd or whatever. I like to set it up to start in a "screen" session so it will persist after logout but you can also reconnect and view the output. You can also run the server in a Docker if you prefer (see below).

---
## Client side setup (Android phone using Kõnele app for input)

Install Kõnele app (also known as K6nele) from f-droid repo onto your Android phone. I use Lineageos as my Android platform but most any Android should work. Google Play services is not required.

Configure Kõnele as follows. Under "Kõnele settings"->"Recognition services"->"Kõnele (fast recognition)" where it says "Service based on the Kaldi GStreamer server..." set the URL to point to your server address and port (set up above), for example:
````
    ws://YOURSERVERHOSTNAMEORIPADDRESS:9002/client/ws/speech
````

The port number in that ws:// URL must agree with the port that you set the server to run, above.

I also use the "Anysoft Keyboard" app from f-droid as my basic input mechanism on my Android phone. I think things will work with the regular Android input keyboard system, but if you have problems, install the Anysoft Keyboard and try again.

---
## Usage

In order to get the microphone on the virtual keyboard to invoke Kõnele (and send audio to the server for transcription) you will probably have to invoke the Kõnele app first on its own once, after you boot your phone. After that it should happen automatically when you invoke your normal input system, until you reboot your phone.

When you click on the microphone input on your Android phone's virtual keyboard, you should see the server side "minimal-fw-mem.py" print a message acknowledging the connection. As you speak, the audio data should be captured in memory on the server side. When you click to stop input on the phone, you should see a message on the server side indicating that the audio is complete, and faster-whisper will be invoked on the audio data. Then a message should be sent back to the phone with the text of the transcription. The resulting text can be inserted into a text message or email as you wish.

If you click on the Kõnele app itself (instead of the microphone on the Android keyboard) it will do a web search with the recognized text instead.

---
## Docker

If you wish, you can easily run this system using Docker, which gives some improved security isolation (but remember, the audio traffic and recognition results are NOT encrypted on the network!)

To do this, from the directory that contains the Dockerfile and minimal-fw-mem.py from the repository, create a docker image called "fwmem":

````
    docker build -t fwmem .
````

This will take some time to build the image based on Ubuntu Linux base image containing faster-whisper, websockets library, and all their dependencies, according to the specification in Dockerfile.

You can then run this docker image as follows:

````
    docker run -p 9002:9002 fwmem
````

That will start the docker image you just created and map the system port 9002 to the server running on port 9002 inside the docker.

---
## Limitations and cautions

There is minimal security in this implementation. The audio data and recognition results are sent in the clear across the network from your phone to the server and back. If you leave the server running on an open port on your server, other people may be able to connect to it and use your server to perform voice recogntion (or possibly do something worse, if there is a way to exploit the server). I run this over a tinc VPN, but if you expose the server IP to the world there are security implications. That is your problem.

The audio format in the transmission to the server is Kõnele's default raw and uncompressed audio. Kõnele supports multiple audio formats, but if you change the format on the client side in Kõnele, you will probably also need to change the minimal-fw-mem.py on the server side. The encoding format could be determined dynamically by the url on the server, but this is not currently done.

---
## Alternatives

If you want to try to run a local (on-phone, offline with no network connection) then I recommend that you look at this:

- [WhisperInput](https://github.com/alex-vt/WhisperInput)

I compiled it and tried it out and it works great. For my setup (Pixel 5a with fast network and fast server) it is on average significantly slower returning recognitions since it is running on-phone compared to running on a fast server, but it still runs very well! Give it a try. For short recognitions, it could be faster to run on-phone, especially if your server is not fast.

Another server based approach uses the Kaldi voice recognizer instead of Whisper:

- [Kaldi-Gstreamer-server](https://github.com/alumae/kaldi-gstreamer-server)

I ran this Kaldi server for years and accessed it from my open Android phone using Kõnele as the frontend (just as I describe above for this project). It worked pretty well. I find Whisper to be a much superior voice recognition system though. I think maybe Kaldi works better in other languages than it does in English, but I doubt it compares in recognition accuracy to Whisper these days.

---
## Feedback

These instructions are being improved quickly now. If you encounter problems, send a question and these instructions will be improved.
