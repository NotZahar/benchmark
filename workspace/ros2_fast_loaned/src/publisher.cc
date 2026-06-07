#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <utility>

#include <rclcpp/node.hpp>
#include <rclcpp/rclcpp.hpp>

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
class Publisher final : public rclcpp::Node {
 public:
  Publisher() = delete;
  explicit Publisher(utils::Config config)
      : Node{constants::PUBLISHER_NODE_NAME},
        config_{config},
        message_number_{0} {
    publisher_ = create_publisher<MessageT>(constants::BENCHMARK_TOPIC,
                                            constants::BENCHMARK_QOS);
    if (!publisher_->can_loan_messages()) {
      throw std::runtime_error("rmw_fastrtps did not enable loaned messages");
    }
    timer_ =
        create_wall_timer(std::chrono::milliseconds(config_.publish_period_ms),
                          [this]() { tick(); });
  }

  ~Publisher() override = default;

 private:
  void tick() {
    const auto timestamp_ns = utils::nowNs();
    auto loaned_message = publisher_->borrow_loaned_message();
    auto& message = loaned_message.get();
    message.data.fill(constants::PAYLOAD_DATA_CHUNK);
    message.message_number = message_number_++;
    message.time_stamp_ns = timestamp_ns;

    publisher_->publish(std::move(loaned_message));
  }

  const utils::Config config_;
  std::uint32_t message_number_;
  typename rclcpp::Publisher<MessageT>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
};

template <typename MessageT>
int runPublisher(int argc, char** argv, const utils::Config& config) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<Publisher<MessageT>>(config));
  rclcpp::shutdown();

  return constants::SUCCESS_APP_FINISH;
}

int dispatch(int argc, char** argv, const utils::Config& config) {
  switch (config.payload_size_bytes) {
    case 256:
      return runPublisher<ros2_fast_loaned::msg::Payload256>(argc, argv,
                                                             config);
    case 1024:
      return runPublisher<ros2_fast_loaned::msg::Payload1024>(argc, argv,
                                                              config);
    case 4096:
      return runPublisher<ros2_fast_loaned::msg::Payload4096>(argc, argv,
                                                              config);
    case 16384:
      return runPublisher<ros2_fast_loaned::msg::Payload16384>(argc, argv,
                                                               config);
    case 65536:
      return runPublisher<ros2_fast_loaned::msg::Payload65536>(argc, argv,
                                                               config);
    case 262144:
      return runPublisher<ros2_fast_loaned::msg::Payload262144>(argc, argv,
                                                                config);
    case 1048576:
      return runPublisher<ros2_fast_loaned::msg::Payload1048576>(argc, argv,
                                                                 config);
    case 4194304:
      return runPublisher<ros2_fast_loaned::msg::Payload4194304>(argc, argv,
                                                                 config);
    default:
      std::cerr << "Unsupported loaned payload size: "
                << config.payload_size_bytes << std::endl;
      return constants::FAILED_APP_FINISH;
  }
}

}  // namespace tb

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << __FUNCTION__ << ": " << __LINE__ << std::endl;
    return tb::constants::FAILED_APP_FINISH;
  }

  return tb::dispatch(argc, argv, tb::utils::parseConfig(argv[1]));
}
