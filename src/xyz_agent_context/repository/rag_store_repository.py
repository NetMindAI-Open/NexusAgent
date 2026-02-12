"""
@file_name: rag_store_repository.py
@author: NetMind.AI
@date: 2025-12-02
@description: RAG Store Repository - Data access layer for RAG Store metadata

Responsibilities:
- CRUD operations for RAG Store
- Keyword management
- Uploaded file records
"""

import json
from typing import List, Dict, Any, Optional
from loguru import logger

from .base import BaseRepository
from xyz_agent_context.utils import utc_now
from xyz_agent_context.schema import RAGStoreModel


class RAGStoreRepository(BaseRepository[RAGStoreModel]):
    """
    RAG Store Repository implementation

    Usage example:
        repo = RAGStoreRepository(db_client)

        # Get or create a store
        store = await repo.get_or_create_store(agent_id, user_id, store_name)

        # Add a file record
        await repo.add_uploaded_file(agent_id, user_id, "document.pdf")

        # Update keywords
        await repo.update_keywords(agent_id, user_id, ["AI", "machine learning"])
    """

    table_name = "instance_rag_store"
    id_field = "id"

    _json_fields = {"keywords", "uploaded_files"}

    # =========================================================================
    # Instance-based query methods (added 2025-12-24)
    # =========================================================================

    async def get_store_by_instance(
        self,
        instance_id: str
    ) -> Optional[RAGStoreModel]:
        """
        Get a RAG Store record by instance_id

        Args:
            instance_id: Instance ID (GeminiRAGModule's instance_id)

        Returns:
            RAGStoreModel or None
        """
        logger.debug(f"    → RAGStoreRepository.get_store_by_instance({instance_id})")
        return await self.find_one({"instance_id": instance_id})

    async def create_store_for_instance(
        self,
        instance_id: str,
        agent_id: str,
        user_id: str,
        store_name: str
    ) -> int:
        """
        Create a RAG Store record for an Instance

        Args:
            instance_id: Instance ID (GeminiRAGModule's instance_id)
            agent_id: Agent ID
            user_id: User ID
            store_name: Gemini Store name

        Returns:
            Inserted record ID
        """
        logger.debug(f"    → RAGStoreRepository.create_store_for_instance({instance_id})")

        display_name = f"instance_{instance_id}"
        now = utc_now()

        store = RAGStoreModel(
            display_name=display_name,
            store_name=store_name,
            agent_id=agent_id,
            user_id=user_id,
            instance_id=instance_id,
            keywords=[],
            uploaded_files=[],
            file_count=0,
            created_at=now,
            updated_at=now,
        )

        return await self.insert(store)

    async def get_or_create_store_for_instance(
        self,
        instance_id: str,
        agent_id: str,
        user_id: str,
        store_name: str
    ) -> RAGStoreModel:
        """
        Get or create a RAG Store record for an Instance

        Args:
            instance_id: Instance ID
            agent_id: Agent ID
            user_id: User ID
            store_name: Gemini Store name

        Returns:
            RAGStoreModel
        """
        logger.debug(f"    → RAGStoreRepository.get_or_create_store_for_instance({instance_id})")

        store = await self.get_store_by_instance(instance_id)
        if store:
            # If store_name has changed, update it
            if store.store_name != store_name:
                await self.update_store_by_instance(instance_id, {"store_name": store_name})
                store.store_name = store_name
            return store

        # Create new record
        await self.create_store_for_instance(instance_id, agent_id, user_id, store_name)
        return await self.get_store_by_instance(instance_id)

    async def update_store_by_instance(
        self,
        instance_id: str,
        updates: Dict[str, Any]
    ) -> int:
        """
        Update a RAG Store record by instance_id

        Args:
            instance_id: Instance ID
            updates: Fields to update

        Returns:
            Number of affected rows
        """
        logger.debug(f"    → RAGStoreRepository.update_store_by_instance({instance_id})")

        updates["updated_at"] = utc_now()

        # Serialize JSON fields
        for field in self._json_fields:
            if field in updates and not isinstance(updates[field], str):
                updates[field] = json.dumps(updates[field], ensure_ascii=False)

        query = f"""
            UPDATE {self.table_name}
            SET {', '.join(f'`{k}` = %s' for k in updates.keys())}
            WHERE instance_id = %s
        """

        params = list(updates.values()) + [instance_id]
        result = await self._db.execute(query, params=tuple(params), fetch=False)
        return result if isinstance(result, int) else 0

    async def add_uploaded_file_by_instance(
        self,
        instance_id: str,
        filename: str
    ) -> int:
        """
        Add an uploaded file record by instance_id

        Args:
            instance_id: Instance ID
            filename: File name

        Returns:
            Number of affected rows
        """
        logger.debug(f"    → RAGStoreRepository.add_uploaded_file_by_instance({instance_id}, {filename})")

        store = await self.get_store_by_instance(instance_id)
        if not store:
            logger.warning(f"RAG store not found for instance_id={instance_id}")
            return 0

        # Update file list
        uploaded_files = store.uploaded_files or []
        if filename not in uploaded_files:
            uploaded_files.append(filename)

        return await self.update_store_by_instance(
            instance_id=instance_id,
            updates={
                "uploaded_files": uploaded_files,
                "file_count": len(uploaded_files),
            }
        )

    async def update_keywords_by_instance(
        self,
        instance_id: str,
        keywords: List[str]
    ) -> int:
        """
        Update keyword list by instance_id

        Args:
            instance_id: Instance ID
            keywords: Keyword list

        Returns:
            Number of affected rows
        """
        logger.debug(f"    → RAGStoreRepository.update_keywords_by_instance({instance_id})")

        return await self.update_store_by_instance(
            instance_id=instance_id,
            updates={"keywords": keywords}
        )

    async def get_keywords_by_instance(
        self,
        instance_id: str,
        score: bool = False
    ) -> List[str]:
        """
        Get keyword list by instance_id

        Args:
            instance_id: Instance ID
            score: Whether to return keywords with scores

        Returns:
            Keyword list
        """
        logger.debug(f"    → RAGStoreRepository.get_keywords_by_instance({instance_id})")

        store = await self.get_store_by_instance(instance_id)
        if not store:
            return []

        file_count = store.file_count or 0
        keywords_raw = store.keywords
        keywords = []

        if keywords_raw:
            for keyword in keywords_raw:
                if isinstance(keyword, str):
                    keywords.append(keyword)
                elif isinstance(keyword, dict):
                    if not score:
                        keywords.append(keyword["keyword"])
                    else:
                        return keywords_raw
        else:
            return []

        return keywords[:min(file_count * 10, len(keywords))]

    # =========================================================================
    # Convenience query methods
    # =========================================================================

    async def get_store(
        self,
        agent_id: str,
        user_id: str
    ) -> Optional[RAGStoreModel]:
        """Get a RAG Store record"""
        logger.debug(f"    → RAGStoreRepository.get_store({agent_id}, {user_id})")
        display_name = f"agent_{agent_id}"
        return await self.find_one({"display_name": display_name})

    async def get_store_by_display_name(
        self,
        display_name: str
    ) -> Optional[RAGStoreModel]:
        """Get a store by display_name"""
        logger.debug(f"    → RAGStoreRepository.get_store_by_display_name({display_name})")
        return await self.find_one({"display_name": display_name})

    async def create_store(
        self,
        agent_id: str,
        user_id: str,
        store_name: str
    ) -> int:
        """Create a RAG Store record"""
        logger.debug(f"    → RAGStoreRepository.create_store({agent_id}, {user_id})")

        display_name = f"agent_{agent_id}"
        now = utc_now()

        store = RAGStoreModel(
            display_name=display_name,
            store_name=store_name,
            agent_id=agent_id,
            user_id=user_id,
            keywords=[],
            uploaded_files=[],
            file_count=0,
            created_at=now,
            updated_at=now,
        )

        return await self.insert(store)

    async def get_or_create_store(
        self,
        agent_id: str,
        user_id: str,
        store_name: str
    ) -> RAGStoreModel:
        """Get or create a RAG Store record"""
        logger.debug(f"    → RAGStoreRepository.get_or_create_store({agent_id}, {user_id})")

        store = await self.get_store(agent_id, user_id)
        if store:
            # If store_name has changed, update it
            if store.store_name != store_name:
                await self.update_store(agent_id, user_id, {"store_name": store_name})
                store.store_name = store_name
            return store

        # Create new record
        await self.create_store(agent_id, user_id, store_name)
        return await self.get_store(agent_id, user_id)

    async def update_store(
        self,
        agent_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> int:
        """Update a RAG Store record"""
        logger.debug(f"    → RAGStoreRepository.update_store({agent_id}, {user_id})")

        display_name = f"agent_{agent_id}"
        updates["updated_at"] = utc_now()

        # Serialize JSON fields
        for field in self._json_fields:
            if field in updates and not isinstance(updates[field], str):
                updates[field] = json.dumps(updates[field], ensure_ascii=False)

        query = f"""
            UPDATE {self.table_name}
            SET {', '.join(f'`{k}` = %s' for k in updates.keys())}
            WHERE display_name = %s
        """

        params = list(updates.values()) + [display_name]
        result = await self._db.execute(query, params=tuple(params), fetch=False)
        return result if isinstance(result, int) else 0

    async def add_uploaded_file(
        self,
        agent_id: str,
        user_id: str,
        filename: str
    ) -> int:
        """Add an uploaded file record"""
        logger.debug(f"    → RAGStoreRepository.add_uploaded_file({agent_id}, {user_id}, {filename})")

        store = await self.get_store(agent_id, user_id)
        if not store:
            logger.warning(f"RAG store not found for {agent_id}/{user_id}")
            return 0

        # Update file list
        uploaded_files = store.uploaded_files or []
        if filename not in uploaded_files:
            uploaded_files.append(filename)

        return await self.update_store(
            agent_id=agent_id,
            user_id=user_id,
            updates={
                "uploaded_files": uploaded_files,
                "file_count": len(uploaded_files),
            }
        )

    async def update_keywords(
        self,
        agent_id: str,
        user_id: str,
        keywords: List[str]
    ) -> int:
        """Update keyword list"""
        logger.debug(f"    → RAGStoreRepository.update_keywords({agent_id}, {user_id})")

        # Ensure keywords do not exceed 20
        # keywords = keywords[:20]

        return await self.update_store(
            agent_id=agent_id,
            user_id=user_id,
            updates={"keywords": keywords}
        )

    async def get_keywords(
        self,
        agent_id: str,
        user_id: str,
        score:bool=False
    ) -> List[str]:
        """Get keyword list"""
        logger.debug(f"    → RAGStoreRepository.get_keywords({agent_id}, {user_id})")
        file_count = await self.get_file_count(agent_id, user_id)
        store = await self.get_store(agent_id, user_id)
        if not store:  # If store does not exist, return empty list
            return []
        keywords_raw=store.keywords
        keywords=[]
        if keywords_raw: # If keyword list is not empty
            for keyword in keywords_raw:
                if isinstance(keyword, str):
                    keywords.append(keyword)
                elif isinstance(keyword, dict):
                    if not score: # When not calculating score, return keyword directly
                        keywords.append(keyword["keyword"])
                    else:
                        return keywords_raw # When calculating score, return keyword list with scores
        else:
            return []
        return keywords[:min(file_count*10, len(keywords))]

    async def get_file_count(
        self,
        agent_id: str,
        user_id: str
    ) -> int:
        """Get file count"""
        logger.debug(f"    → RAGStoreRepository.get_file_count({agent_id}, {user_id})")
        store = await self.get_store(agent_id, user_id)
        if store:
            return store.file_count
        return 0

    async def delete_store(
        self,
        agent_id: str,
        user_id: str
    ) -> int:
        """Delete a RAG Store record"""
        logger.debug(f"    → RAGStoreRepository.delete_store({agent_id}, {user_id})")

        display_name = f"agent_{agent_id}"
        query = f"DELETE FROM {self.table_name} WHERE display_name = %s"
        result = await self._db.execute(query, params=(display_name,), fetch=False)
        return result if isinstance(result, int) else 0

    def _row_to_entity(self, row: Dict[str, Any]) -> RAGStoreModel:
        """Convert a database row to a RAGStoreModel object"""
        keywords = self._parse_json_field(row.get("keywords"), [])
        uploaded_files = self._parse_json_field(row.get("uploaded_files"), [])

        return RAGStoreModel(
            id=row.get("id"),
            display_name=row["display_name"],
            store_name=row["store_name"],
            agent_id=row["agent_id"],
            user_id=row["user_id"],
            instance_id=row.get("instance_id"),
            keywords=keywords,
            uploaded_files=uploaded_files,
            file_count=row.get("file_count", 0),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _entity_to_row(self, entity: RAGStoreModel) -> Dict[str, Any]:
        """Convert a RAGStoreModel object to a database row"""
        return {
            "display_name": entity.display_name,
            "store_name": entity.store_name,
            "agent_id": entity.agent_id,
            "user_id": entity.user_id,
            "instance_id": entity.instance_id,
            "keywords": json.dumps(entity.keywords, ensure_ascii=False),
            "uploaded_files": json.dumps(entity.uploaded_files, ensure_ascii=False),
            "file_count": entity.file_count,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }

    @staticmethod
    def _parse_json_field(value: Any, default: Any) -> Any:
        """Parse a JSON field"""
        if value is None:
            return default
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return default
        return value
