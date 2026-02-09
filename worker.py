"""
Vast.ai PyWorker for Hindi ASR serverless endpoint.
Proxies HTTP requests to ASR model server, reports metrics for autoscaling.
"""
import os
import struct

from vastai import (
    Worker,
    WorkerConfig,
    HandlerConfig,
    BenchmarkConfig,
    LogActionConfig,
)

MODEL_SERVER_URL = "http://127.0.0.1"
MODEL_SERVER_PORT = int(os.environ.get("SERVER_PORT", "8000"))
MODEL_LOG_FILE = os.environ.get("MODEL_LOG", "/var/log/model/server.log")


def asr_workload_calculator(payload):
    """Estimate workload from request. Returns estimated audio seconds."""
    return 10.0


def asr_benchmark_generator():
    """Generate benchmark payload: 1s silence WAV."""
    sample_rate = 16000
    num_samples = int(sample_rate * 1.0)
    silence = b'\x00\x00' * num_samples
    data_size = len(silence)
    wav_header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + data_size, b'WAVE', b'fmt ', 16,
        1, 1, sample_rate, sample_rate * 2, 2, 16,
        b'data', data_size,
    )
    return {
        "file": ("benchmark.wav", wav_header + silence, "audio/wav"),
        "language": "hi",
    }


worker_config = WorkerConfig(
    model_server_url=MODEL_SERVER_URL,
    model_server_port=MODEL_SERVER_PORT,
    model_log_file=MODEL_LOG_FILE,
    handlers=[
        HandlerConfig(
            route="/v1/audio/transcriptions",
            allow_parallel_requests=True,
            max_queue_time=120.0,
            workload_calculator=asr_workload_calculator,
            benchmark_config=BenchmarkConfig(
                generator=asr_benchmark_generator,
                runs=4,
                concurrency=1,
            ),
        ),
        HandlerConfig(
            route="/v1/audio/transcriptions/stream",
            allow_parallel_requests=True,
            max_queue_time=60.0,
            workload_calculator=asr_workload_calculator,
        ),
        HandlerConfig(
            route="/health",
            allow_parallel_requests=True,
            max_queue_time=5.0,
            workload_calculator=lambda payload: 0.0,
        ),
    ],
    log_action_config=LogActionConfig(
        on_load=["Application startup complete."],
        on_error=[
            "Traceback (most recent call last):",
            "RuntimeError:",
            "CUDA out of memory",
        ],
        on_info=[
            "Warming up GPU",
            "Pipeline loaded",
        ],
    ),
)

Worker(worker_config).run()
