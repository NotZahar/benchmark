use anyhow::{Result, bail};
use rust_zenoh::flatbuffers_generated::rust_zenoh::Payload;
use rust_zenoh::{
    Codec, CommonArgs, Config, KEY_EXPR, PayloadMode, map_zenoh, results_file_path,
    zenoh_client_config,
};
use std::fs;
use std::path::Path;
use zenoh::Wait;

fn decode_raw_timestamp(payload: &[u8]) -> Result<i64> {
    if payload.len() < 8 {
        bail!("raw payload is too small: {}", payload.len());
    }

    Ok(i64::from_le_bytes(payload[0..8].try_into()?))
}

fn decode_flatbuffers_timestamp(payload: &[u8]) -> Result<i64> {
    let decoded = flatbuffers::size_prefixed_root::<Payload>(payload)
        .map_err(|err| anyhow::anyhow!("FlatBuffer parse error: {err:?}"))?;
    Ok(decoded.timestamp())
}

fn decode_payload_timestamp(payload: &[u8], codec: Codec) -> Result<i64> {
    match codec {
        Codec::Raw => decode_raw_timestamp(payload),
        Codec::Flatbuffers => decode_flatbuffers_timestamp(payload),
    }
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 3 {
        eprintln!(
            "Usage: {} <config_file> <instance_id> [endpoint] [raw|flatbuffers] [bytes|shm] [output_dir]",
            args[0]
        );
        std::process::exit(1);
    }

    let config = Config::from_file(Path::new(&args[1]))?;
    let instance_id: i32 = args[2].parse()?;
    let common_args = CommonArgs::parse(&args, 3)?;
    let use_shm = common_args.payload_mode == PayloadMode::Shm;
    let session =
        map_zenoh(zenoh::open(zenoh_client_config(&common_args.endpoint, use_shm)?).wait())?;
    let subscriber = map_zenoh(session.declare_subscriber(KEY_EXPR).wait())?;

    let mut latencies = Vec::with_capacity(config.number_of_samples);
    while latencies.len() < config.number_of_samples {
        let sample = map_zenoh(subscriber.recv())?;
        let delivered_through_shm = !use_shm || sample.payload().as_shm().is_some();
        let payload = sample.payload().to_bytes();
        let timestamp = decode_payload_timestamp(&payload, common_args.codec)?;
        let received_at = rust_zenoh::utils::now();
        latencies.push(received_at - timestamp);
        if !delivered_through_shm {
            bail!("zenoh payload was not delivered through shared memory");
        }
    }

    let result_folder = format!(
        "{}/latencies/{}_bytes_{}_ms_{}_samples",
        results_file_path(&common_args.output_dir_name),
        config.payload_size_bytes,
        config.publish_period_ms,
        config.number_of_samples
    );
    fs::create_dir_all(&result_folder)?;

    let result_file = format!("{}/{}_subscriber.txt", result_folder, instance_id);
    fs::write(
        result_file,
        rust_zenoh::utils::make_benchmark_result(&config, latencies),
    )?;

    Ok(())
}
