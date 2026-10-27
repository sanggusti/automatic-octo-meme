#!/bin/bash
# Boot one worker: headless Gazebo server + ArduCopter SITL (JSON link).
# SITL listens for MAVLink GCS on TCP 5760.
set -euo pipefail

export GZ_SIM_SYSTEM_PLUGIN_PATH=/home/pilot/ardupilot_gazebo/build:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}
export GZ_SIM_RESOURCE_PATH=/home/pilot/ardupilot_gazebo/models:/home/pilot/ardupilot_gazebo/worlds:${GZ_SIM_RESOURCE_PATH:-}
export PATH=/home/pilot/ardupilot/Tools/autotest:$PATH

cd /home/pilot/ardupilot_gazebo/worlds
if gz sim -s -r --headless-rendering iris_runway.sdf > /tmp/gz.log 2>&1 & then
  :
else
  gz sim -s -r iris_runway.sdf > /tmp/gz.log 2>&1 &
fi
echo "gazebo started, waiting for transport..."
sleep 20

cd /home/pilot/ardupilot/ArduCopter
exec sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --no-mavproxy -I0 --no-rebuild
