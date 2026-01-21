@0xdbbfb3d09f1e0526;

using Cxx = import "/capnp/c++.capnp";
$Cxx.namespace("tb_proto");

struct Payload {
  timeStampNs @0 :Int64;
  data @1 :Data;
  messageNumber @2 :UInt32;
}