#!/bin/bash
# Boot one worker: headless Gazebo server + ArduCopter SITL (JSON link).
# SITL listens for MAVLink GCS on TCP 5760.
set -euo pipefail

export GZ_SIM_SYSTEM_PLUGIN_PATH=/home/pilot/ardupilot_gazebo/build:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}
export GZ_SIM_RESOURCE_PATH=/home/pilot/ardupilot_gazebo/models:/home/pilot/ardupilot_gazebo/worlds:${GZ_SIM_RESOURCE_PATH:-}
export PATH=/home/pilot/ardupilot/Tools/autotest:$PATH

cd /home/pilot/ardupilot_gazebo/worlds
# T2 capture (#16): DMB_GZ_RECORD_PATH (host-mounted /record) enables
# gz state logging for --playback. Recording must never kill the worker:
# if the dir cannot be prepared, fall back to no-record, loudly.
# NOTE: gz appends "(1)" to an EXISTING record path (landing outside the
# mount and failing as non-root), so always record into a fresh leaf dir.
RECORD_ARGS=()
if [ -n "${DMB_GZ_RECORD_PATH:-}" ]; then
  if sudo mkdir -p "$DMB_GZ_RECORD_PATH" && sudo chmod 777 "$DMB_GZ_RECORD_PATH" \
      && touch "$DMB_GZ_RECORD_PATH/.writetest" 2>/dev/null; then
    rm -f "$DMB_GZ_RECORD_PATH/.writetest"
    RECORD_ARGS=(--record-path "$DMB_GZ_RECORD_PATH/gzlog")
    echo "gz recording to $DMB_GZ_RECORD_PATH/gzlog"
  else
    echo "WARNING: cannot write $DMB_GZ_RECORD_PATH; recording disabled" >&2
  fi
fi
if gz sim -s -r --headless-rendering "${RECORD_ARGS[@]}" iris_runway.sdf > /tmp/gz.log 2>&1 & then
  :
else
  gz sim -s -r "${RECORD_ARGS[@]}" iris_runway.sdf > /tmp/gz.log 2>&1 &
fi
echo "gazebo started, waiting for transport..."
sleep 20

cd /home/pilot/ardupilot/ArduCopter
exec sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --no-mavproxy -I0 --no-rebuild
