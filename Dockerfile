FROM ubuntu:latest

# RUNs are done when building image
# CMD is done when image is invoked. there is only one CMD

RUN useradd -rm -d /home/fwuser -s /bin/bash -g root -G sudo -u 1000 fwuser
COPY minimal-fw-mem.py /home/fwuser

RUN apt update
RUN apt install -y python3-pip
RUN pip install faster-whisper
RUN pip install wsocket
USER fwuser

# this will run when docker image is created, to force download of model data from openai
# so that model data will be included in the image for later use rather than downloading
# that data each time the docker is run:
RUN python3 /home/fwuser/minimal-fw-mem.py onlymodel

# this will run when the docker image is run:
CMD python3 /home/fwuser/minimal-fw-mem.py
