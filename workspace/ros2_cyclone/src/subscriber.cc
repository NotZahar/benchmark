#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
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
  Subscriber(utils::Config config, int instance_id) noexcept
      : Node{std::string{constants::SUBSCRIBER_NODE_NAME} + "_" +
             std::to_string(instance_id)},
        config_{config}, instance_id_{instance_id} {
    latencies_.reserve(config_.number_of_samples);
    subscriber_ = create_subscription<ros2_cyclone::msg::Payload>(
        constants::BENCHMARK_TOPIC, constants::BENCHMARK_QOS,
        [this](ros2_cyclone::msg::Payload::ConstSharedPtr message) {
          tack(std::move(message));
        });
  }

  ~Subscriber() {
    const auto result_folder =
        std::string{constants::RESULTS_FILE_PATH} + "/" +
        std::to_string(config_.payload_size_bytes) + "_bytes_" +
        std::to_string(config_.publish_period_ms) + "_ms_" +
        std::to_string(config_.number_of_samples) + "_samples";
    std::filesystem::create_directories(result_folder);

    const auto result_file =
        result_folder + "/" + std::to_string(instance_id_) + "_subscriber.txt";

    std::ofstream out{result_file};
    out << makeBenchmarkResult(config_, std::move(latencies_));
    out.close();
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
  int instance_id_;
  std::vector<std::int64_t> latencies_;
  rclcpp::Subscription<ros2_cyclone::msg::Payload>::SharedPtr subscriber_;
};

} // namespace tb

int main(int argc, char **argv) {
  if (argc != 3) { // NOTE: First is config, second is instance id
    std::cerr << __FUNCTION__ << ": " << __LINE__ << std::endl;
    std::abort();

    return tb::constants::FAILED_APP_FINISH;
  }

  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<tb::Subscriber>(tb::utils::parseConfig(argv[1]),
                                                std::stoi(argv[2])));
  rclcpp::shutdown();

  return tb::constants::SUCCESS_APP_FINISH;
}
