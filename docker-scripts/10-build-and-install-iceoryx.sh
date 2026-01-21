#!/bin/bash

set -eo pipefail

echo "Building Iceoryx ..."
mkdir -p ~/iceoryx_ws/src
cd ~/iceoryx_ws
source /opt/ros/jazzy/setup.bash
rosdep init || true
rosdep update

vcs import src/ <<EOF
repositories:
  rmw_iceoryx:
    type: git
    url: https://github.com/ros2/rmw_iceoryx.git
    version: jazzy
  rcl_interfaces:
    type: git
    url: https://github.com/ros2/rcl_interfaces.git
    version: jazzy
  test_interface_files:
    type: git
    url: https://github.com/ros2/test_interface_files.git
    version: jazzy
EOF

find src/ -name "package.xml" | head -10
colcon list --names-only
if ! rosdep install --from-paths src --ignore-src -y --rosdistro jazzy 2>&1 | grep -q "Failed to install"; then
	echo "rosdep finished successfully."
else
	echo "rosdep encountered errors but continuing."
fi
colcon build --packages-select test_interface_files --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release --allow-overriding builtin_interfaces
source install/setup.bash
colcon build --packages-select test_msgs --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release --allow-overriding builtin_interfaces
source install/setup.bash
colcon build --packages-up-to rmw_iceoryx_cpp --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
echo "source ~/iceoryx_ws/install/setup.bash" >>~/.bashrc

ldconfig
