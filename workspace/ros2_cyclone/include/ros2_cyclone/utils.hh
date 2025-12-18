#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>
#include <yaml-cpp/yaml.h>

namespace {

[[nodiscard]] inline double
makeAverage(const std::vector<std::int64_t> &latencies) noexcept {
  const auto number_of_samples = latencies.size();

  return static_cast<double>(
             std::accumulate(latencies.cbegin(), latencies.cend(), 0LL)) /
         static_cast<double>(number_of_samples);
}

[[nodiscard]] inline double
makeMedian(const std::vector<std::int64_t> &latencies) noexcept {
  const auto number_of_samples = latencies.size();

  return (number_of_samples % 2 == 1)
             ? static_cast<double>(latencies[number_of_samples / 2])
             : 0.5 *
                   (static_cast<double>(latencies[number_of_samples / 2 - 1]) +
                    static_cast<double>(latencies[number_of_samples / 2]));
}

[[nodiscard]] inline std::int64_t
makeP99(const std::vector<std::int64_t> &latencies) noexcept {
  const auto number_of_samples = latencies.size();

  std::size_t index99 = static_cast<std::size_t>(
      std::ceil(0.99 * static_cast<double>(number_of_samples)));
  index99 = (index99 == 0 ? 0 : index99 - 1);
  if (index99 >= number_of_samples)
    index99 = number_of_samples - 1;

  return latencies[index99];
}

} // namespace

namespace tb::utils {

struct Config {
  std::size_t payload_size_bytes;
  std::size_t publish_period_ms;
  std::size_t number_of_samples;
};

using TimePointType = decltype(std::chrono::steady_clock::now());

[[nodiscard]] inline Config
parseConfig(const std::string path_to_config) noexcept {
  Config config;

  if (!std::filesystem::is_regular_file(path_to_config)) {
    std::cerr << __FUNCTION__ << ": " << __LINE__ << std::endl;
    std::abort();

    return config;
  }

  auto root = YAML::LoadFile(path_to_config);
  if (!root["payload_size_bytes"] || !root["publish_period_ms"] ||
      !root["number_of_samples"]) {
    std::cerr << __FUNCTION__ << ": " << __LINE__ << std::endl;
    std::abort();

    return config;
  }

  config.payload_size_bytes =
      root["payload_size_bytes"].as<decltype(Config::payload_size_bytes)>();
  config.publish_period_ms =
      root["publish_period_ms"].as<decltype(Config::publish_period_ms)>();
  config.number_of_samples =
      root["number_of_samples"].as<decltype(Config::number_of_samples)>();

  return config;
}

[[nodiscard]] inline std::string
makeBenchmarkResult(Config config,
                    std::vector<std::int64_t> latencies) noexcept {
  if (latencies.size() != config.number_of_samples)
    return "Invalid input data\n";

  std::string result = "";
  std::sort(latencies.begin(), latencies.end());

  const auto number_of_samples = latencies.size();
  const auto average = makeAverage(latencies);
  const auto median = makeMedian(latencies);
  const auto p99 = makeP99(latencies);

  result += "Number of samples: " + std::to_string(number_of_samples) + "\n";
  result +=
      "Payload size: " + std::to_string(config.payload_size_bytes) + " bytes\n";
  result +=
      "Publish period: " + std::to_string(config.publish_period_ms) + " ms\n\n";
  result += "Average latency: " + std::to_string(average) + " ns\n";
  result += "Median latency: " + std::to_string(median) + " ns\n";
  result += "P99 latency: " + std::to_string(p99) + " ns\n";

  return result;
}

[[nodiscard]] inline TimePointType now() noexcept {
  return std::chrono::steady_clock::now();
}

[[nodiscard]] inline long elapsed(const TimePointType &t1,
                                  const TimePointType &t2) noexcept {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(t2 - t1).count();
}

} // namespace tb::utils