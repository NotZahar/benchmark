use std::mem::MaybeUninit;
use std::path::Path;
use std::thread;
use std::time::{Duration, Instant};

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
        let next_wake = Instant::now() + period;

        let timestamp = utils::now();
        let total_size = config.payload_size_bytes + 12;
        let mut sample = publisher.loan_slice_uninit(total_size)?;
        let payload = sample.payload_mut();

        for byte in payload.iter_mut() {
            *byte = MaybeUninit::new(PAYLOAD_DATA_CHUNK);
        }
        for (index, byte) in (message_number as u32).to_le_bytes().iter().enumerate() {
            payload[8 + index] = MaybeUninit::new(*byte);
        }
        for (index, byte) in timestamp.to_le_bytes().iter().enumerate() {
            payload[index] = MaybeUninit::new(*byte);
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
