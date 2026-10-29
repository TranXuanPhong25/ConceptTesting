import unittest
import numpy as np
from .dense import cache_key, cached_vector


class CacheTests(unittest.TestCase):
    def test_identity_and_text_changes_invalidate_key(self):
        self.assertEqual(cache_key("model+cap512", "same"), cache_key("model+cap512", "same"))
        self.assertNotEqual(cache_key("model+cap512", "same"), cache_key("model+cap256", "same"))
        self.assertNotEqual(cache_key("model+cap512", "same"), cache_key("model+cap512", "other"))

    def test_corruption_is_rejected(self):
        good = np.zeros(768, dtype=np.float32)
        good[0] = 1
        np.testing.assert_array_equal(cached_vector(768, good.tobytes()), good)
        for bad in (np.ones(768, dtype=np.float32), np.full(768, np.nan, dtype=np.float32), good[:30]):
            with self.assertRaisesRegex(ValueError, "Invalid cached"):
                cached_vector(len(bad), bad.tobytes())
