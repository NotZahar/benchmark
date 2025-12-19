#include <chrono>
#include <cstdint>
#include <cstring>
#include <thread>
#include <zmq.hpp>

#include "flat/Payload_generated.h"
#include "zmq_flatbuffers/constants.hh"
#include "zmq_flatbuffers/utils.hh"

namespace tb {

class Publisher {
public:
  Publisher() = delete;
  explicit Publisher(utils::Config config) noexcept
      : config_{config}, message_number_{0}, context_{1},
        socket_{context_, zmq::socket_type::pub} {
    socket_.bind(constants::ZMQ_TCP_ENDPOINT);
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
  }

  void run() noexcept {
    while (message_number_ < config_.number_of_samples) {
      tick();
      std::this_thread::sleep_for(
          std::chrono::milliseconds(config_.publish_period_ms));
    }

    std::this_thread::sleep_for(std::chrono::seconds(1));
  }

private:
  void tick() noexcept {
    constexpr auto metadata_overhead = 128;
    flatbuffers::FlatBufferBuilder builder{config_.payload_size_bytes +
                                           metadata_overhead};

    std::vector<uint8_t> data(config_.payload_size_bytes,
                              constants::PAYLOAD_DATA_CHUNK);

    builder.Finish(tb_flat::CreatePayload(
        builder, utils::now(), builder.CreateVector(data), message_number_++));

    zmq::message_t message{builder.GetSize()};
    std::memcpy(message.data(), builder.GetBufferPointer(), builder.GetSize());

    socket_.send(message, zmq::send_flags::none);
  }

  const utils::Config config_;
  std::uint32_t message_number_;
  zmq::context_t context_;
  zmq::socket_t socket_;
};

} // namespace tb

int main(int argc, char **argv) {
  if (argc != 2)
    return tb::constants::FAILED_APP_FINISH;

  tb::Publisher publisher{tb::utils::parseConfig(argv[1])};
  publisher.run();

  return tb::constants::SUCCESS_APP_FINISH;
}
