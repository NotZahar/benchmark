#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <utility>
#include <vector>
#include <zmq.hpp>

#include "Payload.pb.h"
#include "zmq_protobuf/constants.hh"
#include "zmq_protobuf/utils.hh"

namespace tb {

class Subscriber {
public:
  Subscriber() = delete;

  Subscriber(utils::Config config, int instance_id, std::string transport_type)
      : config_{config}, transport_type_{std::move(transport_type)},
        instance_id_{instance_id}, context_{1},
        socket_{context_, zmq::socket_type::sub} {

    latencies_.reserve(config_.number_of_samples);

    socket_.connect(transport_type_ == "tcp" ? constants::ZMQ_TCP_ENDPOINT
                                             : constants::ZMQ_IPC_ENDPOINT);
    socket_.set(zmq::sockopt::subscribe, "");
  }

  ~Subscriber() {
    const auto result_folder =
        std::string{constants::RESULTS_FILE_PATH} + "_" + transport_type_ +
        "/latencies/" + std::to_string(config_.payload_size_bytes) + "_bytes_" +
        std::to_string(config_.publish_period_ms) + "_ms_" +
        std::to_string(config_.number_of_samples) + "_samples";

    std::filesystem::create_directories(result_folder);

    const auto result_file =
        result_folder + "/" + std::to_string(instance_id_) + "_subscriber.txt";

    std::ofstream out{result_file};
    out << utils::makeBenchmarkResult(config_, std::move(latencies_));
    out.close();
  }

  void run() {
    while (latencies_.size() < config_.number_of_samples) {
      zmq::message_t message;
      const auto result = socket_.recv(message, zmq::recv_flags::none);
      if (result)
        tack(message);
    }
  }

private:
  void tack(const zmq::message_t &message) {
    tb_proto::Payload payload;

    if (!payload.ParseFromArray(message.data(),
                                static_cast<int>(message.size()))) {
      std::cerr << "Failed to parse protobuf payload" << std::endl;
      std::abort();
    }

    if (payload.data().empty() ||
        static_cast<std::uint8_t>(payload.data()[0]) !=
            constants::PAYLOAD_DATA_CHUNK) {
      std::cerr << "Invalid payload data" << std::endl;
      std::abort();
    }

    const auto latency_ns = utils::now() - payload.time_stamp_ns();
    latencies_.push_back(latency_ns);
  }

  const utils::Config config_;
  std::string transport_type_;
  int instance_id_;
  std::vector<std::int64_t> latencies_;
  zmq::context_t context_;
  zmq::socket_t socket_;
};

} // namespace tb

int main(int argc, char **argv) {
  if (argc != 4)
    return tb::constants::FAILED_APP_FINISH;

  tb::Subscriber subscriber{tb::utils::parseConfig(argv[1]), std::stoi(argv[2]),
                            argv[3]};
  subscriber.run();

  return tb::constants::SUCCESS_APP_FINISH;
}
