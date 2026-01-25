use std::fs;
use std::path::Path;

use iceoryx2::prelude::*;
use rust_iceoryx2::{Config, PAYLOAD_DATA_CHUNK, utils, RESULTS_FILE_PATH};

fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        eprintln!("Usage: {} <config_file> <instance_id>", args[0]);
        std::process::exit(1);
    }

    let config = Config::from_file(Path::new(&args[1]))?;
    let instance_id: i32 = args[2].parse()?;

    let node_name_str = format!("benchmark_subscriber_{}", instance_id);
    let node_name: NodeName = node_name_str.as_str().try_into()?;

    let node = NodeBuilder::new()
        .name(&node_name)
        .create::<ipc::Service>()?;

    let service_name: ServiceName = "BenchmarkService".try_into()?;
    let service = node
        .service_builder(&service_name)
        .publish_subscribe::<[u8]>()
        .open_or_create()?;

    let subscriber = service.subscriber_builder().create()?;

    let mut latencies = Vec::with_capacity(config.number_of_samples);

    while latencies.len() < config.number_of_samples {
        if let Some(sample) = subscriber.receive()? {
            let now = utils::now();
            let sample_slice = sample.payload();

            if sample_slice.len() < 12 {
                eprintln!("Sample too small");
                continue;
            }

            let timestamp = i64::from_le_bytes(
                sample_slice[0..8].try_into().map_err(|_| anyhow::anyhow!("Failed to read timestamp"))?
            );

            let _message_number = u32::from_le_bytes(
                sample_slice[8..12].try_into().map_err(|_| anyhow::anyhow!("Failed to read message number"))?
            );

            let data_start = 12;
            let data_end = data_start + config.payload_size_bytes;

            if data_end > sample_slice.len() {
                eprintln!("Invalid payload size in sample");
                continue;
            }

            if !sample_slice[data_start..data_end].iter().all(|&b| b == PAYLOAD_DATA_CHUNK) {
                eprintln!("Invalid data pattern");
                continue;
            }

            latencies.push(now - timestamp);
        }
    }

    let result_folder = format!(
        "{}/latencies/{}_bytes_{}_ms_{}_samples",
        RESULTS_FILE_PATH,
        config.payload_size_bytes,
        config.publish_period_ms,
        config.number_of_samples
    );

    fs::create_dir_all(&result_folder)?;

    let result_file = format!("{}/{}_subscriber.txt", result_folder, instance_id);
    fs::write(
        result_file,
        utils::make_benchmark_result(&config, latencies),
    )?;

    Ok(())
}
