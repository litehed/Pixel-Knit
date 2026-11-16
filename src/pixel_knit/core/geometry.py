def line_cells(start: tuple[int, int], end: tuple[int, int]):
    (r0, c0), (r1, c1) = start, end
    dr, dc = abs(r1 - r0), abs(c1 - c0)
    sr = 1 if r0 < r1 else -1
    sc = 1 if c0 < c1 else -1
    err = dc - dr
    while True:
        yield r0, c0
        if (r0, c0) == (r1, c1):
            return
        e2 = 2 * err
        if e2 > -dr:
            err -= dr
            c0 += sc
        if e2 < dc:
            err += dc
            r0 += sr
