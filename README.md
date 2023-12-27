# Simulator Worker

## Purpose
This is a worker backend application for HITL simulator project.

Worker accepts commands (aka opcodes) through WSS or CLI, and executes them on the local environment - usually,
that will be a HITL simulator with PX4 autopilot attached to it, and a 3D simulator.

It supports starting, stopping, configuring the autopilot and launching user missions.
The intended usage is to work with the [server](https://github.com/ZilantRobotics/sim_server) and provide users with 
a convenient web-based GUI to test their code against the real hardware. CLI mode is supported for power users and quick tests.
## Setup
* Clone this repo `git clone https://github.com/Jlo6CTEP/sim_runner --recursive`
* Clone HITL sim repo `git clone https://github.com/RaccoonlabDev/innopolis_vtol_dynamics.git --recursive`
  * If you are pulling that repo, don't forget to update submodules
* Download a binary release of 3D simulator `https://github.com/ZilantRobotics/simulator3d` 
  * Unzip to 3dsim folder
* Assuming you did the above steps in the same directory, there should be no need
to update paths in the `./sim_runner/sample_config/settings.ini` file
* If it complains that it can't find something, go to the aforementioned file and fix paths.
This app can also read configuration from .env file and environment variables, chain of priority is
environment variables -> CLI arguments -> settings.ini -> .env file from the highest to the lowest

## Architecture
![architecture.svg](assets%2Farchitecture.svg)
This program can be launched in two main modes - WSS and CLI
* CLI mode is intended for testing and debugging, user can either launch a one-off 
run and supply commands (opcodes) via the command line, for the list of possible options please
refer to `./config/opcode_file.json`, or connect to an existing Worker via WSS
* WSS mode is intended for production use, application connects to a Simulator Server backend
and receives commands from there. Users can interact with the Worker indirectly via
the GUI web application

To run in WSS mode, start the app with `python3 sim.py wss`, this will use default
configuration options from `./config/settings.ini` and `./config/.env` files

## System requirements
Python: 3.9
OS: Ubuntu 22.04, known to not work on WSL, RPi4 (8Gb ram) and Jetson Xavier NX
CPU: AMD FX 8300 or better
GPU: AMD Radeon HD5800 or better
