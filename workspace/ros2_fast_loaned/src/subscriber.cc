#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <utility>

#include <rcl/subscription.h>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp/wait_set.hpp>

#include "ros2_fast_loaned/constants.hh"
#include "ros2_fast_loaned/msg/payload1024.hpp"
#include "ros2_fast_loaned/msg/payload1048576.hpp"
#include "ros2_fast_loaned/msg/payload16384.hpp"
#include "ros2_fast_loaned/msg/payload256.hpp"
#include "ros2_fast_loaned/msg/payload262144.hpp"
#include "ros2_fast_loaned/msg/payload4096.hpp"
#include "ros2_fast_loaned/msg/payload4194304.hpp"
#include "ros2_fast_loaned/msg/payload65536.hpp"
#include "ros2_fast_loaned/utils.hh"

namespace tb {

template <typename MessageT>
class Subscriber final : public rclcpp::Node {
 public:
  Subscriber() = delete;
  Subscriber(utils::Config config, int instance_id)
      : Node{std::string{constants::SUBSCRIBER_NODE_NAME} + "_" +
             std::to_string(instance_id)},
        config_{config},
        instance_id_{instance_id} {
    latencies_.reserve(config_.number_of_samples);
    subscriber_ = create_subscription<MessageT>(
        constants::BENCHMARK_TOPIC, constants::BENCHMARK_QOS,
        [this](typename MessageT::ConstSharedPtr message) {
          (void)message;
          std::cerr << "unexpected rclcpp callback on loaned subscriber"
                    << std::endl;
          std::abort();
        });
    if (!subscriber_->can_loan_messages()) {
      throw std::runtime_error(
          "rmw_fastrtps did not enable loaned subscription messages");
    }
  }

  ~Subscriber() {
    const auto result_folder =
        utils::latencyResultsPath(constants::RESULTS_FILE_PATH) + "/" +
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

  void run() {
    rclcpp::WaitSet wait_set;
    wait_set.add_subscription(subscriber_);

    while (rclcpp::ok() && latencies_.size() < config_.number_of_samples) {
      const auto wait_result = wait_set.wait(std::chrono::seconds(5));
      if (wait_result.kind() == rclcpp::WaitResultKind::Timeout) {
        continue;
      }
      if (wait_result.kind() != rclcpp::WaitResultKind::Ready) {
        std::cerr << "loaned subscriber wait set is not ready" << std::endl;
        std::abort();
      }

      void* loaned_message = nullptr;
      rmw_message_info_t message_info{};
      const auto take_result = rcl_take_loaned_message(
          subscriber_->get_subscription_handle().get(), &loaned_message,
          &message_info, nullptr);
      if (take_result != RCL_RET_OK || loaned_message == nullptr) {
        std::cerr << "failed to take loaned message: " << take_result
                  << std::endl;
        std::abort();
      }

      const auto received_at_ns = utils::nowNs();
      tack(*static_cast<const MessageT*>(loaned_message), received_at_ns);

      const auto return_result = rcl_return_loaned_message_from_subscription(
          subscriber_->get_subscription_handle().get(), loaned_message);
      if (return_result != RCL_RET_OK) {
        std::cerr << "failed to return loaned message: " << return_result
                  << std::endl;
        std::abort();
      }
    }
  }

 private:
  void tack(const MessageT& message,
            const std::int64_t received_at_ns) noexcept {
    latencies_.push_back(received_at_ns - message.time_stamp_ns);
  }

  const utils::Config config_;
  int instance_id_;
  std::vector<std::int64_t> latencies_;
  typename rclcpp::Subscription<MessageT>::SharedPtr subscriber_;
};

template <typename MessageT>
int runSubscriber(int argc, char** argv, const utils::Config& config,
                  int instance_id) {
  rclcpp::init(argc, argv);
  auto subscriber = std::make_shared<Subscriber<MessageT>>(config, instance_id);
  subscriber->run();
  rclcpp::shutdown();

  return constants::SUCCESS_APP_FINISH;
}

int dispatch(int argc, char** argv, const utils::Config& config,
             int instance_id) {
  switch (config.payload_size_bytes) {
    case 256:
      return runSubscriber<ros2_fast_loaned::msg::Payload256>(
          argc, argv, config, instance_id);
    case 1024:
      return runSubscriber<ros2_fast_loaned::msg::Payload1024>(
          argc, argv, config, instance_id);
    case 4096:
      return runSubscriber<ros2_fast_loaned::msg::Payload4096>(
          argc, argv, config, instance_id);
    case 16384:
      return runSubscriber<ros2_fast_loaned::msg::Payload16384>(
          argc, argv, config, instance_id);
    case 65536:
      return runSubscriber<ros2_fast_loaned::msg::Payload65536>(
          argc, argv, config, instance_id);
    case 262144:
      return runSubscriber<ros2_fast_loaned::msg::Payload262144>(
          argc, argv, config, instance_id);
    case 1048576:
      return runSubscriber<ros2_fast_loaned::msg::Payload1048576>(
          argc, argv, config, instance_id);
    case 4194304:
      return runSubscriber<ros2_fast_loaned::msg::Payload4194304>(
          argc, argv, config, instance_id);
    default:
      std::cerr << "Unsupported loaned payload size: "
                << config.payload_size_bytes << std::endl;
      return constants::FAILED_APP_FINISH;
  }
}

}  // namespace tb

int main(int argc, char** argv) {
  if (argc != 3) {
    std::cerr << __FUNCTION__ << ": " << __LINE__ << std::endl;
    return tb::constants::FAILED_APP_FINISH;
  }

  return tb::dispatch(argc, argv, tb::utils::parseConfig(argv[1]),
                      std::stoi(argv[2]));
}
