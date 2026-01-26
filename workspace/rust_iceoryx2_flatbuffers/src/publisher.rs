use std::time::{Duration, SystemTime};
use std::thread;
use std::path::Path;
use std::mem::MaybeUninit;
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::Arc;
use iceoryx2::prelude::*;
use log::{info, error, warn};

use rust_iceoryx2_flatbuffers::flatbuffers_generated::rust_iceoryx_2_flatbuffers::{Payload, PayloadArgs};
use rust_iceoryx2_flatbuffers::{Config, utils, PAYLOAD_DATA_CHUNK};


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

    info!("Starting publisher with config: {:?}", config);

    let node_name_str = config.get_publisher_node_name();
    let node_name: NodeName = node_name_str.try_into()
        .map_err(|e| anyhow::anyhow!("Invalid node name '{}': {}", node_name_str, e))?;

    let node = NodeBuilder::new()
        .name(&node_name)
        .create::<ipc::Service>()
        .map_err(|e| anyhow::anyhow!("Failed to create node: {}", e))?;

    let service_name_str = config.get_topic_name();
    let service_name: ServiceName = service_name_str.try_into()
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

    info!("Publisher initialized, waiting for subscribers...");
    thread::sleep(Duration::from_millis(1000));

    let message_counter = Arc::new(AtomicU32::new(0));
    let message_counter_clone = Arc::clone(&message_counter);

    let running = Arc::new(std::sync::atomic::AtomicBool::new(true));
    let r = running.clone();
    ctrlc::set_handler(move || {
        r.store(false, Ordering::SeqCst);
        info!("Shutdown signal received");
    }).expect("Error setting Ctrl-C handler");

    let mut message_number = 0;
    let period = Duration::from_millis(config.publish_period_ms as u64);
    let mut missed_deadlines = 0;

    info!("Starting to publish {} messages...", config.number_of_samples);

    while message_number < config.number_of_samples && running.load(Ordering::SeqCst) {
        let publish_start = SystemTime::now();
        let next_wake = publish_start + period;

        let mut fbb = flatbuffers::FlatBufferBuilder::new();
        let data_vec = fbb.create_vector(&vec![PAYLOAD_DATA_CHUNK; config.payload_size_bytes]);

        let payload = Payload::create(
            &mut fbb,
            &PayloadArgs {
                timestamp: utils::now_ns(),
                message_number: message_number as u32,
                payload: Some(data_vec),
            },
        );
        fbb.finish_size_prefixed(payload, None);
        let buffer = fbb.finished_data();

        match publisher.loan_slice_uninit(buffer.len()) {
            Ok(mut sample) => {
                let payload_mut = sample.payload_mut();
                for (i, &byte) in buffer.iter().enumerate() {
                    payload_mut[i] = MaybeUninit::new(byte);
                }
                let initialized_sample = unsafe { sample.assume_init() };
                if let Err(e) = initialized_sample.send() {
                    error!("Failed to send message {}: {}", message_number, e);
                } else {
                    message_counter_clone.store(message_number as u32, Ordering::SeqCst);
                    if message_number % 1000 == 0 {
                        info!("Published message {}", message_number);
                    }
                }
            }
            Err(e) => {
                error!("Failed to loan slice for message {}: {}", message_number, e);
            }
        }

        message_number += 1;

        if let Ok(duration) = next_wake.duration_since(SystemTime::now()) {
            thread::sleep(duration);
        } else {
            missed_deadlines += 1;
            if missed_deadlines % 100 == 0 {
                warn!("Missed {} deadlines", missed_deadlines);
            }
        }
    }

    info!("Publisher finished. Sent {} messages.", message_number);
    thread::sleep(Duration::from_secs(1));

    Ok(())
}
