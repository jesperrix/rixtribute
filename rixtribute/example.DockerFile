FROM pytorch/pytorch:1.6.0-cuda10.1-cudnn7-runtime


COPY requirements.txt /workdir/requirements.txt
RUN pip install -r /workdir/requirements.txt

RUN echo 'print("hello, world!")' > /workdir/main.py
