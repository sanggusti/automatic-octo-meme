# Pinned Track 1 sim image: Ubuntu 22.04 + Gazebo + ArduPilot SITL.
# Follows the official ardupilot_gazebo plugin install steps; the plugin
# needs no ROS. ArduPilot source + waf SITL build happen here so eval
# workers only run binaries. Allow a long first build.
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git gnupg lsb-release sudo \
    python3 python3-pip \
    libgz-sim8-dev rapidjson-dev \
    libopencv-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl \
  && rm -rf /var/lib/apt/lists/*

# Gazebo Harmonic (binary install)
RUN curl -fsSL https://packages.osrfoundation.org/gazebo.gpg \
      -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
      > /etc/apt/sources.list.d/gazebo-stable.list \
  && apt-get update && apt-get install -y --no-install-recommends gz-harmonic \
  && rm -rf /var/lib/apt/lists/*

# ArduPilot SITL build (pinned commit set in the sim-spike issue).
# TODO(sim-spike): pin ARDUPILOT_REF, run Tools/environment_install, waf configure --board sitl, waf copter.
# TODO(sim-spike): clone ArduPilot/ardupilot_gazebo, build plugin, install worlds/models.

WORKDIR /opt/dmb
CMD ["gz", "sim", "-v4", "-r", "shapes.sdf"]
