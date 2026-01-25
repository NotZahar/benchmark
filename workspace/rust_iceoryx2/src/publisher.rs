use std::time::{Duration, SystemTime};
use std::thread;
use std::path::Path;
use std::mem::MaybeUninit;

use iceoryx2::prelude::*;
use rust_iceoryx2::{Config, PAYLOAD_DATA_CHUNK, utils};

fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 2 {
        eprintln!("Usage: {} <config_file>", args[0]);
        std::process::exit(1);
    }

    let config = Config::from_file(Path::new(&args[1]))?;

    let node_name: NodeName = "benchmark_publisher".try_into()?;
    let node = NodeBuilder::new()
        .name(&node_name)
        .create::<ipc::Service>()?;

    let service_name_str = "BenchmarkService_Shared";
    let service_name: ServiceName = service_name_str.try_into()?;

    let service = node
        .service_builder(&service_name)
        .publish_subscribe::<[u8]>()
        .open_or_create()?;

    let publisher = service
        .publisher_builder()
        .initial_max_slice_len(config.payload_size_bytes + 12)
        .create()?;

    thread::sleep(Duration::from_millis(500));

    let mut message_number = 0;
    let period = Duration::from_millis(config.publish_period_ms as u64);

    while message_number < config.number_of_samples {
        let next_wake = SystemTime::now() + period;

        let total_size = config.payload_size_bytes + 12;
        let mut local_buffer = vec![PAYLOAD_DATA_CHUNK; total_size];

        let timestamp = utils::now();
        let timestamp_bytes = timestamp.to_le_bytes();
        local_buffer[0..8].copy_from_slice(&timestamp_bytes);

        let msg_number_u32 = message_number as u32;
        let msg_bytes = msg_number_u32.to_le_bytes();
        local_buffer[8..12].copy_from_slice(&msg_bytes);

        let mut sample = publisher.loan_slice_uninit(total_size)?;
        let payload = sample.payload_mut();

        for (i, &byte) in local_buffer.iter().enumerate() {
            payload[i] = MaybeUninit::new(byte);
        }

        let initialized_sample = unsafe { sample.assume_init() };
        initialized_sample.send()?;

        message_number += 1;

        if next_wake > SystemTime::now() {
            thread::sleep(next_wake.duration_since(SystemTime::now())?);
        }
    }

    thread::sleep(Duration::from_secs(1));
    Ok(())
}
