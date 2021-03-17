# rixtribute - A wrapper around AWS to manage long running jobs
Orchestra distribution of long running jobs on AWS infrastructure

## First objective
  1. Run long running process on EC2
  2. run command on server and recieve output locally
  3. Set into production: 
    1. run periodically
    2. run permanently (server)


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

# TODO:
[x] Create security group
[x] Create key-pair
  [x] add key to rxtb-profile
  [x] add user name prefix to key name to avoid duplicates on multi person work setup
[x] Test tmux command for long running commands
[x] Run command remotely inside docker container
  [ ] Test if --gpus=all works on gpu instance
[ ] Somehow save output
[ ] Test if tensorboard can be run from commands

[ ] Start/stop instance for improved startup times
[ ] Start normal instance (non-spot)
## Config parsing
[ ] parse project like provider, instance and container
[ ] if no rxtb file in current dir traverse until .git dir

