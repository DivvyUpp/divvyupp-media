"""Copy the Kokoro ONNX model with its per-phoneme duration tensor added as an output named "duration".
kokoro-onnx then reports phoneme timings (Kokoro.create_timed), which story Reels use for lip-sync.
Usage: python3 pipeline/expose_durations.py kokoro.onnx kokoro-timed.onnx"""
import sys
import onnx
from onnx import helper, TensorProto

SRC = "/encoder/Cast_output_0"   # rounded, clipped durations (frames per token), just before the length expansion
m = onnx.load(sys.argv[1])
assert any(SRC in n.output for n in m.graph.node), "duration tensor not found; the model export changed"
m.graph.node.append(helper.make_node("Identity", [SRC], ["duration"]))
m.graph.output.append(helper.make_tensor_value_info("duration", TensorProto.INT64, None))
onnx.save(m, sys.argv[2])
print("wrote", sys.argv[2])
