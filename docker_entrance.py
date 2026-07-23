import os
import sys
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.config import Config
from common.logger import setup_logger
from common.pipeline import run_pipeline
from common.web_server import start_web_server

log = setup_logger('docker_entrance')

def work_loop():
    cfg = Config()
    cfg.IS_DOCKER = True

    # 基础配置校验
    assert cfg.EMBY_SERVER, "❌ EMBY_HOST / EMBY_SERVER 环境变量未配置！"
    assert cfg.API_KEY, "❌ EMBY_API_KEY 环境变量未配置！"
    assert cfg.USER_ID, "❌ EMBY_USER_ID 环境变量未配置！"
    assert cfg.LIB_NAME, "❌ LIB_NAME 环境变量未配置！"

    log.info("🚀 启动 Emby Scripts Docker 调度入口 (Pipeline 流水线模式)...")
    log.info(f"⚙️ 配置 - 服务器: {cfg.EMBY_SERVER}, 媒体库: {cfg.LIB_NAME}, 预览模式(DryRun): {cfg.DRY_RUN}")

    # 若开启 Web 控制台，则在后台线程启动 Web 服务
    if cfg.ENABLE_WEB:
        web_thread = threading.Thread(target=start_web_server, args=(cfg.WEB_PORT,), daemon=True)
        web_thread.start()
        log.info(f"🌐 Web 管理控制台已启用，可通过 http://<HOST>:{cfg.WEB_PORT} 访问")
    else:
        log.info("🔒 Web 管理控制台当前处于关闭状态 (ENABLE_WEB=false)")

    while True:
        try:
            run_pipeline(cfg)
        except Exception as ex:
            log.error(f"❌ 调度循环捕获异常: {ex}", exc_info=True)

        interval_hours = cfg.RUN_INTERVAL_HOURS if cfg.RUN_INTERVAL_HOURS > 0 else 24
        log.info(f"⌛ 本轮任务完成，休眠 {interval_hours} 小时后自动进行下一轮调度...")
        time.sleep(interval_hours * 3600)

if __name__ == "__main__":
    work_loop()
