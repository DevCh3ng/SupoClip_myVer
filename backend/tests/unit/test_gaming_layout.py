
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from src.video_utils import detect_gaming_layout, create_gaming_split_clip, round_to_even

class TestGamingLayout(unittest.TestCase):
    def setUp(self):
        # Mock VideoFileClip
        self.mock_clip = MagicMock()
        self.mock_clip.size = (1920, 1080)
        self.mock_clip.duration = 10.0
        
    @patch("src.video_utils.detect_faces_in_clip")
    def test_detect_gaming_layout_found(self, mock_detect_faces):
        # Mock a face in the top-right corner
        # face_center_x, face_center_y, face_area, confidence
        mock_detect_faces.return_value = [
            (1600, 200, 10000, 0.9), # Small face
        ]
        
        result = detect_gaming_layout(self.mock_clip, 0, 10)
        self.assertIsNotNone(result)
        x, y, w, h = result
        self.assertTrue(x > 1000) # Should be on the right
        self.assertTrue(y < 500) # Should be on top
        self.assertEqual(w, round_to_even(w))
        
    @patch("src.video_utils.detect_faces_in_clip")
    def test_detect_gaming_layout_not_found(self, mock_detect_faces):
        # Mock a large face (not a webcam)
        mock_detect_faces.return_value = [
            (960, 540, 500000, 0.9), # Large area
        ]
        
        result = detect_gaming_layout(self.mock_clip, 0, 10)
        self.assertNone(result)

    def test_create_gaming_split_clip_dimensions(self):
        # Mock webcam box
        webcam_box = (1500, 100, 300, 300)
        target_w, target_h = 1080, 1920
        
        # We need to mock cropped().resized() and CompositeVideoClip
        with patch("src.video_utils.CompositeVideoClip") as mock_composite:
            create_gaming_split_clip(self.mock_clip, webcam_box, target_w, target_h)
            
            # Verify CompositeVideoClip was called with target size
            args, kwargs = mock_composite.call_args
            self.assertEqual(kwargs["size"], (target_w, target_h))
            self.assertEqual(len(args[0]), 2) # Should have 2 clips

if __name__ == "__main__":
    unittest.main()
