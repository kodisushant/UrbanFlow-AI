"""
UrbanFlow AI - Model Benchmark Utility (Member 2)
Measures real FPS and peak RAM for YOLOv8n across available runtime backends:
- PyTorch (CPU)
- ONNX Runtime
- OpenVINO (Intel CPU optimized)

Persists benchmark results and determines the fastest runtime engine by default.
Does not rely on hardcoded FPS claims.
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Optional


def measure_memory_mb() -> float:
    """Returns current process RSS memory usage in Megabytes."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024.0 * 1024.0)
    except Exception:
        return 0.0


def benchmark_model(
    model_obj_or_path: Any,
    imgsz: int = 640,
    iterations: int = 50,
    warmup: int = 10
) -> Dict[str, float]:
    """
    Executes warmup and timing loop on dummy image tensor or numpy array.
    Returns: {"fps": float, "mean_latency_ms": float, "peak_ram_mb": float}
    """
    import numpy as np

    dummy_frame = np.random.randint(0, 255, (imgsz, imgsz, 3), dtype=np.uint8)
    initial_mem = measure_memory_mb()
    peak_mem = initial_mem

    # Warmup
    for _ in range(warmup):
        _ = model_obj_or_path.predict(source=dummy_frame, conf=0.25, verbose=False)
        peak_mem = max(peak_mem, measure_memory_mb())

    # Timing loop
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        _ = model_obj_or_path.predict(source=dummy_frame, conf=0.25, verbose=False)
        dur = time.perf_counter() - start
        latencies.append(dur)
        peak_mem = max(peak_mem, measure_memory_mb())

    avg_latency = sum(latencies) / len(latencies)
    fps = 1.0 / avg_latency if avg_latency > 0 else 0.0

    return {
        "fps": round(fps, 2),
        "mean_latency_ms": round(avg_latency * 1000.0, 2),
        "peak_ram_mb": round(peak_mem, 1)
    }


def run_benchmarks(
    model_name: str = "yolov8n.pt",
    iterations: int = 40,
    results_path: str = "assets/benchmark_results.json"
) -> Dict[str, Any]:
    """
    Evaluates PyTorch CPU and attempts exports to ONNX and OpenVINO.
    """
    results: Dict[str, Any] = {
        "model_name": model_name,
        "backends": {},
        "selected_best_format": "pytorch"
    }

    try:
        from ultralytics import YOLO
    except ImportError:
        print("[Benchmark] Ultralytics is not installed. Run 'pip install -r requirements-vision.txt'")
        return results

    # 1. Benchmark PyTorch CPU
    print(f"[Benchmark] Evaluating PyTorch CPU with {model_name}...")
    try:
        pt_model = YOLO(model_name)
        pt_metrics = benchmark_model(pt_model, iterations=iterations)
        results["backends"]["pytorch"] = {
            "format": "pt",
            "device": "cpu",
            **pt_metrics
        }
        print(f"  PyTorch CPU: {pt_metrics['fps']} FPS, {pt_metrics['mean_latency_ms']} ms/frame, Peak RAM: {pt_metrics['peak_ram_mb']} MB")
    except Exception as e:
        print(f"  PyTorch CPU benchmark failed: {e}")

    # 2. Benchmark ONNX Runtime (if export succeeds)
    print("[Benchmark] Testing ONNX export and inference...")
    try:
        onnx_path = pt_model.export(format="onnx", imgsz=640, verbose=False)
        onnx_model = YOLO(onnx_path)
        onnx_metrics = benchmark_model(onnx_model, iterations=iterations)
        results["backends"]["onnx"] = {
            "format": "onnx",
            "path": str(onnx_path),
            **onnx_metrics
        }
        print(f"  ONNX Runtime: {onnx_metrics['fps']} FPS, {onnx_metrics['mean_latency_ms']} ms/frame, Peak RAM: {onnx_metrics['peak_ram_mb']} MB")
    except Exception as e:
        print(f"  ONNX export/benchmark skipped or failed: {e}")

    # 3. Benchmark OpenVINO (Intel CPU acceleration)
    print("[Benchmark] Testing OpenVINO export and inference...")
    try:
        ov_path = pt_model.export(format="openvino", imgsz=640, verbose=False)
        ov_model = YOLO(ov_path)
        ov_metrics = benchmark_model(ov_model, iterations=iterations)
        results["backends"]["openvino"] = {
            "format": "openvino",
            "path": str(ov_path),
            **ov_metrics
        }
        print(f"  OpenVINO: {ov_metrics['fps']} FPS, {ov_metrics['mean_latency_ms']} ms/frame, Peak RAM: {ov_metrics['peak_ram_mb']} MB")
    except Exception as e:
        print(f"  OpenVINO export/benchmark skipped or failed: {e}")

    # Determine fastest backend
    best_format = "pytorch"
    best_fps = 0.0
    for name, data in results["backends"].items():
        if data.get("fps", 0.0) > best_fps:
            best_fps = data["fps"]
            best_format = name

    results["selected_best_format"] = best_format
    print(f"\n[Benchmark Complete] Best runtime backend selected: '{best_format}' ({best_fps} FPS)")

    # Save results
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


def get_default_model_format(results_path: str = "assets/benchmark_results.json") -> str:
    """Reads cached benchmark result or falls back to 'pytorch'."""
    if os.path.exists(results_path):
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("selected_best_format", "pytorch")
        except Exception:
            pass
    return "pytorch"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UrbanFlow AI Vision Model Benchmark")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Base model weights")
    parser.add_argument("--iterations", type=int, default=30, help="Number of benchmark iterations")
    parser.add_argument("--out", type=str, default="assets/benchmark_results.json", help="Output path for benchmark results")
    args = parser.parse_args()

    run_benchmarks(model_name=args.model, iterations=args.iterations, results_path=args.out)
