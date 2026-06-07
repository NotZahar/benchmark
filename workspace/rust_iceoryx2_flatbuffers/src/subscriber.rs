use iceoryx2::prelude::*;
use std::fs;
use std::path::Path;

use rust_iceoryx2_flatbuffers::flatbuffers_generated::rust_iceoryx_2_flatbuffers::Payload;
use rust_iceoryx2_flatbuffers::{Config, RESULTS_FILE_PATH, utils};

fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 3 {
        eprintln!("Usage: {} <config_file> <instance_id>", args[0]);
        std::process::exit(1);
    }

    let config = Config::from_file(Path::new(&args[1]))?;
    let instance_id: i32 = args[2].parse()?;

    let node_name_str = format!("benchmark_subscriber_flatbuffers_{}", instance_id);
    let node_name: NodeName = node_name_str.as_str().try_into()?;

    let node = NodeBuilder::new()
        .name(&node_name)
        .create::<ipc::Service>()?;

    let service_name: ServiceName = "BenchmarkService_FlatBuffers".try_into()?;
    let service = node
        .service_builder(&service_name)
        .publish_subscribe::<[u8]>()
        .open_or_create()?;

    let subscriber = service.subscriber_builder().create()?;

    let mut latencies = Vec::with_capacity(config.number_of_samples);

    while latencies.len() < config.number_of_samples {
        if let Some(sample) = subscriber.receive()? {
            let sample_slice = sample.payload();

            let aligned_buffer: Vec<u8> = sample_slice.to_vec();

            let payload = flatbuffers::size_prefixed_root::<Payload>(&aligned_buffer)
                .map_err(|e| anyhow::anyhow!("FlatBuffer parse error: {:?}", e))?;

            let timestamp = payload.timestamp();
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
