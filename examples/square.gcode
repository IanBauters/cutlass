; 20 mm square in mm, Z controls the blade
G21            ; millimetres
G90            ; absolute
G0 Z5          ; lift
G0 X10 Y10     ; travel to start
G1 Z-1 F1000   ; plunge (tool down)
G1 X30 Y10     ; bottom edge
G1 X30 Y30     ; right edge
G1 X10 Y30     ; top edge
G1 X10 Y10     ; close
G0 Z5          ; lift
