FROM python:3.8

RUN apt-get update
RUN apt-get install unzip

COPY ./docker/sim3d /sim3d_archive
SHELL ["/bin/bash", "-c"]
RUN if unzip /sim3d_archive -d sim3d; then \
     echo "unzipped 3d sim"; \
   elif [[ -f "/sim3d_archive/ZilantSimulator3d.x86_64" ]]; then \
     mv /sim3d_archive /sim3d && \
     echo "folder provided"; \
   else \
     echo "provided sim path is neither a folder nor a zipfile" && \
     exit 12; \
   fi

WORKDIR /app

COPY ./src ./
COPY ./simulator3d ./
COPY ./sim.py ./
COPY ./config_options.py ./
COPY ./requirements.txt ./
RUN python3 -m pip install -r requirements.txt

CMD python3

