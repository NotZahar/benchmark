use iceoryx2::prelude::*;
use std::mem::MaybeUninit;
use std::path::Path;
use std::thread;
use std::time::{Duration, Instant};

use rust_iceoryx2_flatbuffers::flatbuffers_generated::rust_iceoryx_2_flatbuffers::{
    Payload, PayloadArgs,
};
use rust_iceoryx2_flatbuffers::{Config, PAYLOAD_DATA_CHUNK, utils};

fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        eprintln!("Usage: {} <config_file>", args[0]);
        std::process::exit(1);
    }

    let config = Config::from_file(Path::new(&args[1]))?;

    if config.should_enable_logging() {
        env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();
    }

    let node_name_str = config.get_publisher_node_name();
    let node_name: NodeName = node_name_str
        .try_into()
        .map_err(|e| anyhow::anyhow!("Invalid node name '{}': {}", node_name_str, e))?;

    let node = NodeBuilder::new()
        .name(&node_name)
        .create::<ipc::Service>()
        .map_err(|e| anyhow::anyhow!("Failed to create node: {}", e))?;

    let service_name_str = config.get_topic_name();
    let service_name: ServiceName = service_name_str
        .try_into()
        .map_err(|e| anyhow::anyhow!("Invalid service name '{}': {}", service_name_str, e))?;

    let service = node
        .service_builder(&service_name)
        .publish_subscribe::<[u8]>()
        .open_or_create()
        .map_err(|e| anyhow::anyhow!("Failed to open service: {}", e))?;

    let max_slice_len = config.payload_size_bytes + 128;
    let publisher = service
        .publisher_builder()
        .initial_max_slice_len(max_slice_len)
        .create()
        .map_err(|e| anyhow::anyhow!("Failed to create publisher: {}", e))?;

    thread::sleep(Duration::from_millis(1000));

    let mut message_number = 0;
    let period = Duration::from_millis(config.publish_period_ms as u64);

    while message_number < config.number_of_samples {
        let publish_start = Instant::now();
        let next_wake = publish_start + period;

        let mut fbb = flatbuffers::FlatBufferBuilder::new();
        let data = vec![PAYLOAD_DATA_CHUNK; config.payload_size_bytes];
        let timestamp = utils::now_ns();
        let data_vec = fbb.create_vector(&data);

        let payload = Payload::create(
            &mut fbb,
            &PayloadArgs {
                timestamp,
                message_number: message_number as u32,
                payload: Some(data_vec),
            },
        );
        fbb.finish_size_prefixed(payload, None);
        let buffer = fbb.finished_data();

        let mut sample = publisher.loan_slice_uninit(buffer.len())?;
        let payload_mut = sample.payload_mut();
        for (index, &byte) in buffer.iter().enumerate() {
            payload_mut[index] = MaybeUninit::new(byte);
        }
        let initialized_sample = unsafe { sample.assume_init() };
        initialized_sample.send()?;

        message_number += 1;

        let now = Instant::now();
        if next_wake > now {
            thread::sleep(next_wake.duration_since(now));
        }
    }

    thread::sleep(Duration::from_secs(1));

    Ok(())
}
