# rixtribute - A wrapper around AWS to manage long running jobs
Orchestra distribution of long running jobs on AWS infrastructure


## How to
First create a _rxtb-config.yaml_ file

Setup the following sections: __provider__, __project__, __instance__

to start an instance: 

`rxtb start`

```
Specified instances:
    name       provider
--  ---------  ----------
 0  gpu-iptc   aws
 1  test-iptc  aws
Choose instance to start: 1
```

Then select 
