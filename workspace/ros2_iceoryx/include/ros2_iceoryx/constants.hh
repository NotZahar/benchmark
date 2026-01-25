#pragma once

#include <rclcpp/qos.hpp>

namespace tb::constants {

inline constexpr auto PUBLISHER_NODE_NAME = "tb_publisher";
inline constexpr auto SUBSCRIBER_NODE_NAME = "tb_subscriber";
inline constexpr auto BENCHMARK_TOPIC = "/tb_benchmark_topic";
inline const auto BENCHMARK_QOS = rclcpp::QoS{10};
inline constexpr auto PAYLOAD_DATA_CHUNK = 0xFF;
inline constexpr auto RESULTS_FILE_PATH =
    "/root/workspace/tmp/ros2_iceoryx/latencies";

inline constexpr auto SUCCESS_APP_FINISH = 0;
inline constexpr auto FAILED_APP_FINISH = 0;

}  // namespace tb::constants
