use serde::{Deserialize, Serialize};
use std::path::Path;
use anyhow::Result;

pub const PAYLOAD_DATA_CHUNK: u8 = 0xFF;
pub const RESULTS_FILE_PATH: &str = "/root/workspace/tmp/rust_iceoryx2_flatbuffers";

pub mod flatbuffers_generated {
    include!(concat!(env!("OUT_DIR"), "/rust_iceoryx2_flatbuffers_payload.rs"));
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Config {
    pub payload_size_bytes: usize,
    pub publish_period_ms: usize,
    pub number_of_samples: usize,
    #[serde(default = "default_enable_logging")]
    pub enable_logging: bool,
    #[serde(default = "default_publisher_node_name")]
    pub publisher_node_name: String,
    #[serde(default = "default_topic_name")]
    pub topic_name: String,
}

fn default_enable_logging() -> bool { true }
fn default_publisher_node_name() -> String { "benchmark_publisher_flatbuffers".to_string() }
fn default_topic_name() -> String { "BenchmarkService_FlatBuffers".to_string() }

impl Config {
    pub fn from_file(path: &Path) -> Result<Self> {
        let file = std::fs::File::open(path)?;
        let config: Config = serde_yaml::from_reader(file)?;
        Ok(config)
    }

    pub fn should_enable_logging(&self) -> bool {
        self.enable_logging
    }

    pub fn get_publisher_node_name(&self) -> &str {
        &self.publisher_node_name
    }

    pub fn get_topic_name(&self) -> &str {
        &self.topic_name
    }
}

pub mod utils {
    use super::*;
    use std::time::{SystemTime, UNIX_EPOCH};

    pub fn now() -> i64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos() as i64
    }

    pub fn now_ns() -> i64 {
        now()
    }

    pub fn elapsed(t1: i64, t2: i64) -> i64 {
        t2 - t1
    }

    pub fn make_average(latencies: &[i64]) -> f64 {
        if latencies.is_empty() {
            return 0.0;
        }
        latencies.iter().sum::<i64>() as f64 / latencies.len() as f64
    }

    pub fn make_median(latencies: &[i64]) -> f64 {
        if latencies.is_empty() {
            return 0.0;
        }

        let mut sorted = latencies.to_vec();
        sorted.sort_unstable();

        if sorted.len() % 2 == 1 {
            sorted[sorted.len() / 2] as f64
        } else {
            (sorted[sorted.len() / 2 - 1] as f64 + sorted[sorted.len() / 2] as f64) / 2.0
        }
    }

    pub fn make_p99(latencies: &[i64]) -> i64 {
        if latencies.is_empty() {
            return 0;
        }

        let mut sorted = latencies.to_vec();
        sorted.sort_unstable();

        let index = ((sorted.len() as f64) * 0.99).ceil() as usize - 1;
        sorted[index.min(sorted.len() - 1)]
    }

    pub fn make_benchmark_result(config: &Config, latencies: Vec<i64>) -> String {
        let average = make_average(&latencies);
        let median = make_median(&latencies);
        let p99 = make_p99(&latencies);

        format!(
            "Number of samples: {}\n\
             Payload size: {} bytes\n\
             Publish period: {} ms\n\n\
             Average latency: {:.2} ns\n\
             Median latency: {:.2} ns\n\
             P99 latency: {} ns\n",
            latencies.len(),
            config.payload_size_bytes,
            config.publish_period_ms,
            average,
            median,
            p99
        )
    }
}
