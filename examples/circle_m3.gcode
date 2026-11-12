; 20 mm circle driven by M3/M5 (no Z), one G2 arc split into two half-circles
G21
G90
M5             ; tool up
G0 X10 Y20     ; start on the circle (centre 20,20, r10)
M3             ; tool down
G2 X30 Y20 I10 J0   ; lower half, clockwise
G2 X10 Y20 I-10 J0  ; upper half, clockwise
M5             ; tool up
