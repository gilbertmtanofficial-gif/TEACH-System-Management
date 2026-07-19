def calculate_points(current, deduction):
    return max(0, current - deduction)

def test_point_deduction():
    assert calculate_points(10, 3) == 7
    assert calculate_points(2, 5) == 0

def test_point_addition():
    assert (5 + 3) == 8
