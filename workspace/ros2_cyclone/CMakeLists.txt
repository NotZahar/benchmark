cmake_minimum_required(VERSION 3.28)

project("ros2_cyclone")
set(ROS2_NODE_PUBLISHER "${PROJECT_NAME}_publisher")
set(ROS2_NODE_SUBSCRIBER "${PROJECT_NAME}_subscriber")
set(ROS2_CUSTOM_MSGS "${PROJECT_NAME}__rosidl_typesupport_cpp")

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(std_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(yaml-cpp REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME} "msg/Payload.msg" DEPENDENCIES
                           builtin_interfaces)

add_executable(${ROS2_NODE_PUBLISHER})
target_sources(${ROS2_NODE_PUBLISHER} PRIVATE src/publisher.cc)

add_executable(${ROS2_NODE_SUBSCRIBER})
target_sources(${ROS2_NODE_SUBSCRIBER} PRIVATE src/subscriber.cc)

target_include_directories(
  ${ROS2_NODE_PUBLISHER}
  PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
         $<INSTALL_INTERFACE:include>)
target_include_directories(
  ${ROS2_NODE_SUBSCRIBER}
  PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
         $<INSTALL_INTERFACE:include>)

ament_target_dependencies(${ROS2_NODE_PUBLISHER} rclcpp std_msgs)
ament_target_dependencies(${ROS2_NODE_SUBSCRIBER} rclcpp std_msgs)

rosidl_get_typesupport_target(${ROS2_CUSTOM_MSGS} ${PROJECT_NAME}
                              "rosidl_typesupport_cpp")

set(EXTRA_COMPILER_FLAGS -Wall -Wextra -Wconversion -Wshadow -Wpedantic -Werror)
target_compile_options(${ROS2_NODE_PUBLISHER} PRIVATE ${EXTRA_COMPILER_FLAGS})
target_compile_options(${ROS2_NODE_SUBSCRIBER} PRIVATE ${EXTRA_COMPILER_FLAGS})

target_link_libraries(${ROS2_NODE_PUBLISHER} ${ROS2_CUSTOM_MSGS} yaml-cpp)
target_link_libraries(${ROS2_NODE_SUBSCRIBER} ${ROS2_CUSTOM_MSGS} yaml-cpp)

install(TARGETS ${ROS2_NODE_PUBLISHER} ${ROS2_NODE_SUBSCRIBER}
        DESTINATION lib/${PROJECT_NAME})

ament_package()
