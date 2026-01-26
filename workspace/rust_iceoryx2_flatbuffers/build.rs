use std::{fs, path::PathBuf};

fn main() {
    println!("cargo:rerun-if-changed=src/Payload.fbs");

    let out_dir = PathBuf::from(std::env::var("OUT_DIR").unwrap());

    let status = std::process::Command::new("flatc")
        .args([
            "--rust",
            "--gen-mutable",
            "--gen-object-api",
            "-o",
            out_dir.to_str().unwrap(),
            "src/Payload.fbs",
        ])
        .status()
        .expect("Failed to execute flatc");

    assert!(status.success(), "flatc compilation failed");

    let generated = out_dir.join("Payload_generated.rs");
    let renamed = out_dir.join("rust_iceoryx2_flatbuffers_payload.rs");
    fs::rename(&generated, &renamed).expect("Failed to rename generated file");

    let content = fs::read_to_string(&renamed).expect("Failed to read generated file");
    let patched = content
        .replace("alloc::vec::Vec", "::std::vec::Vec")
        .replace("::alloc::vec::Vec", "::std::vec::Vec");
    fs::write(&renamed, patched).expect("Failed to patch generated file");
}
