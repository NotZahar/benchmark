use anyhow::{Context, Result};
use rust_zenoh::flatbuffers_generated::rust_zenoh::{Payload, PayloadArgs};
use rust_zenoh::{
    Codec, CommonArgs, Config, KEY_EXPR, PAYLOAD_DATA_CHUNK, PayloadMode, map_zenoh,
    zenoh_client_config,
};
use std::path::Path;
use std::thread;
use std::time::{Duration, Instant};
use zenoh::Wait;
use zenoh::qos::CongestionControl;
use zenoh::shm::{BlockOn, GarbageCollect, PosixShmProviderBackend, ShmProviderBuilder};

fn make_raw_payload(config: &Config, message_number: u32) -> Vec<u8> {
    let timestamp = rust_zenoh::utils::now();
    let mut payload = vec![PAYLOAD_DATA_CHUNK; config.payload_size_bytes + 12];
    payload[8..12].copy_from_slice(&message_number.to_le_bytes());
    payload[0..8].copy_from_slice(&timestamp.to_le_bytes());
    payload
}

fn make_flatbuffers_payload(config: &Config, message_number: u32) -> Vec<u8> {
    let mut builder = flatbuffers::FlatBufferBuilder::with_capacity(
        config.payload_size_bytes.saturating_add(128),
    );
    let data = vec![PAYLOAD_DATA_CHUNK; config.payload_size_bytes];
    let timestamp = rust_zenoh::utils::now();
    let payload_data = builder.create_vector(&data);
    let payload = Payload::create(
        &mut builder,
        &PayloadArgs {
            timestamp,
            message_number,
            payload: Some(payload_data),
        },
    );
    builder.finish_size_prefixed(payload, None);
    builder.finished_data().to_vec()
}

fn make_payload(config: &Config, codec: Codec, message_number: u32) -> Vec<u8> {
    match codec {
        Codec::Raw => make_raw_payload(config, message_number),
        Codec::Flatbuffers => make_flatbuffers_payload(config, message_number),
    }
}

fn fill_raw_payload(payload: &mut [u8], message_number: u32) {
    let timestamp = rust_zenoh::utils::now();
    payload.fill(PAYLOAD_DATA_CHUNK);
    payload[8..12].copy_from_slice(&message_number.to_le_bytes());
    payload[0..8].copy_from_slice(&timestamp.to_le_bytes());
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        eprintln!(
            "Usage: {} <config_file> [endpoint] [raw|flatbuffers] [bytes|shm] [output_dir]",
            args[0]
        );
        std::process::exit(1);
    }

    let config = Config::from_file(Path::new(&args[1]))?;
    let common_args = CommonArgs::parse(&args, 2)?;
    let use_shm = common_args.payload_mode == PayloadMode::Shm;
    let session =
        map_zenoh(zenoh::open(zenoh_client_config(&common_args.endpoint, use_shm)?).wait())?;
    let publisher = map_zenoh(
        session
            .declare_publisher(KEY_EXPR)
            .congestion_control(CongestionControl::Block)
            .wait(),
    )?;

    let shm_provider = if use_shm {
        let max_payload_size = config.payload_size_bytes.saturating_add(4096);
        let backend = PosixShmProviderBackend::builder(max_payload_size * 16)
            .wait()
            .map_err(|err| anyhow::anyhow!("failed to create zenoh SHM backend: {err}"))?;
        Some(ShmProviderBuilder::backend(backend).wait())
    } else {
        None
    };

    thread::sleep(Duration::from_millis(500));

    let period = Duration::from_millis(config.publish_period_ms as u64);
    for message_number in 0..config.number_of_samples {
        let next_wake = Instant::now() + period;
        if let Some(provider) = shm_provider.as_ref() {
            let flatbuffers_payload = (common_args.codec == Codec::Flatbuffers)
                .then(|| make_payload(&config, common_args.codec, message_number as u32));
            let payload_size = flatbuffers_payload
                .as_ref()
                .map_or(config.payload_size_bytes + 12, Vec::len);
            let layout = provider.alloc_layout(payload_size)?;
            let mut shm_payload = layout
                .alloc()
                .with_policy::<BlockOn<GarbageCollect>>()
                .wait()
                .context("failed to allocate zenoh SHM payload")?;
            match common_args.codec {
                Codec::Raw => {
                    fill_raw_payload(shm_payload.as_mut(), message_number as u32);
                }
                Codec::Flatbuffers => {
                    let payload = flatbuffers_payload.as_ref().expect("flatbuffers payload");
                    shm_payload.as_mut().copy_from_slice(payload.as_slice());
                }
            }
            map_zenoh(publisher.put(shm_payload).wait())?;
        } else {
            let payload = make_payload(&config, common_args.codec, message_number as u32);
            map_zenoh(publisher.put(payload).wait())?;
        }

        let now = Instant::now();
        if next_wake > now {
            thread::sleep(next_wake.duration_since(now));
        }
    }

    thread::sleep(Duration::from_secs(1));
    Ok(())
}
