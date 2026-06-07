#pragma once

#include <cstdint>

namespace tb::constants {

inline constexpr auto ZMQ_TCP_ENDPOINT = "tcp://127.0.0.1:5555";
inline constexpr auto ZMQ_IPC_ENDPOINT = "ipc:///tmp/zmq_benchmark_capnp.ipc";
inline constexpr std::uint8_t PAYLOAD_DATA_CHUNK = 0xFF;
inline constexpr auto RESULTS_FILE_PATH = "/root/workspace/tmp/zmq_capnproto";

inline constexpr auto SUCCESS_APP_FINISH = 0;
inline constexpr auto FAILED_APP_FINISH = 1;

}  // namespace tb::constants
