use anyhow::{Result, anyhow, bail};
use serde::{Deserialize, Serialize};
use std::error::Error;
use std::path::Path;

pub const PAYLOAD_DATA_CHUNK: u8 = 0xFF;
pub const DEFAULT_RESULTS_DIR: &str = "rust_zenoh_router_tcp";
pub const KEY_EXPR: &str = "transport_benchmark/payload";

pub mod flatbuffers_generated {
    include!(concat!(env!("OUT_DIR"), "/rust_zenoh_payload.rs"));
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Config {
    pub payload_size_bytes: usize,
    pub publish_period_ms: usize,
    pub number_of_samples: usize,
}

impl Config {
    pub fn from_file(path: &Path) -> Result<Self> {
        let file = std::fs::File::open(path)?;
        let config: Config = serde_yaml::from_reader(file)?;
        Ok(config)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Codec {
    Raw,
    Flatbuffers,
}

impl Codec {
    pub fn parse(value: &str) -> Result<Self> {
        match value {
            "raw" => Ok(Self::Raw),
            "flatbuffers" => Ok(Self::Flatbuffers),
            _ => bail!("unknown zenoh codec: {value}"),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PayloadMode {
    Bytes,
    Shm,
}

impl PayloadMode {
    pub fn parse(value: &str) -> Result<Self> {
        match value {
            "bytes" => Ok(Self::Bytes),
            "shm" => Ok(Self::Shm),
            _ => bail!("unknown zenoh payload mode: {value}"),
        }
    }
}

#[derive(Debug)]
pub struct CommonArgs {
    pub endpoint: String,
    pub codec: Codec,
    pub payload_mode: PayloadMode,
    pub output_dir_name: String,
}

impl CommonArgs {
    pub fn parse(args: &[String], start: usize) -> Result<Self> {
        let endpoint = args
            .get(start)
            .cloned()
            .unwrap_or_else(|| "tcp/127.0.0.1:17447".to_string());
        let codec = Codec::parse(args.get(start + 1).map(String::as_str).unwrap_or("raw"))?;
        let payload_mode =
            PayloadMode::parse(args.get(start + 2).map(String::as_str).unwrap_or("bytes"))?;
        let output_dir_name = args
            .get(start + 3)
            .cloned()
            .unwrap_or_else(|| DEFAULT_RESULTS_DIR.to_string());

        Ok(Self {
            endpoint,
            codec,
            payload_mode,
            output_dir_name,
        })
    }
}

pub fn results_file_path(output_dir_name: &str) -> String {
    format!("/root/workspace/tmp/{output_dir_name}")
}

pub fn zenoh_client_config(endpoint: &str, enable_shm: bool) -> Result<zenoh::Config> {
    let mut config = zenoh::Config::default();
    insert_json5(&mut config, "mode", r#""client""#)?;
    insert_json5(
        &mut config,
        "connect/endpoints",
        &format!(r#"["{}"]"#, endpoint),
    )?;
    insert_json5(&mut config, "connect/timeout_ms", "-1")?;
    insert_json5(&mut config, "connect/exit_on_failure", "true")?;
    insert_json5(&mut config, "listen/endpoints", "[]")?;
    insert_json5(&mut config, "scouting/multicast/enabled", "false")?;
    insert_json5(&mut config, "scouting/gossip/enabled", "false")?;
    insert_json5(&mut config, "timestamping/enabled", "false")?;
    if endpoint.starts_with("quic/") {
        let ca_certificate = std::env::var("ZENOH_QUIC_CA_CERTIFICATE")
            .unwrap_or_else(|_| "/tmp/transport-benchmark-zenoh-quic-certs/ca.pem".to_string());
        insert_json5(&mut config, "transport/link/protocols", r#"["quic"]"#)?;
        insert_json5(
            &mut config,
            "transport/link/tls/root_ca_certificate",
            &format!(r#""{}""#, ca_certificate),
        )?;
        insert_json5(
            &mut config,
            "transport/link/tls/verify_name_on_connect",
            "false",
        )?;
    }
    insert_json5(
        &mut config,
        "transport/shared_memory/enabled",
        if enable_shm { "true" } else { "false" },
    )?;
    if enable_shm {
        insert_json5(&mut config, "transport/shared_memory/mode", r#""init""#)?;
        insert_json5(
            &mut config,
            "transport/shared_memory/transport_optimization/message_size_threshold",
            "1",
        )?;
        insert_json5(
            &mut config,
            "transport/shared_memory/transport_optimization/pool_size",
            "67108864",
        )?;
    }
    Ok(config)
}

fn insert_json5(config: &mut zenoh::Config, key: &str, value: &str) -> Result<()> {
    config
        .insert_json5(key, value)
        .map_err(|err| anyhow!("failed to set zenoh config {key}: {err}"))
}

pub fn map_zenoh<T>(result: std::result::Result<T, Box<dyn Error + Send + Sync>>) -> Result<T> {
    result.map_err(|err| anyhow!("{err}"))
}

pub mod utils {
    use super::*;

    pub fn now() -> i64 {
        let mut ts = libc::timespec {
            tv_sec: 0,
            tv_nsec: 0,
        };
        let result = unsafe { libc::clock_gettime(libc::CLOCK_MONOTONIC, &mut ts) };
        assert_eq!(result, 0, "clock_gettime(CLOCK_MONOTONIC) failed");

        (ts.tv_sec as i64) * 1_000_000_000 + (ts.tv_nsec as i64)
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

        if latencies.len() % 2 == 1 {
            latencies[latencies.len() / 2] as f64
        } else {
            (latencies[latencies.len() / 2 - 1] as f64 + latencies[latencies.len() / 2] as f64)
                / 2.0
        }
    }

    pub fn make_p99(latencies: &[i64]) -> i64 {
        if latencies.is_empty() {
            return 0;
        }

        let index = (latencies.len() as f64 * 0.99).ceil() as usize - 1;
        latencies[index.min(latencies.len() - 1)]
    }

    pub fn make_benchmark_result(config: &Config, mut latencies: Vec<i64>) -> String {
        latencies.sort();

        let average = make_average(&latencies);
        let median = make_median(&latencies);
        let p99 = make_p99(&latencies);

        format!(
            "Number of samples: {}\n\
             Payload size: {} bytes\n\
             Publish period: {} ms\n\n\
             Average latency: {} ns\n\
             Median latency: {} ns\n\
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
