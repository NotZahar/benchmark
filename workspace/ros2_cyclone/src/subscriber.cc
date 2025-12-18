#include <cstdlib>
#include <cstring>
#include <iostream>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/byte_multi_array.hpp>

#include "ros2_cyclone/constants.hh"
#include "ros2_cyclone/msg/payload.hpp"
#include "ros2_cyclone/utils.hh"

namespace tb {

class Subscriber final : public rclcpp::Node {
public:
  Subscriber() = delete;
  explicit Subscriber(utils::Config config) noexcept
      : Node{constants::SUBSCRIBER_NODE_NAME}, config_{config} {
    latencies_.reserve(config_.number_of_samples);
    subscriber_ = create_subscription<ros2_cyclone::msg::Payload>(
        constants::BENCHMARK_TOPIC, constants::BENCHMARK_QOS,
        [this](ros2_cyclone::msg::Payload::ConstSharedPtr message) {
          tack(std::move(message));
        });
  }

  ~Subscriber() {
    std::cerr << utils::makeBenchmarkResult(config_, std::move(latencies_));
  }

private:
  void tack(ros2_cyclone::msg::Payload::ConstSharedPtr message) noexcept {
    if (message->data.empty() ||
        message->data[0] != constants::PAYLOAD_DATA_CHUNK) {
      std::cerr << __FUNCTION__ << ": " << __LINE__ << std::endl;
      std::abort();
    }

    latencies_.push_back((now() - message->time_stamp).nanoseconds());
    if (latencies_.size() == config_.number_of_samples)
      rclcpp::shutdown();
  }

  const utils::Config config_;
  std::vector<std::int64_t> latencies_;
  rclcpp::Subscription<ros2_cyclone::msg::Payload>::SharedPtr subscriber_;
};

} // namespace tb

int main(int argc, char **argv) {
  if (argc != 2) {
    std::cerr << __FUNCTION__ << ": " << __LINE__ << std::endl;
    std::abort();

    return tb::constants::FAILED_APP_FINISH;
  }

  rclcpp::init(argc, argv);
  rclcpp::spin(
      std::make_shared<tb::Subscriber>(tb::utils::parseConfig(argv[1])));
  rclcpp::shutdown();

  return tb::constants::SUCCESS_APP_FINISH;
}
