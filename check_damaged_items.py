import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from common.config import Config
from common.logger import setup_logger
from common.emby_client import EmbyClient

log = setup_logger('check_damaged_items')

# 用户指定的环境变量默认参数
DEFAULT_ENV = {
    'EMBY_SERVER': 'http://192.168.50.100:8096',
    'EMBY_HOST': 'http://192.168.50.100:8096',
    'API_KEY': '4b17bc5173e648a7baf560b84f98a363',
    'EMBY_API_KEY': '4b17bc5173e648a7baf560b84f98a363',
    'USER_ID': '4e8374bbd9b7443b8ad4481615a8c395',
    'EMBY_USER_ID': '4e8374bbd9b7443b8ad4481615a8c395',
    'LIB_NAME': 'Movies - 动画,Movies - 外语,Movies - 国语,IMDB&Douban TOP500,Anime - 完结,Anime - 追番,Series - 完结,Series - 连载,Documentary',
}

def check_damaged_items():
    cfg = Config()
    cfg.load_script_config(DEFAULT_ENV)
    client = EmbyClient(cfg)

    if not cfg.LIB_NAME:
        log.error("❌ LIB_NAME 未配置！")
        return

    libs = cfg.LIB_NAME.split(',')
    damaged_items = []
    total_scanned = 0

    log.info("🔍 ══════════════════ [开始检测受影响的元数据缺失条目] ══════════════════")

    for lib_name in libs:
        lib_name = lib_name.strip()
        if not lib_name:
            continue

        parent_id = client.get_library_id(lib_name)
        if not parent_id:
            log.warning(f"⚠️  [媒体库未找到] {lib_name}")
            continue

        items = client.get_lib_items(parent_id)
        log.info(f"📁 [扫描媒体库: {lib_name}] 共 {len(items)} 个条目，开始排查...")

        for item in items:
            total_scanned += 1
            item_id = item['Id']
            item_name = item.get('Name', '未知名称')

            # 抓取包含所有真实字段的原始全量 Item
            full_item = client.get_item(item_id)
            if not full_item:
                continue

            # 检测标准：如果 Overview (简介) 为空 且 缺乏 ProductionYear (年份) 或 PremiereDate (上映时间)
            has_overview = bool(full_item.get('Overview'))
            has_year = bool(full_item.get('ProductionYear'))
            has_premiere = bool(full_item.get('PremiereDate'))

            # 如果关键字段丢失，记为被影响条目
            if not has_overview and not has_year and not has_premiere:
                info = {
                    'lib': lib_name,
                    'id': item_id,
                    'name': item_name,
                    'type': full_item.get('Type', 'Unknown'),
                    'keys_count': len(full_item.keys())
                }
                damaged_items.append(info)
                log.info(f"🚨 [检测到元数据缺失条目] 《{item_name}》 (ID: {item_id}) | 媒体库: {lib_name}")

    log.info("📊 ══════════════════ [检测完成汇总报告] ══════════════════")
    log.info(f"总计扫描条目: {total_scanned} 个")
    log.info(f"受影响/缺少关键元数据条目: {len(damaged_items)} 个")

    if damaged_items:
        print("\n" + "="*80)
        print(f"受影响的条目列表汇总 (共 {len(damaged_items)} 个)：")
        print("="*80)
        for idx, item in enumerate(damaged_items, 1):
            print(f"{idx:3d}. [媒体库: {item['lib']}] 《{item['name']}》 | ItemId: {item['id']} | 类型: {item['type']}")
        print("="*80 + "\n")
    else:
        log.info("🎉 恭喜！未检测到任何受影响的元数据缺失条目！")

if __name__ == '__main__':
    check_damaged_items()
