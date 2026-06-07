use iceoryx2::prelude::*;
use rust_iceoryx2::{Config, RESULTS_FILE_PATH, utils};
use std::fs;
use std::path::Path;

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

    let service_name: ServiceName = "BenchmarkService_Shared".try_into()?;
    let service = node
        .service_builder(&service_name)
        .publish_subscribe::<[u8]>()
        .open_or_create()?;

    let subscriber = service.subscriber_builder().create()?;

    let mut latencies = Vec::with_capacity(config.number_of_samples);

    while latencies.len() < config.number_of_samples {
        if let Some(sample) = subscriber.receive()? {
            let sample_slice = sample.payload();

            if sample_slice.len() < 8 {
                anyhow::bail!("sample is too small: {}", sample_slice.len());
            }

            let timestamp_bytes: [u8; 8] = sample_slice[0..8].try_into()?;
            let timestamp = i64::from_le_bytes(timestamp_bytes);
            let now = utils::now();
            let latency = now - timestamp;
            latencies.push(latency);
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
