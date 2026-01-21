#include <capnp/message.h>
#include <capnp/serialize-packed.h>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <kj/array.h>
#include <kj/common.h>
#include <kj/debug.h>
#include <kj/exception.h>
#include <kj/io.h>
#include <string>
#include <thread>
#include <vector>
#include <zmq.hpp>

#include "Payload.capnp.h"
#include "zmq_capnproto/constants.hh"
#include "zmq_capnproto/utils.hh"

namespace tb {

class Publisher {
public:
  Publisher() = delete;

  Publisher(utils::Config config, std::string transport_type) noexcept
      : config_{config}, 
        payload_size_{config.payload_size_bytes},
        message_number_{0}, 
        context_{1},
        socket_{context_, zmq::socket_type::pub} {

    std::filesystem::remove("/tmp/zmq_benchmark_capnp.ipc");

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
    capnp::MallocMessageBuilder message_builder;

    std::vector<uint8_t> payload_data_vec(payload_size_, 
                                          static_cast<uint8_t>(constants::PAYLOAD_DATA_CHUNK));

    auto payload_builder = message_builder.initRoot<tb_proto::Payload>();
    
    auto timestamp = utils::now();
    auto msg_num = message_number_++;
    
    payload_builder.setTimeStampNs(timestamp);
    payload_builder.setMessageNumber(msg_num);

    kj::ArrayPtr<const uint8_t> data_array_ptr(payload_data_vec.data(), payload_size_);
    payload_builder.setData(data_array_ptr);

    kj::VectorOutputStream raw_output_stream;
    capnp::writePackedMessage(raw_output_stream, message_builder);

    kj::ArrayPtr<const kj::byte> serialized_data = raw_output_stream.getArray();
    
    static zmq::message_t zmq_message;
    
    if (zmq_message.size() < serialized_data.size()) {
      zmq_message.rebuild(serialized_data.size());
    }
    
    std::memcpy(zmq_message.data(), serialized_data.begin(), serialized_data.size());
    socket_.send(zmq_message, zmq::send_flags::none);
  }

  const utils::Config config_;
  const size_t payload_size_;
  std::uint32_t message_number_;
  zmq::context_t context_;
  zmq::socket_t socket_;
};

} // namespace tb

int main(int argc, char **argv) {
  if (argc != 3)
    return tb::constants::FAILED_APP_FINISH;

  tb::Publisher publisher{tb::utils::parseConfig(argv[1]), argv[2]};
  publisher.run();

  return tb::constants::SUCCESS_APP_FINISH;
}