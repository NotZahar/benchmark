#include <chrono>
#include <cstdint>
#include <cstring>
#include <thread>
#include <zmq.hpp>

#include "flat/Payload_generated.h"
#include "zmq_flatbuffers/constants.hh"
#include "zmq_flatbuffers/utils.hh"

inline constexpr auto METADATA_OVERHEAD = 256;

namespace tb {

class Publisher {
 public:
  Publisher() = delete;
  Publisher(utils::Config config, std::string transport_type) noexcept
      : config_{config},
        builder_{config_.payload_size_bytes + METADATA_OVERHEAD},
        message_number_{0},
        context_{1},
        socket_{context_, zmq::socket_type::pub} {
    std::filesystem::remove("/tmp/zmq_benchmark_flat.ipc");
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
    builder_.Clear();

    std::vector<uint8_t> data(config_.payload_size_bytes,
                              constants::PAYLOAD_DATA_CHUNK);

    const auto data_vector = builder_.CreateVector(data);
    builder_.Finish(tb_flat::CreatePayload(builder_, timestamp, data_vector,
                                           message_number_++));

    zmq::message_t message(builder_.GetBufferPointer(), builder_.GetSize());
    socket_.send(message, zmq::send_flags::none);
  }

  const utils::Config config_;
  flatbuffers::FlatBufferBuilder builder_;
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
