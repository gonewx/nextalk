#!/usr/bin/env python
"""
NexTalk 性能基准测试脚本
用于测试和优化系统性能
"""

import time
import asyncio
import statistics
import psutil
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
import argparse

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from nextalk.audio.capture import AudioCaptureManager
from nextalk.network.ws_client import WebSocketClient
from nextalk.input.hotkey import HotkeyManager
from nextalk.output.text_injector import TextInjector
from nextalk.core.controller import MainController


class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self):
        self.results = {}
        self.process = psutil.Process()
        
    def measure_memory(self) -> float:
        """测量内存使用（MB）"""
        return self.process.memory_info().rss / 1024 / 1024
    
    def measure_cpu(self) -> float:
        """测量 CPU 使用率"""
        return self.process.cpu_percent(interval=1)
    
    async def benchmark_audio_capture(self, duration: int = 10) -> Dict[str, Any]:
        """测试音频采集性能"""
        print(f"测试音频采集 ({duration}秒)...")
        
        capture = AudioCaptureManager()
        samples = []
        memory_before = self.measure_memory()
        
        start_time = time.time()
        capture.start_capture()
        
        while time.time() - start_time < duration:
            await asyncio.sleep(0.1)
            samples.append(self.measure_cpu())
        
        capture.stop_capture()
        memory_after = self.measure_memory()
        
        return {
            "duration": duration,
            "avg_cpu": statistics.mean(samples),
            "max_cpu": max(samples),
            "memory_delta": memory_after - memory_before,
            "latency": capture.get_latency() if hasattr(capture, 'get_latency') else None
        }
    
    async def benchmark_websocket(self, messages: int = 100) -> Dict[str, Any]:
        """测试 WebSocket 性能"""
        print(f"测试 WebSocket 通信 ({messages}条消息)...")
        
        client = WebSocketClient("ws://localhost:10095")
        latencies = []
        
        try:
            await client.connect()
            
            for i in range(messages):
                start = time.time()
                await client.send_message({"test": i})
                # 假设有响应
                await asyncio.sleep(0.01)  # 模拟处理时间
                latencies.append((time.time() - start) * 1000)  # ms
            
            await client.disconnect()
            
        except Exception as e:
            print(f"WebSocket 测试失败: {e}")
            return {"error": str(e)}
        
        return {
            "messages": messages,
            "avg_latency_ms": statistics.mean(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "p95_latency_ms": statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        }
    
    def benchmark_hotkey(self, iterations: int = 1000) -> Dict[str, Any]:
        """测试快捷键响应性能"""
        print(f"测试快捷键响应 ({iterations}次)...")
        
        manager = HotkeyManager()
        response_times = []
        
        for _ in range(iterations):
            start = time.time()
            # 模拟快捷键处理
            manager.process_key_event({'key': 'space', 'modifiers': ['ctrl', 'alt']})
            response_times.append((time.time() - start) * 1000)  # ms
        
        return {
            "iterations": iterations,
            "avg_response_ms": statistics.mean(response_times),
            "min_response_ms": min(response_times),
            "max_response_ms": max(response_times)
        }
    
    def benchmark_text_injection(self, text_length: int = 1000) -> Dict[str, Any]:
        """测试文本注入性能"""
        print(f"测试文本注入 ({text_length}字符)...")
        
        injector = TextInjector()
        test_text = "测试文本" * (text_length // 8)
        
        start = time.time()
        injector.inject_text(test_text)
        injection_time = (time.time() - start) * 1000  # ms
        
        return {
            "text_length": len(test_text),
            "injection_time_ms": injection_time,
            "chars_per_second": len(test_text) / (injection_time / 1000)
        }
    
    async def benchmark_full_pipeline(self, duration: int = 30) -> Dict[str, Any]:
        """测试完整处理流程"""
        print(f"测试完整流程 ({duration}秒)...")
        
        controller = MainController()
        metrics = {
            "cpu_samples": [],
            "memory_samples": [],
            "events_processed": 0
        }
        
        start_time = time.time()
        await controller.start()
        
        while time.time() - start_time < duration:
            metrics["cpu_samples"].append(self.measure_cpu())
            metrics["memory_samples"].append(self.measure_memory())
            metrics["events_processed"] += 1
            await asyncio.sleep(1)
        
        await controller.stop()
        
        return {
            "duration": duration,
            "avg_cpu": statistics.mean(metrics["cpu_samples"]),
            "avg_memory_mb": statistics.mean(metrics["memory_samples"]),
            "peak_memory_mb": max(metrics["memory_samples"]),
            "events_per_second": metrics["events_processed"] / duration
        }
    
    def benchmark_startup(self) -> Dict[str, Any]:
        """测试启动性能"""
        print("测试启动时间...")
        
        start = time.time()
        controller = MainController()
        init_time = time.time() - start
        
        start = time.time()
        asyncio.run(controller.start())
        start_time = time.time() - start
        
        asyncio.run(controller.stop())
        
        return {
            "init_time_ms": init_time * 1000,
            "start_time_ms": start_time * 1000,
            "total_time_ms": (init_time + start_time) * 1000
        }
    
    async def run_all_benchmarks(self) -> Dict[str, Any]:
        """运行所有基准测试"""
        print("=" * 50)
        print("NexTalk 性能基准测试")
        print("=" * 50)
        
        results = {}
        
        # 音频采集测试
        try:
            results["audio_capture"] = await self.benchmark_audio_capture()
        except Exception as e:
            results["audio_capture"] = {"error": str(e)}
        
        # WebSocket 测试
        try:
            results["websocket"] = await self.benchmark_websocket()
        except Exception as e:
            results["websocket"] = {"error": str(e)}
        
        # 快捷键测试
        try:
            results["hotkey"] = self.benchmark_hotkey()
        except Exception as e:
            results["hotkey"] = {"error": str(e)}
        
        # 文本注入测试
        try:
            results["text_injection"] = self.benchmark_text_injection()
        except Exception as e:
            results["text_injection"] = {"error": str(e)}
        
        # 启动时间测试
        try:
            results["startup"] = self.benchmark_startup()
        except Exception as e:
            results["startup"] = {"error": str(e)}
        
        # 完整流程测试
        try:
            results["full_pipeline"] = await self.benchmark_full_pipeline()
        except Exception as e:
            results["full_pipeline"] = {"error": str(e)}
        
        # 系统信息
        results["system_info"] = {
            "cpu_count": psutil.cpu_count(),
            "memory_total_mb": psutil.virtual_memory().total / 1024 / 1024,
            "python_version": sys.version,
            "platform": sys.platform
        }
        
        return results
    
    def print_results(self, results: Dict[str, Any]):
        """打印测试结果"""
        print("\n" + "=" * 50)
        print("测试结果")
        print("=" * 50)
        
        for category, data in results.items():
            print(f"\n[{category}]")
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, float):
                        print(f"  {key}: {value:.2f}")
                    else:
                        print(f"  {key}: {value}")
            else:
                print(f"  {data}")
    
    def save_results(self, results: Dict[str, Any], filename: str):
        """保存测试结果到文件"""
        output_path = Path(filename)
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n结果已保存到: {output_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="NexTalk 性能基准测试")
    parser.add_argument(
        "--output",
        default="benchmark_results.json",
        help="输出文件路径"
    )
    parser.add_argument(
        "--audio-duration",
        type=int,
        default=10,
        help="音频测试时长（秒）"
    )
    parser.add_argument(
        "--ws-messages",
        type=int,
        default=100,
        help="WebSocket 测试消息数"
    )
    parser.add_argument(
        "--full-duration",
        type=int,
        default=30,
        help="完整流程测试时长（秒）"
    )
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark()
    
    try:
        # 运行测试
        results = asyncio.run(benchmark.run_all_benchmarks())
        
        # 打印结果
        benchmark.print_results(results)
        
        # 保存结果
        benchmark.save_results(results, args.output)
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n测试失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())