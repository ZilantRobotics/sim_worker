# Simulator Runner
This is a worker backend application for HITL simulator project.
It accepts commands (opcodes) either through WSS, which is an intended
way to communicate with the worker or through CLI, this mode can be 
used for local testing.

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