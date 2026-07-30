from pipeline.metrics import bbox_iou, bbox_match_score, character_error_rate, evaluate_regions, normalize_text


def test_normalize_text_preserves_japanese_content_and_removes_layout():
    assert normalize_text(" ロキとの\n戦い!! ") == "ロキとの戦い!!"


def test_character_error_rate_is_zero_for_equivalent_layout():
    assert character_error_rate("ほっほっ\nほっ!!", "ほっほっほっ!!") == 0


def test_region_matching_counts_missed_text_as_error():
    metrics = evaluate_regions(
        [{"id": 2, "x": 10, "y": 10, "w": 40, "h": 40, "text": "魔神"}],
        [
            {"bubble_id": "hit", "x": 10, "y": 10, "w": 40, "h": 40, "text": "魔神"},
            {"bubble_id": "miss", "x": 100, "y": 100, "w": 20, "h": 20, "text": "どん"},
        ],
    )
    assert metrics[0].cer == 0
    assert metrics[1].prediction_id is None and metrics[1].cer == 1


def test_bbox_iou_is_symmetric():
    a = {"x": 0, "y": 0, "w": 10, "h": 10}
    b = {"x": 5, "y": 5, "w": 10, "h": 10}
    assert bbox_iou(a, b) == bbox_iou(b, a)


def test_match_score_accepts_a_text_line_inside_a_bubble():
    bubble = {"x": 0, "y": 0, "w": 100, "h": 100}
    line = {"x": 30, "y": 30, "w": 20, "h": 30}
    assert bbox_iou(line, bubble) < 0.10
    assert bbox_match_score(line, bubble) == 1.0
