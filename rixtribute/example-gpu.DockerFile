FROM nvidia/cuda:11.2.1-base-ubuntu20.04
SHELL ["/bin/bash", "-c"]

#RUN mkdir /workdir
COPY requirements.txt /workdir/requirements.txt

RUN apt-get -y update && \
    apt-get -y install python3-pip && \
    rm -rf /var/lib/apt/lists/*

RUN pip3 install torch torchvision
RUN pip3 install -r /workdir/requirements.txt

RUN echo $'import torch \n\
print(torch.cuda.current_device()) \n\
print(torch.cuda.device(0)) \n\
print(torch.cuda.get_device_name(0)) \n\
'> /workdir/main.py


ENTRYPOINT ["python3","/workdir/main.py"]
