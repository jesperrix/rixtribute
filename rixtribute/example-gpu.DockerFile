FROM nvidia/cuda:10.2-runtime-ubuntu18.04
SHELL ["/bin/bash", "-c"]

RUN mkdir /workdir
RUN apt-get -y update
RUN apt-get -y install python3-pip

COPY requirements.txt /workdir/requirements.txt
RUN pip3 install torch torchvision
RUN pip3 install -r /workdir/requirements.txt

RUN echo $'import torch \n\
print(torch.cuda.current_device()) \n\
print(torch.cuda.device(0)) \n\
print(torch.cuda.get_device_name(0)) \n\
'> /workdir/main.py


ENTRYPOINT ["python3","/workdir/main.py"]
