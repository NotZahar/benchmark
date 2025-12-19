#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <flatbuffers/flatbuffers.h>
#include <fstream>
#include <iostream>
#include <thread>
#include <vector>
#include <zmq.hpp>

#include "flat/Payload_generated.h"
#include "zmq_flatbuffers/constants.hh"
#include "zmq_flatbuffers/utils.hh"

namespace tb {

class Subscriber {
public:
  Subscriber() = delete;
  Subscriber(utils::Config config, int instance_id)
      : config_{config}, instance_id_{instance_id}, context_{1},
        socket_{context_, zmq::socket_type::sub} {
    latencies_.reserve(config_.number_of_samples);

    socket_.connect(constants::ZMQ_TCP_ENDPOINT);
    socket_.set(zmq::sockopt::subscribe, "");

    // Skip initial messages during connection stabilization
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
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
    out << utils::makeBenchmarkResult(config_, std::move(latencies_));
    out.close();
  }

  void run() {
    while (latencies_.size() < config_.number_of_samples) {
      zmq::message_t message;
      auto result = socket_.recv(message, zmq::recv_flags::none);

      if (result) {
        tack(message);
      }
    }
  }

private:
  void tack(const zmq::message_t &message) {
    auto payload = tb_flat::GetPayload(message.data());

    if (!payload->data() || payload->data()->size() == 0 ||
        (*payload->data())[0] != constants::PAYLOAD_DATA_CHUNK) {
      std::cerr << "Invalid payload data" << std::endl;
      std::abort();
    }

    auto now =
        std::chrono::high_resolution_clock::now().time_since_epoch().count();

    std::int64_t latency_ns = now - payload->time_stamp_ns();
    latencies_.push_back(latency_ns);
  }

  const utils::Config config_;
  int instance_id_;
  std::vector<std::int64_t> latencies_;
  zmq::context_t context_;
  zmq::socket_t socket_;
};

} // namespace tb

int main(int argc, char **argv) {
  if (argc != 3)
    return tb::constants::FAILED_APP_FINISH;

  tb::Subscriber subscriber{tb::utils::parseConfig(argv[1]),
                            std::stoi(argv[2])};
  subscriber.run();

  return tb::constants::SUCCESS_APP_FINISH;
}
