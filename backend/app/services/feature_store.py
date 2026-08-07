"""
RailMind Redis Real-Time Feature Store.
Caches per-train node feature vectors in Redis Hashes with TTL expiry.
Provides sub-5ms p99 pipeline batch reads for PyTorch Geometric GNN inference.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import torch

logger = logging.getLogger(__name__)

try:
    import redis.asyncio as aioredis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


class TrainFeatureStore:
    """
    Redis Feature Store for Train State & GNN Node Feature Vectors.
    Feature schema per train (8 dims):
      [delay_min, speed_kmh, distance_to_next_km, platform_occupancy,
       weather_severity, time_of_day_norm, priority_class, track_congestion]
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0", ttl_sec: int = 60):
        self.redis_url = redis_url
        self.ttl_sec = ttl_sec
        self._redis = None
        self._local_cache: Dict[str, List[float]] = {}  # Fallback in-memory dict

    async def connect(self):
        """Connects to Redis server."""
        if HAS_REDIS and not self._redis:
            try:
                self._redis = aioredis.from_url(self.redis_url, decode_responses=True)
                await self._redis.ping()
                logger.info("TrainFeatureStore connected to Redis.")
            except Exception as e:
                logger.warning(f"Redis Feature Store unavailable ({e}). Using in-memory fallback store.")
                self._redis = None

    async def close(self):
        """Closes Redis connection."""
        if self._redis:
            await self._redis.close()

    async def set_train_features(self, train_id: str, feature_vector: List[float]) -> bool:
        """
        Stores train feature vector in Redis Hash with TTL expiry.
        """
        if len(feature_vector) != 8:
            raise ValueError(f"Feature vector must have length 8, got {len(feature_vector)}")

        self._local_cache[train_id] = feature_vector

        if self._redis:
            try:
                key = f"train_features:{train_id}"
                mapping = {"vec": json.dumps(feature_vector)}
                await self._redis.hset(key, mapping=mapping)
                await self._redis.expire(key, self.ttl_sec)
                return True
            except Exception as e:
                logger.error(f"Failed to set features in Redis: {e}")

        return False

    async def get_batch_features(self, train_ids: List[str]) -> torch.Tensor:
        """
        Pipeline batch read of feature vectors for all requested train_ids.
        Returns PyTorch float32 Tensor of shape [N, 8] for direct GNN input.
        """
        features_list: List[List[float]] = []

        if self._redis:
            try:
                pipe = self._redis.pipeline()
                for tid in train_ids:
                    pipe.hget(f"train_features:{tid}", "vec")
                raw_results = await pipe.execute()

                for i, raw in enumerate(raw_results):
                    tid = train_ids[i]
                    if raw:
                        vec = json.loads(raw)
                    else:
                        vec = self._local_cache.get(tid, [0.0] * 8)
                    features_list.append(vec)
            except Exception as e:
                logger.error(f"Redis pipeline error ({e}). Using local fallback.")
                features_list = [self._local_cache.get(tid, [0.0] * 8) for tid in train_ids]
        else:
            features_list = [self._local_cache.get(tid, [0.0] * 8) for tid in train_ids]

        if not features_list:
            return torch.zeros((0, 8), dtype=torch.float32)

        return torch.tensor(features_list, dtype=torch.float32)
