use iceoryx2::prelude::*;
use std::fs;
use std::path::Path;
use std::time::Duration;
use std::thread;

use rust_iceoryx2_flatbuffers::flatbuffers_generated::rust_iceoryx_2_flatbuffers::Payload;
use rust_iceoryx2_flatbuffers::{Config, utils, RESULTS_FILE_PATH, PAYLOAD_DATA_CHUNK};

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
            let now = utils::now();
            let sample_slice = sample.payload();

            let aligned_buffer: Vec<u8> = sample_slice.to_vec();
            let payload = flatbuffers::root::<Payload>(&aligned_buffer)
                       .map_err(|e| anyhow::anyhow!("FlatBuffer parse error: {:?}", e))?;

            let timestamp = payload.timestamp();
            let seq_num = payload.message_number();
            let data_option = payload.payload();

            if let Some(data_vec) = data_option {
                let data_slice: &[u8] = data_vec.bytes();

                if data_slice.len() != config.payload_size_bytes {
                    eprintln!(
                        "Payload size mismatch (msg {}): expected {}, got {}",
                        seq_num,
                        config.payload_size_bytes,
                        data_slice.len()
                    );
                    continue;
                }

                if !data_slice.iter().all(|&b| b == PAYLOAD_DATA_CHUNK) {
                    eprintln!("Invalid payload pattern in message {}", seq_num);
                    continue;
                }
            } else {
                eprintln!("Missing payload data in message {}", seq_num);
                continue;
            }

            let latency = now - timestamp;
            latencies.push(latency);
        } else {
            thread::sleep(Duration::from_micros(2));
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
