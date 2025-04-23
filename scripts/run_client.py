#!/usr/bin/env python3
"""
NexTalk 客户端运行脚本

该脚本启动NexTalk的语音识别客户端，执行nextalk_client.main模块。
"""

import subprocess
import sys
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)


def main():
    """
    启动NexTalk客户端
    
    使用subprocess执行nextalk_client.main模块，启动客户端应用程序。
    """
    logger.info("正在启动NexTalk客户端...")
    
    try:
        # 使用Python解释器执行nextalk_client.main模块
        subprocess.run(
            [sys.executable, "-m", "nextalk_client.main"],
            check=True,
            env=os.environ
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"客户端执行失败，返回码: {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        logger.info("客户端被用户中断")
    except Exception as e:
        logger.exception(f"启动客户端时发生错误: {e}")
        sys.exit(1)
    else:
        logger.info("客户端已正常退出")


if __name__ == "__main__":
    main() 