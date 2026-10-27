# Track 1 sim image: Ubuntu 22.04 + Gazebo Harmonic + ArduPilot SITL + plugin.
# Pins: ArduCopter Copter-4.6.3, ardupilot_gazebo 80dc9664.
# One container = one worker (single SITL + Gazebo pair); the bridge spawns
# one container per episode for full isolation.
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git gnupg lsb-release sudo \
    python3 python3-pip \
  && rm -rf /var/lib/apt/lists/*

# Gazebo Harmonic (binary install) + plugin build deps (OSRF repo first)
RUN curl -fsSL https://packages.osrfoundation.org/gazebo.gpg \
      -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
      > /etc/apt/sources.list.d/gazebo-stable.list \
  && apt-get update && apt-get install -y --no-install-recommends \
    gz-harmonic \
    libgz-sim8-dev rapidjson-dev \
    libopencv-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl \
    mesa-utils libgl1-mesa-dri libegl1 \
  && rm -rf /var/lib/apt/lists/*

# Non-root build user (ArduPilot prereq script refuses root)
RUN useradd -m -s /bin/bash pilot \
  && echo "pilot ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
USER pilot
ENV USER=pilot LOGNAME=pilot
WORKDIR /home/pilot

# ArduPilot, pinned to Copter-4.6.3 (SITL build for ArduCopter only)
ARG ARDUPILOT_REF=Copter-4.6.3
RUN git clone --branch ${ARDUPILOT_REF} --depth 1 \
      https://github.com/ArduPilot/ardupilot.git /home/pilot/ardupilot \
  && cd /home/pilot/ardupilot \
  && git submodule update --init --recursive --depth 1 \
  && Tools/environment_install/install-prereqs-ubuntu.sh -y \
  && . ~/.profile \
  && ./waf configure --board sitl \
  && ./waf copter -j$(nproc)

# ArduPilot Gazebo plugin, pinned
ARG PLUGIN_REF=80dc9664dda7efd6c5d1a71a79198d1d6b708c0e
RUN git clone https://github.com/ArduPilot/ardupilot_gazebo.git /home/pilot/ardupilot_gazebo \
  && cd /home/pilot/ardupilot_gazebo \
  && git checkout ${PLUGIN_REF} \
  && mkdir build && cd build \
  && cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  && make -j$(nproc)

ENV GZ_SIM_SYSTEM_PLUGIN_PATH=/home/pilot/ardupilot_gazebo/build
ENV GZ_SIM_RESOURCE_PATH=/home/pilot/ardupilot_gazebo/models:/home/pilot/ardupilot_gazebo/worlds
ENV PATH=/home/pilot/ardupilot/Tools/autotest:$PATH

COPY --chown=pilot:pilot entrypoint.sh /home/pilot/entrypoint.sh
RUN chmod +x /home/pilot/entrypoint.sh

EXPOSE 5760
CMD ["/home/pilot/entrypoint.sh"]
