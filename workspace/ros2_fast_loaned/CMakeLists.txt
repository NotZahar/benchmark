cmake_minimum_required(VERSION 3.28)

project("ros2_fast_loaned")
set(ROS2_NODE_PUBLISHER "${PROJECT_NAME}_publisher")
set(ROS2_NODE_SUBSCRIBER "${PROJECT_NAME}_subscriber")
set(ROS2_CUSTOM_MSGS "${PROJECT_NAME}__rosidl_typesupport_cpp")
include("${CMAKE_CURRENT_SOURCE_DIR}/../cmake/CompilerWarnings.cmake")

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(yaml-cpp REQUIRED)

rosidl_generate_interfaces(
  ${PROJECT_NAME}
  "msg/Payload256.msg"
  "msg/Payload1024.msg"
  "msg/Payload4096.msg"
  "msg/Payload16384.msg"
  "msg/Payload65536.msg"
  "msg/Payload262144.msg"
  "msg/Payload1048576.msg"
  "msg/Payload4194304.msg")

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

rosidl_get_typesupport_target(${ROS2_CUSTOM_MSGS} ${PROJECT_NAME}
                              "rosidl_typesupport_cpp")

target_enable_benchmark_warnings(${ROS2_NODE_PUBLISHER})
target_enable_benchmark_warnings(${ROS2_NODE_SUBSCRIBER})

target_link_libraries(${ROS2_NODE_PUBLISHER} rclcpp::rclcpp ${ROS2_CUSTOM_MSGS}
                      yaml-cpp)
target_link_libraries(${ROS2_NODE_SUBSCRIBER} rclcpp::rclcpp ${ROS2_CUSTOM_MSGS}
                      yaml-cpp)

install(TARGETS ${ROS2_NODE_PUBLISHER} ${ROS2_NODE_SUBSCRIBER}
        DESTINATION lib/${PROJECT_NAME})

ament_package()
