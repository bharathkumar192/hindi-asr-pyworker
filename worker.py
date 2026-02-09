"""Vast.ai PyWorker for Hindi ASR serverless."""
import os
import struct
import base64

from vastai import (
    Worker,
    WorkerConfig,
    HandlerConfig,
    BenchmarkConfig,
    LogActionConfig,
)

MODEL_SERVER_URL = "http://127.0.0.1"
MODEL_SERVER_PORT = int(os.environ.get("SERVER_PORT", "18000"))
MODEL_LOG_FILE = os.environ.get("MODEL_LOG", "/var/log/model/server.log")

def asr_workload_calculator(payload):
    return 10.0

def asr_benchmark_generator():
    """Generate benchmark: 1s silence WAV as base64 JSON (not multipart)."""
    sr = 16000
    n = sr * 1
    silence = b'\x00\x00' * n
    ds = len(silence)
    hdr = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36+ds, b'WAVE', b'fmt ', 16, 1, 1, sr, sr*2, 2, 16, b'data', ds)
    wav_bytes = hdr + silence
    return {
        "audio_base64": base64.b64encode(wav_bytes).decode("ascii"),
        "language": "hi",
    }

worker_config = WorkerConfig(
    model_server_url=MODEL_SERVER_URL,
    model_server_port=MODEL_SERVER_PORT,
    model_log_file=MODEL_LOG_FILE,
    handlers=[
        HandlerConfig(
            route="/v1/audio/transcriptions/json",
            allow_parallel_requests=True,
            max_queue_time=120.0,
            workload_calculator=asr_workload_calculator,
            benchmark_config=BenchmarkConfig(generator=asr_benchmark_generator, runs=4, concurrency=1),
        ),
        HandlerConfig(route="/v1/audio/transcriptions", allow_parallel_requests=True,
                      max_queue_time=120.0, workload_calculator=asr_workload_calculator),
        HandlerConfig(route="/health", allow_parallel_requests=True,
                      max_queue_time=5.0, workload_calculator=lambda p: 0.0),
    ],
    log_action_config=LogActionConfig(
        on_load=["Application startup complete."],
        on_error=["Traceback (most recent call last):", "RuntimeError:", "CUDA out of memory"],
        on_info=["Warming up GPU", "Pipeline loaded"],
    ),
)

Worker(worker_config).run()
