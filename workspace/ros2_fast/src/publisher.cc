#include <chrono>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <rclcpp/node.hpp>
#include <rclcpp/rclcpp.hpp>

#include "ros2_fast/constants.hh"
#include "ros2_fast/msg/payload.hpp"
#include "ros2_fast/utils.hh"

namespace tb {

class Publisher final : public rclcpp::Node {
 public:
  Publisher() = delete;
  explicit Publisher(utils::Config config) noexcept
      : Node{constants::PUBLISHER_NODE_NAME},
        config_{config},
        message_number_{0} {
    publisher_ = create_publisher<ros2_fast::msg::Payload>(
        constants::BENCHMARK_TOPIC, constants::BENCHMARK_QOS);
    timer_ =
        create_wall_timer(std::chrono::milliseconds(config_.publish_period_ms),
                          [this]() { tick(); });
  }

  ~Publisher() override = default;

 private:
  void tick() noexcept {
    const auto timestamp = now();
    ros2_fast::msg::Payload message;
    message.data.resize(config_.payload_size_bytes,
                        constants::PAYLOAD_DATA_CHUNK);
    message.message_number = message_number_++;
    message.time_stamp = timestamp;

    publisher_->publish(std::move(message));
  }

  const utils::Config config_;
  std::uint32_t message_number_;
  rclcpp::Publisher<ros2_fast::msg::Payload>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
};

}  // namespace tb

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << __FUNCTION__ << ": " << __LINE__ << std::endl;
    std::abort();

    return tb::constants::FAILED_APP_FINISH;
  }

  rclcpp::init(argc, argv);
  rclcpp::spin(
      std::make_shared<tb::Publisher>(tb::utils::parseConfig(argv[1])));
  rclcpp::shutdown();

  return tb::constants::SUCCESS_APP_FINISH;
}
