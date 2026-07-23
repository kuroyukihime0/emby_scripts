import requests
import logging
from common.config import Config
from common.logger import setup_logger

logger = setup_logger('emby_client')

class EmbyClient:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.session = requests.Session()

    @property
    def headers(self):
        return {
            'X-Emby-Token': self.config.API_KEY,
            'Content-Type': 'application/json',
        }

    def get_library_id(self, lib_name: str) -> str:
        """
        根据媒体库名称获取对应的 ItemId
        """
        if not lib_name:
            return None
        url = f"{self.config.EMBY_SERVER.rstrip('/')}/emby/Library/VirtualFolders"
        try:
            res = self.session.get(url, headers=self.headers)
            res.raise_for_status()
            folders = res.json()
            lib_ids = [i['ItemId'] for i in folders if i.get('Name') == lib_name]
            if not lib_ids:
                logger.error(f"Library: '{lib_name}' not exists on server.")
                return None
            return lib_ids[0]
        except Exception as e:
            logger.error(f"Failed to fetch library ID for '{lib_name}': {e}")
            return None

    def get_lib_items(self, parent_id: str, fields: str = "ProviderIds,SortName,Tags,TagItems,Genres,GenreItems,LockedFields") -> list:
        """
        递归获取 parent_id 目录下的所有非文件夹子项，并一次性拉取全量属性字段（零重复 GET 请求）
        """
        url = f"{self.config.EMBY_SERVER.rstrip('/')}/emby/Items"
        params = {
            'ParentId': parent_id,
            'fields': fields
        }
        try:
            res = self.session.get(url, headers=self.headers, params=params)
            res.raise_for_status()
            items = res.json().get('Items', [])
            
            items_folder = [item for item in items if item.get("Type") == "Folder"]
            result_items = [item for item in items if item.get("Type") != "Folder"]

            for folder in items_folder:
                result_items.extend(self.get_lib_items(folder['Id'], fields=fields))

            return result_items
        except Exception as e:
            logger.error(f"Failed to get lib items for parent_id '{parent_id}': {e}")
            return []

    def get_item(self, item_id: str) -> dict:
        """
        获取特定 Item 的详细配置
        """
        url = f"{self.config.EMBY_SERVER.rstrip('/')}/emby/Users/{self.config.USER_ID}/Items/{item_id}?Fields=ChannelMappingInfo"
        try:
            res = self.session.get(url, headers=self.headers)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            logger.error(f"Failed to get item '{item_id}': {e}")
            return None

    def update_item(self, item_id: str, item_data: dict) -> bool:
        """
        更新特定 Item 节点数据
        """
        if self.config.DRY_RUN:
            logger.info(f"[DRY_RUN] Would update item {item_id}")
            return True

        url = f"{self.config.EMBY_SERVER.rstrip('/')}/emby/Items/{item_id}?reqformat=json"
        try:
            res = self.session.post(url, json=item_data, headers=self.headers)
            if res.status_code in [200, 204]:
                return True
            else:
                logger.error(f"Failed to update item {item_id}: {res.status_code} {res.content}")
                return False
        except Exception as e:
            logger.error(f"Exception updating item {item_id}: {e}")
            return False
