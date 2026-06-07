#include <chrono>
#include <cstdint>
#include <filesystem>
#include <string>
#include <thread>
#include <zmq.hpp>

#include "Payload.pb.h"
#include "zmq_protobuf/constants.hh"
#include "zmq_protobuf/utils.hh"

namespace tb {

class Publisher {
 public:
  Publisher() = delete;

  Publisher(utils::Config config, std::string transport_type) noexcept
      : config_{config},
        message_number_{0},
        context_{1},
        socket_{context_, zmq::socket_type::pub} {
    std::filesystem::remove("/tmp/zmq_benchmark_proto.ipc");

    socket_.bind(transport_type == "tcp" ? constants::ZMQ_TCP_ENDPOINT
                                         : constants::ZMQ_IPC_ENDPOINT);

    std::this_thread::sleep_for(std::chrono::milliseconds(500));
  }

  void run() noexcept {
    auto next_wake = std::chrono::steady_clock::now();
    const auto period = std::chrono::milliseconds(config_.publish_period_ms);

    while (message_number_ < config_.number_of_samples) {
      next_wake += period;
      tick();
      std::this_thread::sleep_until(next_wake);
    }

    std::this_thread::sleep_for(std::chrono::seconds(1));
  }

 private:
  void tick() noexcept {
    const auto timestamp = utils::now();
    tb_proto::Payload payload;

    std::string data(config_.payload_size_bytes,
                     static_cast<char>(constants::PAYLOAD_DATA_CHUNK));
    payload.mutable_data()->assign(data.data(), data.size());
    payload.set_message_number(message_number_++);
    payload.set_time_stamp_ns(timestamp);

    const auto size = payload.ByteSizeLong();
    zmq::message_t message(size);

    if (!payload.SerializeToArray(message.data(),
                                  static_cast<int>(message.size()))) {
      std::cerr << __FUNCTION__ << ": " << __LINE__ << std::endl;
      std::abort();
    }

    socket_.send(message, zmq::send_flags::none);
  }

  const utils::Config config_;
  std::uint32_t message_number_;
  zmq::context_t context_;
  zmq::socket_t socket_;
};

}  // namespace tb

int main(int argc, char** argv) {
  if (argc != 3) return tb::constants::FAILED_APP_FINISH;

  tb::Publisher publisher{tb::utils::parseConfig(argv[1]), argv[2]};
  publisher.run();

  return tb::constants::SUCCESS_APP_FINISH;
}
